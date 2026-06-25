import json
import os
import sys
from datetime import datetime
import psycopg2
from psycopg2 import Error
import psycopg2.extras

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config


# Helper Function
def execute_simple_sql(sql_statement):
    """通用的快捷 SQL 执行工具 (用于执行重置标签、清空表等操作)"""
    connection = None
    cursor = None
    try:
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
        if connection: connection.close()


def init_tables():
    """连接 stock_analyst 数据库并初始化表结构"""
    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME
        )
        cursor = connection.cursor()
        print(f"✅ 成功连接到数据库: {config.DB_NAME}")

        # 🌟 1. 创建 company_overview 表 (已包含 is_sp500 字段)
        create_overview_sql = """
        CREATE TABLE IF NOT EXISTS company_overview (
            symbol VARCHAR(10) PRIMARY KEY,
            asset_type VARCHAR(50),
            name VARCHAR(255),
            description TEXT,
            cik VARCHAR(20),
            exchange VARCHAR(50),
            currency VARCHAR(10),
            country VARCHAR(50),
            sector VARCHAR(100),
            industry VARCHAR(100),
            address TEXT,
            official_site TEXT,
            fiscal_year_end VARCHAR(20),
            latest_quarter DATE,
            market_capitalization BIGINT,
            ebitda BIGINT,
            pe_ratio NUMERIC(10, 4),
            peg_ratio NUMERIC(10, 4),
            book_value NUMERIC(10, 4),
            dividend_per_share NUMERIC(10, 4),
            dividend_yield NUMERIC(10, 4),
            eps NUMERIC(10, 4),
            revenue_per_share_ttm NUMERIC(10, 4),
            profit_margin NUMERIC(10, 4),
            operating_margin_ttm NUMERIC(10, 4),
            return_on_assets_ttm NUMERIC(10, 4),
            return_on_equity_ttm NUMERIC(10, 4),
            revenue_ttm BIGINT,
            gross_profit_ttm BIGINT,
            diluted_eps_ttm NUMERIC(10, 4),
            quarterly_earnings_growth_yoy NUMERIC(10, 4),
            quarterly_revenue_growth_yoy NUMERIC(10, 4),
            analyst_target_price NUMERIC(10, 4),
            analyst_rating_strong_buy INTEGER,
            analyst_rating_buy INTEGER,
            analyst_rating_hold INTEGER,
            analyst_rating_sell INTEGER,
            analyst_rating_strong_sell INTEGER,
            trailing_pe NUMERIC(10, 4),
            forward_pe NUMERIC(10, 4),
            price_to_sales_ratio_ttm NUMERIC(10, 4),
            price_to_book_ratio NUMERIC(10, 4),
            ev_to_revenue NUMERIC(10, 4),
            ev_to_ebitda NUMERIC(10, 4),
            beta NUMERIC(10, 4),
            week_52_high NUMERIC(10, 4),
            week_52_low NUMERIC(10, 4),
            day_50_moving_average NUMERIC(10, 4),
            day_200_moving_average NUMERIC(10, 4),
            shares_outstanding BIGINT,
            shares_float BIGINT,
            percent_insiders NUMERIC(10, 4),
            percent_institutions NUMERIC(10, 4),
            dividend_date DATE,
            ex_dividend_date DATE,
            is_sp500 BOOLEAN DEFAULT FALSE,
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """

        # 创建 daily_prices 表
        create_prices_sql = """
        CREATE TABLE IF NOT EXISTS daily_prices (
            symbol VARCHAR(10) REFERENCES company_overview(symbol),
            trade_date DATE,
            open_price NUMERIC(10, 4),
            high_price NUMERIC(10, 4),
            low_price NUMERIC(10, 4),
            close_price NUMERIC(10, 4),
            adjusted_close NUMERIC(10, 4),
            volume BIGINT,
            PRIMARY KEY (symbol, trade_date)
        );
        """

        cursor.execute(create_overview_sql)
        print("✅ 表 'company_overview' 初始化检查完成 ")
        
        cursor.execute(create_prices_sql)
        print("✅ 表 'daily_prices' 初始化检查完成")

        connection.commit()
        print("🎉 所有数据表成功同步！")

    except (Exception, Error) as error:
        print("❌ 数据库操作发生错误:", error)
        if connection: connection.rollback()
            
    finally:
        if cursor: cursor.close()
        if connection: 
            connection.close()
            print("🔌 PostgreSQL 连接已安全关闭。")


