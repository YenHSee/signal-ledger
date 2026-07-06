"""
一次性新闻 backfill 脚本 (Finnhub)。

两个阶段：
  1. 大范围拉取：每支票用一次 [today - N 天, today] 的宽区间请求拉新闻。
     Finnhub 对宽区间的返回条数有上限，热门票的旧新闻可能被截断，所以还需要第二阶段。
  2. 异动日精确补拉：按 daily_prices 计算异动日（单日涨跌 >= 2% 或
     volume >= 30 天均量 2 倍，与前端 computeDailyChanges 同一套规则），
     对每个异动日单独发一次 from=to=当日 的请求，保证关键日期的新闻不被截断丢掉。

写入统一走 insert_stock_news（按 finnhub_id ON CONFLICT DO NOTHING），两阶段重复拉到的新闻自动去重。

用法：
    python scripts/backfill_news.py                    # 全量 S&P 500，回看 30 天
    python scripts/backfill_news.py --days 30 --tickers AAPL,MSFT
    python scripts/backfill_news.py --skip-broad       # 只跑异动日补拉
    python scripts/backfill_news.py --skip-anomaly     # 只跑大范围拉取
"""

import argparse
import os
import sys
import time
from collections import defaultdict
from datetime import date, timedelta

import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from tools.finnhub_news import get_company_news
from utils.data_transformer import transform_finnhub_news_to_db
from utils.storage import init_tables, insert_stock_news

# 与前端 computeDailyChanges 保持一致的异动日阈值
BIG_MOVE_PCT = 2.0
VOLUME_SPIKE_RATIO = 2.0
VOLUME_AVG_WINDOW = 30


def _connect():
    return psycopg2.connect(
        user=config.DB_USER, password=config.DB_PASSWORD,
        host=config.DB_HOST, port=config.DB_PORT, database=config.DB_NAME
    )


def get_backfill_symbols(connection):
    """优先取 S&P 500 名单；company_overview 还没灌数据时退回 daily_prices 里出现过的票"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT symbol FROM company_overview WHERE is_sp500 = TRUE ORDER BY symbol;")
        symbols = [row[0] for row in cursor.fetchall()]
        if symbols:
            return symbols
        cursor.execute("SELECT DISTINCT symbol FROM daily_prices ORDER BY symbol;")
        return [row[0] for row in cursor.fetchall()]


def load_price_rows(connection, from_date):
    """一次性捞出窗口内所有票的日线，按 symbol 分组、按日期升序"""
    grouped = defaultdict(list)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT symbol, trade_date, close_price, volume
            FROM daily_prices
            WHERE trade_date >= %s
            ORDER BY symbol, trade_date;
            """,
            (from_date,),
        )
        for symbol, trade_date, close_price, volume in cursor.fetchall():
            grouped[symbol].append({
                "date": trade_date,
                "close": float(close_price) if close_price is not None else None,
                "volume": int(volume) if volume is not None else None,
            })
    return grouped


def compute_anomaly_dates(price_rows):
    """
    price_rows: 单支票按日期升序的 [{date, close, volume}]。
    返回异动日 date 列表：单日涨跌 >= 2%，或 volume >= 近 30 日均量的 2 倍。
    """
    anomaly_dates = []
    for index, row in enumerate(price_rows):
        prev = price_rows[index - 1] if index > 0 else None
        change_pct = None
        if prev and prev["close"] and row["close"] is not None:
            change_pct = (row["close"] - prev["close"]) / prev["close"] * 100

        volume_window = [
            r["volume"]
            for r in price_rows[max(0, index - (VOLUME_AVG_WINDOW - 1)):index + 1]
            if r["volume"] is not None
        ]
        avg_volume = sum(volume_window) / len(volume_window) if volume_window else None

        is_big_move = change_pct is not None and abs(change_pct) >= BIG_MOVE_PCT
        is_volume_spike = (
            row["volume"] is not None
            and avg_volume is not None
            and row["volume"] >= avg_volume * VOLUME_SPIKE_RATIO
        )

        if is_big_move or is_volume_spike:
            anomaly_dates.append(row["date"])
    return anomaly_dates


def fetch_and_store(symbol, from_date, to_date):
    """拉一个区间的新闻并入库，返回 (拉到条数, 新增入库条数)"""
    raw_news = get_company_news(symbol, from_date, to_date)
    if not raw_news:
        return 0, 0
    news_rows = transform_finnhub_news_to_db(symbol, raw_news)
    inserted = insert_stock_news(news_rows)
    return len(news_rows), inserted


