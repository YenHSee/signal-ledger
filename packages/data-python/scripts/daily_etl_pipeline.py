import os
import sys
import time
import concurrent.futures

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
# Tools
from tools.wikipedia_scraper import get_sp500_tickers 
from tools.yahoo_finance import get_company_overview, get_daily_prices
from tools.finnhub_news import get_company_news
# Utils
from utils.data_transformer import transform_yfinance_overview_to_db, transform_yfinance_prices_to_db, transform_finnhub_news_to_db
# DB 层：连接池、schema、数据读写
from db.connection import init_db_pool, close_db_pool
from db.schema import execute_simple_sql, init_tables
from db.repositories import insert_company_overview, insert_daily_prices, insert_stock_news, count_stock_news


def process_single_overview(ticker):
    """给多线程线程池调用的单体任务"""
    try:
        raw_overview = get_company_overview(ticker)
        if raw_overview:
            clean_overview = transform_yfinance_overview_to_db(raw_overview)
            clean_overview["is_sp500"] = True 
            # 🌟 内部现在是秒级向连接池租借连接，绝不卡顿、绝对线程安全！
            insert_company_overview(clean_overview)
    except Exception as e:
        print(f"⚠️ 处理 {ticker} 基本面时跳过: {e}")


def sync_company_news(tickers):
    """[STEP 5] 从 Finnhub 增量拉取公司新闻并 upsert 入库（表为空时自动 backfill 30 天）"""
    from datetime import date, timedelta

    print(f"\n[STEP 5] 📰 开始同步 {len(tickers)} 支股票的公司新闻 (Finnhub)...")

    if not config.FINNHUB_API_KEY:
        print("⚠️ 未配置 FINNHUB_API_KEY，跳过新闻同步步骤。")
        return

    # 表为空 → 首次运行做 30 天 backfill；否则增量拉最近 3 天（覆盖周末/失败的 run）
    lookback_days = 30 if count_stock_news() == 0 else 3
    today = date.today()
    from_date = (today - timedelta(days=lookback_days)).isoformat()
    to_date = today.isoformat()
    print(f"🗓️ 拉取窗口: {from_date} ~ {to_date} (回看 {lookback_days} 天)")

    total_inserted = 0
    success_count = 0
    for ticker in tickers:
        try:
            raw_news = get_company_news(ticker, from_date, to_date)
            if not raw_news:
                continue
            news_rows = transform_finnhub_news_to_db(ticker, raw_news)
            inserted = insert_stock_news(news_rows)
            total_inserted += inserted
            success_count += 1
        except Exception as e:
            print(f"⚠️ 处理 {ticker} 新闻时跳过: {e}")

    print(f"✅ 新闻同步结束: {success_count} 支股票有新闻，新增入库 {total_inserted} 条。")


def run_stock_pipeline():
    """每日批量更新数据流水线主控程序 (终极完美闭环版)"""
    
    print("\n" + "="*60)
    print("🚀 [START] 工业级 S&P 500 ETL 数据流水线正式启动")
    print("="*60)

    # ---------------------------------------------------------
    # [STEP 0] 系统自检与连接池初始化
    # ---------------------------------------------------------
    print("\n[STEP 0] 🔧 正在进行系统自检并激活全局高速连接池...")
    init_tables() 
    # 🌟 重点：最大开放 20 个连接通道，给 15 个多线程工人用绰绰有余
    init_db_pool(min_conn=1, max_conn=20) 

    # ---------------------------------------------------------
    # [STEP 1] 获取名单 (Extract)
    # ---------------------------------------------------------
    print("\n[STEP 1] 📋 正在向维基百科获取最新 S&P 500 强名单...")
    tickers = get_sp500_tickers()
    if not tickers:
        print("❌ 致命错误：无法获取股票名单，流水线终止。")
        close_db_pool() 
        return

    # ---------------------------------------------------------
    # [STEP 2] 数据库状态重置 (Reset & Truncate)
    # ---------------------------------------------------------
    print("\n[STEP 2] 🔄 正在重置旧的 500 强标签，并清空旧的历史股价...")
    # 🌟 因为上面已经执行了 init_db_pool，这里的两个 SQL 执行将会直接走高速池子，速度直接起飞！
    execute_simple_sql("UPDATE company_overview SET is_sp500 = FALSE;")
    execute_simple_sql("TRUNCATE TABLE daily_prices;")

    # ---------------------------------------------------------
    # [STEP 3] 处理基本面 (Overview Loop - 🌟 多线程并发 + 连接池秒取)
    # ---------------------------------------------------------
    print(f"\n[STEP 3] 🏢 开始【多线程并发流】同步 {len(tickers)} 家公司的基本面 (Overview)...")
    
    # 雇佣 15 个并发工人，从全局连接池动态取用通道，网络损耗降到 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        executor.map(process_single_overview, tickers)

    print("✅ 所有公司的基本面数据并发同步结束。")

    # ---------------------------------------------------------
    # [STEP 4] 批量处理历史股价 (Prices Loop - 🌟 独占专线 + Bulk 批量砸入)
    # ---------------------------------------------------------
    print(f"\n[STEP 4] 📈 开始【单次批量下载】并同步 {len(tickers)} 支股票的最新 3 个月 K 线...")
    try:
        df = get_daily_prices(tickers, period="1mo")
        
        if df is not None:
            print("🔌 正在通过全局连接池进行 Bulk 批量砸入...")
            success_count = 0
            for ticker in tickers:
                try:
                    ticker_df = df[ticker] if len(tickers) > 1 else df
                    ticker_df = ticker_df.dropna(subset=['Close'])
                    if ticker_df.empty:
                        continue
                    
                    raw_dict = ticker_df.to_dict(orient="index")
                    prices_list = transform_yfinance_prices_to_db(ticker, raw_dict)
                    
                    if prices_list and insert_daily_prices(prices_list):
                        success_count += 1
                        
                except Exception as single_err:
                    print(f"⚠️ 解析 {ticker} 股价并打包时跳过: {single_err}")
            
            print(f"✨ 完美！已成功将 {success_count} 支股票（约计三万行K线）全部持久化至云端 DB！")
                
    except Exception as e:
        print(f"❌ 批量下载/砸入股价时发生致命错误: {e}")

    # ---------------------------------------------------------
    # [STEP 5] 拉取公司新闻 (News Loop - Finnhub 增量 append/upsert)
    # ---------------------------------------------------------
    sync_company_news(tickers)

    # ---------------------------------------------------------
    # 收尾：安全关闭全局连接池
    # ---------------------------------------------------------
    close_db_pool()

    print("\n" + "="*60)
    print("🎉 [FINISH] 每日数据流水线完美收官！全市场最新数据已就绪。")
    print("="*60)


if __name__ == "__main__":
    start_time = time.time()
    run_stock_pipeline()
    print(f"\n⏱️ 管道总耗时: {round(time.time() - start_time, 2)} 秒")