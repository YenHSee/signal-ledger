import json
import os
import sys
from datetime import datetime
import psycopg2
from psycopg2 import Error
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

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
            revenue_ttm BIGINT,
            gross_profit_ttm BIGINT,
            shares_outstanding BIGINT,
            shares_float BIGINT,
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

if __name__ == "__main__":
    init_tables()