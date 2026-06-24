import os
import sys
import time
import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Tools
from tools.wikipedia_scraper import get_sp500_tickers 
from tools.yahoo_finance import get_company_overview, get_daily_prices
# Utils
from utils.data_transformer import transform_yfinance_overview_to_db, transform_yfinance_prices_to_db
from utils.storage import execute_simple_sql, init_tables, insert_company_overview, insert_daily_prices


def run_stock_pipeline():
    """每日批量更新数据流水线主控程序"""
    
    print("\n" + "="*60)
    print("🚀 [START] 工业级 S&P 500 ETL 数据流水线正式启动")
    print("="*60)

    # ---------------------------------------------------------
    # [STEP 0] 系统自检
    # ---------------------------------------------------------
    print("\n[STEP 0] 🔧 正在进行系统自检与数据库无损升级...")
    init_tables() 

    # ---------------------------------------------------------
    # [STEP 1] 获取名单 (Extract)
    # ---------------------------------------------------------
    print("\n[STEP 1] 📋 正在向维基百科获取最新 S&P 500 强名单...")
    tickers = get_sp500_tickers()
    if not tickers:
        print("❌ 致命错误：无法获取股票名单，流水线终止。")
        return
        
    # ⚠️ 测试开关：如果你不想跑 500 个，取消下面这行的注释只跑前 5 个测试！
    # tickers = tickers[:5] 

    # ---------------------------------------------------------
    # [STEP 2] 数据库状态重置 (Reset & Truncate)
    # ---------------------------------------------------------
    print("\n[STEP 2] 🔄 正在重置旧的 500 强标签，并清空旧的历史股价...")
    execute_simple_sql("UPDATE company_overview SET is_sp500 = FALSE;")
    execute_simple_sql("TRUNCATE TABLE daily_prices;")

    # ---------------------------------------------------------
    # [STEP 3] 处理基本面 (Overview Loop)
    # ---------------------------------------------------------
    print(f"\n[STEP 3] 🏢 开始同步 {len(tickers)} 家公司的基本面 (Overview)...")
    for ticker in tickers:
        try:
            # 1. 抓 (Extract)
            raw_overview = get_company_overview(ticker)
            if raw_overview:
                # 2. 洗 (Transform)
                clean_overview = transform_yfinance_overview_to_db(raw_overview)
                
                # 🌟 总管权威认证：因为你在这个名单里，我给你盖上 500 强的印章！
                clean_overview["is_sp500"] = True 
                
                # 3. 存 (Load)
                insert_company_overview(clean_overview)
        except Exception as e:
            print(f"⚠️ 处理 {ticker} 基本面时发生小意外跳过: {e}")

    # ---------------------------------------------------------
    # [STEP 4] 批量处理历史股价 (Prices Loop)
    # ---------------------------------------------------------
    print(f"\n[STEP 4] 📈 开始【单次批量下载】并同步 {len(tickers)} 支股票的最新 3 个月 K 线...")
    try:
        df = get_daily_prices(tickers, period="3mo")
        
        if df is not None:
            for ticker in tickers:
                try:
                    # 提取单只股票的数据
                    ticker_df = df[ticker] if len(tickers) > 1 else df
                    ticker_df = ticker_df.dropna(subset=['Close'])
                    if ticker_df.empty:
                        continue
                    
                    # 洗 (Transform - DataFrame转字典，交给清洗车间)
                    raw_dict = ticker_df.to_dict(orient="index")
                    prices_list = transform_yfinance_prices_to_db(ticker, raw_dict)
                    
                    # 存 (Load - 纯净批量写入)
                    if prices_list:
                        insert_daily_prices(prices_list)
                        
                except Exception as single_err:
                    print(f"⚠️ 解析 {ticker} 股价时跳过: {single_err}")
                
    except Exception as e:
        print(f"❌ 批量下载股价发生致命错误: {e}")

    print("\n" + "="*60)
    print("🎉 [FINISH] 每日数据流水线完美收官！全市场最新数据已就绪。")
    print("="*60)


if __name__ == "__main__":
    start_time = time.time()
    run_stock_pipeline()
    print(f"\n⏱️ 管道总耗时: {round(time.time() - start_time, 2)} 秒")