# scripts/fetch_sp500.py
import os
import sys
import time


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 🌟 关键：聘请 Yahoo 员工和数据库入库员工
from tools.yahoo_finance import get_company_overview
from tools.market_data import get_sp500_tickers
from utils.storage import insert_company_overview

def run_batch_import():
    tickers = get_sp500_tickers()
    success_count = 0
    
    print("\n🚀 开始执行 Yahoo Finance 标普 500 批量入库任务...")
    
    # 🌟 因为 Yahoo 没限制，我们直接跑满 500 个！(如果你想测试，可以先改成 tickers[:5])
    for ticker in tickers:
        print(f"\n--- 正在处理: {ticker} ---")
        
        try:
            # 1. 抓取数据 (从雅虎)
            raw_dict = get_company_overview(ticker)
            
            if raw_dict:
                # 2. 洗干净存进数据库 (PostgreSQL)
                # 这个函数内部会自动识别是不是字典，并调用 transformer 帮你转成标准格式！
                if insert_company_overview(raw_dict):
                    success_count += 1
        except Exception as e:
            print(f"❌ 处理 {ticker} 时发生意外崩溃: {e}")
            
        # 保护机制：每抓一家休息 1 秒，防止被雅虎封禁 IP
        time.sleep(1) 
        
    print(f"\n🎉 批量任务完美收官！成功将 {success_count} 家公司的基本面存入数据库。")

if __name__ == "__main__":
    run_batch_import()