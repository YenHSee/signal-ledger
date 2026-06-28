import json
import os
import sys
from datetime import datetime
import psycopg2
from psycopg2 import Error
import psycopg2.extras
from psycopg2.extras import execute_values
from psycopg2.pool import ThreadedConnectionPool

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

db_pool = None

def init_db_pool(min_conn=1, max_conn=20):
    """初始化全局多线程安全的数据库连接池"""
    global db_pool
    if db_pool is None:
        try:
            db_pool = ThreadedConnectionPool(
                min_conn, max_conn,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME
            )
            print(f"📡 [POOL] 成功创建 Supabase 线程安全连接池 (最大容量: {max_conn})")
        except Exception as e:
            print(f"❌ [POOL] 连接池初始化失败: {e}")
            sys.exit(1)

def close_db_pool():
    """安全关闭全局连接池"""
    global db_pool
    if db_pool:
        db_pool.closeall()
        print("🔌 [POOL] 连接池所有资源已安全释放。")


# Helper Function
def execute_simple_sql(sql_statement):
    """通用的快捷 SQL 执行工具（🌟 升级版：优先使用全局连接池，没池子时才走独立连接）"""
    global db_pool
    connection = None
    cursor = None
    is_from_pool = False
    try:
        # 🌟 核心判断：如果全局连接池已经初始化了，就直接从池子里‘秒捞’连接
        if db_pool is not None:
            connection = db_pool.getconn()
            is_from_pool = True
        else:
            # 如果池子还没建（比如单独运行测试），就走以前的老路
            connection = psycopg2.connect(
                user=config.DB_USER, password=config.DB_PASSWORD,
                host=config.DB_HOST, port=config.DB_PORT, database=config.DB_NAME
            )
            
        cursor = connection.cursor()
        cursor.execute(sql_statement)
        connection.commit()
    except Exception as e:
        print(f"❌ SQL 执行失败: {e}")
        if connection: connection.rollback()
    finally:
        if cursor: cursor.close()
        if connection: 
            if is_from_pool and db_pool:
                # 🌟 如果是从池子里借的，记得还回去，千万别 close 它
                db_pool.putconn(connection)
            else:
                connection.close()


def init_tables():
    """初始化表结构"""
    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(
            user=config.DB_USER, password=config.DB_PASSWORD,
            host=config.DB_HOST, port=config.DB_PORT, database=config.DB_NAME
        )
        cursor = connection.cursor()
        
        create_overview_sql = """
        CREATE TABLE IF NOT EXISTS company_overview (
            symbol VARCHAR(10) PRIMARY KEY,
            asset_type VARCHAR(50), name VARCHAR(255), description TEXT, cik VARCHAR(20),
            exchange VARCHAR(50), currency VARCHAR(10), country VARCHAR(50), sector VARCHAR(100),
            industry VARCHAR(100), address TEXT, official_site TEXT, fiscal_year_end VARCHAR(20),
            latest_quarter DATE, market_capitalization BIGINT, ebitda BIGINT,
            pe_ratio NUMERIC(10, 4), peg_ratio NUMERIC(10, 4), book_value NUMERIC(10, 4),
            dividend_per_share NUMERIC(10, 4), dividend_yield NUMERIC(10, 4), eps NUMERIC(10, 4),
            revenue_per_share_ttm NUMERIC(10, 4), profit_margin NUMERIC(10, 4), operating_margin_ttm NUMERIC(10, 4),
            return_on_assets_ttm NUMERIC(10, 4), return_on_equity_ttm NUMERIC(10, 4), revenue_ttm BIGINT,
            gross_profit_ttm BIGINT, diluted_eps_ttm NUMERIC(10, 4), quarterly_earnings_growth_yoy NUMERIC(10, 4),
            quarterly_revenue_growth_yoy NUMERIC(10, 4), analyst_target_price NUMERIC(10, 4),
            analyst_rating_strong_buy INTEGER, analyst_rating_buy INTEGER, analyst_rating_hold INTEGER,
            analyst_rating_sell INTEGER, analyst_rating_strong_sell INTEGER, trailing_pe NUMERIC(10, 4),
            forward_pe NUMERIC(10, 4), price_to_sales_ratio_ttm NUMERIC(10, 4), price_to_book_ratio NUMERIC(10, 4),
            ev_to_revenue NUMERIC(10, 4), ev_to_ebitda NUMERIC(10, 4), beta NUMERIC(10, 4),
            week_52_high NUMERIC(10, 4), week_52_low NUMERIC(10, 4), day_50_moving_average NUMERIC(10, 4),
            day_200_moving_average NUMERIC(10, 4), shares_outstanding BIGINT, shares_float BIGINT,
            percent_insiders NUMERIC(10, 4), percent_institutions NUMERIC(10, 4), dividend_date DATE,
            ex_dividend_date DATE, is_sp500 BOOLEAN DEFAULT FALSE, last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """

        create_prices_sql = """
        CREATE TABLE IF NOT EXISTS daily_prices (
            symbol VARCHAR(10) REFERENCES company_overview(symbol),
            trade_date DATE, open_price NUMERIC(10, 4), high_price NUMERIC(10, 4),
            low_price NUMERIC(10, 4), close_price NUMERIC(10, 4), adjusted_close NUMERIC(10, 4),
            volume BIGINT, PRIMARY KEY (symbol, trade_date)
        );
        """

        cursor.execute(create_overview_sql)
        cursor.execute(create_prices_sql)
        connection.commit()
        print("🎉 所有数据表成功同步！")
    except (Exception, Error) as error:
        print("❌ 数据库操作发生错误:", error)
        if connection: connection.rollback()
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