def insert_company_overview(clean_data: dict):
    # 1. 只做最基本的入参校验（防呆）
    if not clean_data or "symbol" not in clean_data:
        print("❌ 错误: 传入的基本面数据为空或缺少 symbol，放弃写入数据库")
        return False

    symbol = clean_data["symbol"]
    print(f"🔄 正在将 {symbol} 的纯净基本面数据同步至 PostgreSQL...")

    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME
        )
        cursor = connection.cursor()

        # 2. 直接拿着上游传来的 clean_data 往数据库里砸
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
            return_on_equity_ttm = EXCLUDED.return_on_equity_ttm, 
            quarterly_earnings_growth_yoy = EXCLUDED.quarterly_earnings_growth_yoy,
            analyst_target_price = EXCLUDED.analyst_target_price, trailing_pe = EXCLUDED.trailing_pe,
            forward_pe = EXCLUDED.forward_pe, week_52_high = EXCLUDED.week_52_high, week_52_low = EXCLUDED.week_52_low,
            day_50_moving_average = EXCLUDED.day_50_moving_average, day_200_moving_average = EXCLUDED.day_200_moving_average,
            percent_institutions = EXCLUDED.percent_institutions,
            is_sp500 = EXCLUDED.is_sp500,
            last_updated = CURRENT_TIMESTAMP;
        """

        cursor.execute(upsert_sql, clean_data)
        connection.commit()
        print(f"✨ 成功！股票 {symbol} 的基本面数据已持久化至 DB！")
        return True

    except (Exception, Error) as error:
        print(f"❌ 数据库写入失败: {error}")
        if connection: connection.rollback()
        return False
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


def insert_daily_prices(prices_list: list):
    if not prices_list:
        print("❌ 错误: 传入的股价列表为空，放弃写入。")
        return False

    symbol = prices_list[0].get("symbol")
    print(f"🔄 正在将 {symbol} 的 {len(prices_list)} 天历史 K 线批量同步至 PostgreSQL...")

    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME
        )
        cursor = connection.cursor()

        upsert_sql = """
        INSERT INTO daily_prices (
            symbol, trade_date, open_price, high_price, low_price, 
            close_price, adjusted_close, volume
        ) VALUES (
            %(symbol)s, %(trade_date)s, %(open_price)s, %(high_price)s, %(low_price)s, 
            %(close_price)s, %(adjusted_close)s, %(volume)s
        )
        ON CONFLICT (symbol, trade_date) 
        DO UPDATE SET 
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            adjusted_close = EXCLUDED.adjusted_close,
            volume = EXCLUDED.volume;
        """

        cursor.executemany(upsert_sql, prices_list)
        connection.commit()
        
        print(f"✨ 成功！{symbol} 的 {len(prices_list)} 条历史 K 线已持久化至 DB！")
        return True

    except (Exception, Error) as error:
        print(f"❌ 股价数据库写入失败: {error}")
        if connection: connection.rollback() 
        return False
    finally:
        if cursor: cursor.close()
        if connection: connection.close()
        

def build_ai_context(ticker: str):
    """
    【读时计算 (Compute-on-Read) 组装器】
    从 DB 拉取基本面和最新 K 线，动态计算技术指标（如 3周前价格），
    组装成极其完美的 JSON 喂给 AI。
    """
    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(
            user=config.DB_USER, password=config.DB_PASSWORD,
            host=config.DB_HOST, port=config.DB_PORT, database=config.DB_NAME
        )
        # 使用 DictCursor 让我们能通过列名（如 row['pe_ratio']）直接拿数据
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 1. 获取基本面数据
        cursor.execute("SELECT * FROM company_overview WHERE symbol = %s", (ticker.upper(),))
        overview = cursor.fetchone()
        
        if not overview:
            return None

        # 2. 获取最近 15 个交易日（约 3 周）的收盘价
        cursor.execute("""
            SELECT trade_date, close_price 
            FROM daily_prices 
            WHERE symbol = %s 
            ORDER BY trade_date DESC 
            LIMIT 15
        """, (ticker.upper(),))
        prices = cursor.fetchall()

        current_price = float(prices[0]['close_price']) if prices else 0
        price_3_weeks_ago = float(prices[-1]['close_price']) if len(prices) == 15 else current_price

        # 3. 动态计算 52 周分位数位置
        high_52 = float(overview['week_52_high']) if overview['week_52_high'] else 0
        low_52 = float(overview['week_52_low']) if overview['week_52_low'] else 0
        current_position_pct = 0
        if high_52 > low_52 and current_price > 0:
            current_position_pct = round((current_price - low_52) / (high_52 - low_52), 4)

        # 4. 组装 AI 最喜欢的结构
        return {
            "company_identity": {
                "symbol": overview['symbol'],
                "name": overview['name'],
                "sector": overview['sector'],
                "business_summary": overview['description'][:300] if overview['description'] else "N/A"
            },
            "profitability_and_scale": {
                "market_cap": float(overview['market_capitalization'] or 0),
                "profit_margin": float(overview['profit_margin'] or 0),
                "return_on_equity_ttm": float(overview['return_on_equity_ttm'] or 0)
            },
            "valuation_and_growth": {
                "trailing_pe": float(overview['trailing_pe'] or 0),
                "forward_pe": float(overview['forward_pe'] or 0),
                "peg_ratio": float(overview['peg_ratio'] or 0),
                "earnings_growth_yoy": float(overview['quarterly_earnings_growth_yoy'] or 0)
            },
            "smart_money_consensus": {
                "percent_institutions": float(overview['percent_institutions'] or 0),
                "analyst_target_price": float(overview['analyst_target_price'] or 0),
                "current_price": current_price
            },
            "technical_and_momentum": {
                "price_3_weeks_ago": price_3_weeks_ago,
                "week_52_range": {
                    "high": high_52,
                    "low": low_52,
                    "current_position_pct": current_position_pct
                }
            }
        }
    except Exception as e:
        print(f"❌ 组装 AI Context 失败: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if connection: connection.close()
        

def save_analysis_report(ticker: str, analysis_output: dict, raw_data: dict):
    """将分析结果和原始数据存为一个结构化的 JSON 文件"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    exact_time = datetime.now().isoformat() 

    report = {
        "ticker": ticker.upper(),
        "timestamp": exact_time,
        "ai_analysis": analysis_output,
        "raw_financial_data": raw_data
    }
    
    output_dir = "reports"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    file_path = os.path.join(output_dir, f"{date_str}_{ticker.upper()}_report.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
    
    print(f"✅ 研报已持久化 (保留历史): {file_path}")


if __name__ == "__main__":
    init_tables()