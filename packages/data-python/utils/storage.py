import json
import os
import sys
from datetime import datetime
import psycopg2
from psycopg2 import Error
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from utils.data_transformer import transform_alpha_to_db
from tools.alpha_vantage import get_company_overview

def save_analysis_report(ticker: str, analysis_output: dict, raw_data: dict):
    """将分析结果和原始数据存为一个结构化的 JSON 文件"""
    
    # 文件名只要年月日 (方便排序和查找)
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # ⭐️ 内部自带精确到秒的 timestamp，给前端用的！
    exact_time = datetime.now().isoformat() 

    report = {
        "ticker": ticker.upper(),
        "timestamp": exact_time,          # 明确的生成时间
        "ai_analysis": analysis_output,   # 这里面也有 generated_at，双保险
        "raw_financial_data": raw_data
    }
    
    output_dir = "reports"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    file_path = os.path.join(output_dir, f"{date_str}_{ticker.upper()}_report.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
    
    print(f"✅ 研报已持久化 (保留历史): {file_path}")


def init_tables():
    """连接 stock_analyst 数据库并初始化表结构"""
    connection = None
    cursor = None
    try:
        # 1. 直接连接到 stock_analyst
        connection = psycopg2.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME
        )
        cursor = connection.cursor()
        print(f"✅ 成功连接到数据库: {config.DB_NAME}")

        # 2. 编写创建 company_overview 表的 SQL
        # ⚠️ 已添加确实的 TrailingPE, ForwardPE 等字段
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
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """

        # 3. 编写创建 daily_prices 表的 SQL
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

        # 4. 执行 SQL 并提交
        cursor.execute(create_overview_sql)
        print("✅ 表 'company_overview' 初始化检查完成。")
        
        cursor.execute(create_prices_sql)
        print("✅ 表 'daily_prices' 初始化检查完成。")

        connection.commit()
        print("🎉 所有数据表成功同步！")

    except (Exception, Error) as error:
        print("❌ 数据库操作发生错误:", error)
        if connection:
            connection.rollback() # 出错时回滚
            
    finally:
        # 5. 关闭连接
        if cursor: cursor.close()
        if connection: 
            connection.close()
            print("🔌 PostgreSQL 连接已安全关闭。")


def insert_company_overview(raw_json):
    """接收原始 JSON，内部调用 transformer 清洗，并存入数据库"""
    
    clean_data = transform_alpha_to_db(raw_json)
    if not clean_data:
        print("❌ 错误: 原始数据清洗后为空，放弃写入数据库")
        return False

    symbol = clean_data["symbol"]
    print(f"🔄 正在将清洗后的 {symbol} 基本面数据同步至 PostgreSQL...")

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
            percent_insiders, percent_institutions, dividend_date, ex_dividend_date, last_updated
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
            %(percent_insiders)s, %(percent_institutions)s, %(dividend_date)s, %(ex_dividend_date)s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (symbol) 
        DO UPDATE SET 
            asset_type = EXCLUDED.asset_type, name = EXCLUDED.name, description = EXCLUDED.description,
            exchange = EXCLUDED.exchange, sector = EXCLUDED.sector, industry = EXCLUDED.industry,
            latest_quarter = EXCLUDED.latest_quarter, market_capitalization = EXCLUDED.market_capitalization,
            ebitda = EXCLUDED.ebitda, pe_ratio = EXCLUDED.pe_ratio, peg_ratio = EXCLUDED.peg_ratio,
            eps = EXCLUDED.eps, profit_margin = EXCLUDED.profit_margin, revenue_ttm = EXCLUDED.revenue_ttm,
            analyst_target_price = EXCLUDED.analyst_target_price, trailing_pe = EXCLUDED.trailing_pe,
            forward_pe = EXCLUDED.forward_pe, week_52_high = EXCLUDED.week_52_high, week_52_low = EXCLUDED.week_52_low,
            day_50_moving_average = EXCLUDED.day_50_moving_average, day_200_moving_average = EXCLUDED.day_200_moving_average,
            last_updated = CURRENT_TIMESTAMP;
        """

        cursor.execute(upsert_sql, clean_data)
        connection.commit()
        print(f"✨ 成功！股票 {symbol} 的数据已通过 Transformer 清洗并持久化至 DB！")
        return True

    except (Exception, Error) as error:
        print(f"❌ 数据库写入失败: {error}")
        if connection: connection.rollback()
        return False
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

        
if __name__ == "__main__":
    init_tables()
    overview_data = get_company_overview("NVDA")
    insert_company_overview(overview_data)