def insert_company_overview(clean_data: dict):
    """🚀 极速无损版：从全局多线程连接池里‘秒捞’连接进行写入"""
    global db_pool
    if not clean_data or "symbol" not in clean_data:
        return False

    symbol = clean_data["symbol"]
    connection = None
    cursor = None
    try:
        # 🌟 不再重新生成连接，直接从池子里租借一根现成的连接线，耗时 0 毫秒！
        connection = db_pool.getconn()
        cursor = connection.cursor()

        upsert_sql = """
        INSERT INTO company_overview (
            symbol, asset_type, name, description, cik, exchange, currency, country, 
            sector, industry, address, official_site, fiscal_year_end, latest_quarter, 
            market_capitalization, ebitda, pe_ratio, peg_ratio, book_value, 
            dividend_per_share, dividend_yield, eps, revenue_per_share_ttm, 
            profit_margin, operating_margin_ttm, return_on_assets_ttm, return_on_equity_ttm, 
            revenue_ttm, gross_profit_ttm, diluted_eps_ttm, quarterly_earnings_growth_yoy, 
            quarterly_revenue_growth_yoy, analyst_target_price, analyst_rating_strong_buy, 
            analyst_rating_buy, analyst_rating_hold, analyst_rating_sell, analyst_rating_strong_sell, 
            trailing_pe, forward_pe, price_to_sales_ratio_ttm, price_to_book_ratio, 
            ev_to_revenue, ev_to_ebitda, beta, week_52_high, week_52_low, 
            day_50_moving_average, day_200_moving_average, shares_outstanding, shares_float, 
            percent_insiders, percent_institutions, dividend_date, ex_dividend_date, 
            is_sp500, last_updated
        ) VALUES (
            %(symbol)s, %(asset_type)s, %(name)s, %(description)s, %(cik)s, %(exchange)s, %(currency)s, %(country)s, 
            %(sector)s, %(industry)s, %(address)s, %(official_site)s, %(fiscal_year_end)s, %(latest_quarter)s, 
            %(market_capitalization)s, %(ebitda)s, %(pe_ratio)s, %(peg_ratio)s, %(book_value)s, 
            %(dividend_per_share)s, %(dividend_yield)s, %(eps)s, %(revenue_per_share_ttm)s, 
            %(profit_margin)s, %(operating_margin_ttm)s, %(return_on_assets_ttm)s, %(return_on_equity_ttm)s, 
            %(revenue_ttm)s, %(gross_profit_ttm)s, %(diluted_eps_ttm)s, %(quarterly_earnings_growth_yoy)s, 
            %(quarterly_revenue_growth_yoy)s, %(analyst_target_price)s, %(analyst_rating_strong_buy)s, 
            %(analyst_rating_buy)s, %(analyst_rating_hold)s, %(analyst_rating_sell)s, %(analyst_rating_strong_sell)s, 
            %(trailing_pe)s, %(forward_pe)s, %(price_to_sales_ratio_ttm)s, %(price_to_book_ratio)s, 
            %(ev_to_revenue)s, %(ev_to_ebitda)s, %(beta)s, %(week_52_high)s, %(week_52_low)s, 
            %(day_50_moving_average)s, %(day_200_moving_average)s, %(shares_outstanding)s, %(shares_float)s, 
            %(percent_insiders)s, %(percent_institutions)s, %(dividend_date)s, %(ex_dividend_date)s, 
            %(is_sp500)s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (symbol) 
        DO UPDATE SET 
            asset_type = EXCLUDED.asset_type, name = EXCLUDED.name, description = EXCLUDED.description,
            exchange = EXCLUDED.exchange, sector = EXCLUDED.sector, industry = EXCLUDED.industry,
            latest_quarter = EXCLUDED.latest_quarter, market_capitalization = EXCLUDED.market_capitalization,
            ebitda = EXCLUDED.ebitda, pe_ratio = EXCLUDED.pe_ratio, peg_ratio = EXCLUDED.peg_ratio,
            eps = EXCLUDED.eps, profit_margin = EXCLUDED.profit_margin, revenue_ttm = EXCLUDED.revenue_ttm,
            return_on_equity_ttm = EXCLUDED.return_on_equity_ttm, quarterly_earnings_growth_yoy = EXCLUDED.quarterly_earnings_growth_yoy,
            analyst_target_price = EXCLUDED.analyst_target_price, trailing_pe = EXCLUDED.trailing_pe,
            forward_pe = EXCLUDED.forward_pe, week_52_high = EXCLUDED.week_52_high, week_52_low = EXCLUDED.week_52_low,
            day_50_moving_average = EXCLUDED.day_50_moving_average, day_200_moving_average = EXCLUDED.day_200_moving_average,
            percent_institutions = EXCLUDED.percent_institutions, is_sp500 = EXCLUDED.is_sp500, last_updated = CURRENT_TIMESTAMP;
        """
        cursor.execute(upsert_sql, clean_data)
        connection.commit()
        return True
    except Exception as error:
        print(f"❌ 股票 {symbol} 基本面同步失败: {error}")
        if connection: connection.rollback()
        return False
    finally:
        if cursor: cursor.close()
        if connection and db_pool: 
            # 🌟 极其重要：把连接物归原主，还回池子里给下一个线程用，绝对不断开！
            db_pool.putconn(connection)