def run_broad_backfill(symbols, from_date, to_date):
    print(f"\n[PHASE 1] 🌊 大范围拉取: {len(symbols)} 支票 × 区间 {from_date} ~ {to_date}")
    total_inserted = 0
    for i, symbol in enumerate(symbols, 1):
        try:
            fetched, inserted = fetch_and_store(symbol, from_date, to_date)
            total_inserted += inserted
            print(f"  ({i}/{len(symbols)}) {symbol}: 拉到 {fetched} 条，新增 {inserted} 条")
        except Exception as e:
            print(f"  ⚠️ ({i}/{len(symbols)}) {symbol} 大范围拉取失败，跳过: {e}")
    print(f"✅ [PHASE 1] 完成，共新增入库 {total_inserted} 条。")
    return total_inserted


def run_anomaly_backfill(connection, symbols, from_date):
    print(f"\n[PHASE 2] 🎯 按 daily_prices 计算异动日并逐日精确补拉...")
    prices_by_symbol = load_price_rows(connection, from_date)

    tasks = []  # (symbol, anomaly_date)
    for symbol in symbols:
        rows = prices_by_symbol.get(symbol)
        if not rows:
            continue
        for anomaly_date in compute_anomaly_dates(rows):
            tasks.append((symbol, anomaly_date))

    if not tasks:
        print("✅ [PHASE 2] 窗口内没有检测到异动日，无需补拉。")
        return 0

    est_minutes = len(tasks) / 60
    print(f"🗓️ 共检测到 {len(tasks)} 个 (票, 异动日) 组合，预计耗时约 {est_minutes:.0f} 分钟 (60 calls/min pacing)")

    total_inserted = 0
    for i, (symbol, anomaly_date) in enumerate(tasks, 1):
        day = anomaly_date.isoformat()
        try:
            fetched, inserted = fetch_and_store(symbol, day, day)
            total_inserted += inserted
            print(f"  ({i}/{len(tasks)}) {symbol} @ {day}: 拉到 {fetched} 条，新增 {inserted} 条")
        except Exception as e:
            print(f"  ⚠️ ({i}/{len(tasks)}) {symbol} @ {day} 补拉失败，跳过: {e}")
    print(f"✅ [PHASE 2] 完成，异动日补拉共新增入库 {total_inserted} 条。")
    return total_inserted


def main():
    parser = argparse.ArgumentParser(description="一次性 Finnhub 新闻 backfill")
    parser.add_argument("--days", type=int, default=30, help="回看天数 (默认 30)")
    parser.add_argument("--tickers", type=str, default=None,
                        help="只处理指定票，逗号分隔 (默认全量 S&P 500)")
    parser.add_argument("--skip-broad", action="store_true", help="跳过阶段 1 大范围拉取")
    parser.add_argument("--skip-anomaly", action="store_true", help="跳过阶段 2 异动日补拉")
    args = parser.parse_args()

    if not config.FINNHUB_API_KEY:
        print("❌ 未配置 FINNHUB_API_KEY，无法执行 backfill。请先在 .env 里配置。")
        sys.exit(1)

    start_time = time.time()
    today = date.today()
    from_date = today - timedelta(days=args.days)

    print("=" * 60)
    print(f"🚀 [START] 新闻一次性 backfill (回看 {args.days} 天: {from_date} ~ {today})")
    print("=" * 60)

    # 确保 stock_news 表已存在
    init_tables()

    connection = _connect()
    try:
        if args.tickers:
            symbols = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        else:
            symbols = get_backfill_symbols(connection)

        if not symbols:
            print("❌ 找不到任何待处理的票 (company_overview / daily_prices 均为空)，请先跑每日 ETL。")
            sys.exit(1)

        total = 0
        if not args.skip_broad:
            total += run_broad_backfill(symbols, from_date.isoformat(), today.isoformat())
        if not args.skip_anomaly:
            total += run_anomaly_backfill(connection, symbols, from_date)
    finally:
        connection.close()

    print("\n" + "=" * 60)
    print(f"🎉 [FINISH] backfill 完成，共新增入库 {total} 条新闻，耗时 {round(time.time() - start_time, 1)} 秒")
    print("=" * 60)


if __name__ == "__main__":
    main()