def insert_daily_prices(cursor, prices_list: list):
    """接收外部已经创建好的独占复用游标，使用真正的 Bulk Insert 批量塞入数据"""
    if not prices_list:
        return False

    symbol = prices_list[0].get("symbol")
    data_tuples = [
        (
            p.get("symbol"), p.get("trade_date"), p.get("open_price"), p.get("high_price"),
            p.get("low_price"), p.get("close_price"), p.get("adjusted_close"), p.get("volume")
        ) for p in prices_list
    ]

    upsert_sql = """
    INSERT INTO daily_prices (
        symbol, trade_date, open_price, high_price, low_price, close_price, adjusted_close, volume
    ) VALUES %s
    ON CONFLICT (symbol, trade_date) 
    DO UPDATE SET 
        open_price = EXCLUDED.open_price, high_price = EXCLUDED.high_price, low_price = EXCLUDED.low_price,
        close_price = EXCLUDED.close_price, adjusted_close = EXCLUDED.adjusted_close, volume = EXCLUDED.volume;
    """
    execute_values(cursor, upsert_sql, data_tuples)
    return True


def build_ai_context(ticker: str):
    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(
            user=config.DB_USER, password=config.DB_PASSWORD,
            host=config.DB_HOST, port=config.DB_PORT, database=config.DB_NAME
        )
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT * FROM company_overview WHERE symbol = %s", (ticker.upper(),))
        overview = cursor.fetchone()
        if not overview: return None

        cursor.execute("""
            SELECT trade_date, close_price FROM daily_prices 
            WHERE symbol = %s ORDER BY trade_date DESC LIMIT 15
        """, (ticker.upper(),))
        prices = cursor.fetchall()

        current_price = float(prices[0]['close_price']) if prices else 0
        price_3_weeks_ago = float(prices[-1]['close_price']) if len(prices) == 15 else current_price

        recent_price_change_pct = 0
        if price_3_weeks_ago > 0:
            recent_price_change_pct = round((current_price - price_3_weeks_ago) / price_3_weeks_ago, 4)

        high_52 = float(overview['week_52_high']) if overview['week_52_high'] else 0
        low_52 = float(overview['week_52_low']) if overview['week_52_low'] else 0
        current_position_pct = 0
        if high_52 > low_52 and current_price > 0:
            current_position_pct = round((current_price - low_52) / (high_52 - low_52), 4)

        return {
            "company_identity": {
                "symbol": overview['symbol'], "name": overview['name'], "sector": overview['sector'],
                "business_summary": overview['description'][:300] if overview['description'] else "N/A"
            },
            "profitability_and_scale": {
                "market_cap": float(overview['market_capitalization'] or 0),
                "profit_margin": float(overview['profit_margin'] or 0),
                "return_on_equity_ttm": float(overview['return_on_equity_ttm'] or 0)
            },
            "valuation_and_growth": {
                "trailing_pe": float(overview['trailing_pe'] or 0), "forward_pe": float(overview['forward_pe'] or 0),
                "peg_ratio": float(overview['peg_ratio'] or 0),
                "earnings_growth_yoy": float(overview['quarterly_earnings_growth_yoy'] or 0),
                "revenue_growth_yoy": float(overview['quarterly_revenue_growth_yoy'] or 0) 
            },
            "smart_money_consensus": {
                "percent_institutions": float(overview['percent_institutions'] or 0),
                "analyst_target_price": float(overview['analyst_target_price'] or 0), "current_price": current_price
            },
            "technical_and_momentum": {
                "moving_averages": {
                    "day_50_ma": float(overview['day_50_moving_average'] or 0),
                    "day_200_ma": float(overview['day_200_moving_average'] or 0)
                },
                "week_52_range": {"high": high_52, "low": low_52, "current_position_pct": current_position_pct},
                "recent_3_weeks_action": {"price_change_pct": recent_price_change_pct}
            }
        }
    except Exception as e:
        print(f"❌ 组装 AI Context 失败: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


def insert_investment_report(ticker: str, ai_analysis: dict, raw_data: dict, model_tier: str):
    """
    将 AI 生成的投资研报和当时的原始数据快照，一并持久化到 Supabase 数据库
    """
    global db_pool
    connection = None
    cursor = None
    try:
        if db_pool is not None:
            connection = db_pool.getconn()
        else:
            connection = psycopg2.connect(
                user=config.DB_USER, password=config.DB_PASSWORD,
                host=config.DB_HOST, port=config.DB_PORT, database=config.DB_NAME
            )
        cursor = connection.cursor()

        insert_sql = """
        INSERT INTO investment_reports (
            ticker, model_tier, conclusion, conviction_level, target_price, 
            upside_downside_pct, risk_level, reasoning, full_report, 
            raw_financial_data, generated_at
        ) VALUES (
            %(ticker)s, %(model_tier)s, %(conclusion)s, %(conviction_level)s, %(target_price)s,
            %(upside_downside_pct)s, %(risk_level)s, %(reasoning)s, %(full_report)s,
            %(raw_financial_data)s, %(generated_at)s
        )
        """
        
        # 安全处理 target_price (防止大模型偶尔返回带有 $ 或逗号的字符串，或者空值)
        target_price_raw = ai_analysis.get("target_price", 0)
        try:
            target_price_float = float(str(target_price_raw).replace('$', '').replace(',', ''))
        except ValueError:
            target_price_float = 0

        # 组装数据参数
        data_params = {
            "ticker": ticker.upper(),
            "model_tier": model_tier,
            "conclusion": ai_analysis.get("conclusion", "N/A"),
            "conviction_level": ai_analysis.get("conviction_level", "N/A"),
            "target_price": target_price_float,
            "upside_downside_pct": ai_analysis.get("upside_downside_pct", "N/A"),
            "risk_level": ai_analysis.get("risk_level", "N/A"),
            "reasoning": ai_analysis.get("reasoning", "N/A"),
            "full_report": ai_analysis.get("full_report", "N/A"),
            "raw_financial_data": psycopg2.extras.Json(raw_data), 
            "generated_at": ai_analysis.get("generated_at", datetime.now().isoformat())
        }

        cursor.execute(insert_sql, data_params)
        connection.commit()
        return True

    except Exception as error:
        print(f"❌ 股票 {ticker} 研报写入数据库失败: {error}")
        if connection: connection.rollback()
        return False
    finally:
        if cursor: cursor.close()
        if connection:
            if db_pool:
                db_pool.putconn(connection)
            else:
                connection.close()


def save_analysis_report(ticker: str, analysis_output: dict, raw_data: dict, model_letter: str = "L"):
    date_str = datetime.now().strftime("%Y-%m-%d")
    exact_time = datetime.now().isoformat() 
    report = {
        "ticker": ticker.upper(), "timestamp": exact_time, "model_tier": model_letter,
        "ai_analysis": analysis_output, "raw_financial_data": raw_data
    }
    output_dir = "reports"
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    file_name = f"{date_str}_{ticker.upper()}_{model_letter}_report.json"
    file_path = os.path.join(output_dir, file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
    print(f"✅ 研报已持久化 (保留历史): {file_path}")

if __name__ == "__main__":
    init_tables()