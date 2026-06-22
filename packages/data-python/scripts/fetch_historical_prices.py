# scripts/fetch_historical_prices.py
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.yahoo_finance import get_daily_prices
from tools.market_data import get_sp500_tickers
from utils.storage import insert_daily_prices


def run_prices_batch_import():
    tickers = get_sp500_tickers()
    if not tickers:
        return
        
    success_count = 0
    
    print("\n🚀 开始执行 Yahoo Finance 标普 500 历史股价批量入库任务...")
    
    # ⚠️ 测试阶段：建议先跑前 5 个股票。确认没问题了，再改成 tickers (跑满500个)
    for ticker in tickers: 
        print(f"\n--- 正在处理: {ticker} 的历史股价 ---")
        
        try:
            # 1. 抓取数据 (这里我们先设定抓过去 5 年的，大模型最喜欢看长线)
            # 你可以改成 "1mo", "1y", 或者 "max"
            prices_list = get_daily_prices(ticker, period="3mo")
            
            if prices_list:
                # 2. 洗干净并批量存进 PostgreSQL
                if insert_daily_prices(prices_list):
                    success_count += 1
                    
        except Exception as e:
            print(f"❌ 处理 {ticker} 时发生意外崩溃: {e}")
            
        # 保护机制：每抓一家休息 1-2 秒，防止被雅虎封禁
        time.sleep(1.5) 
        
    print(f"\n🎉 历史股价批量任务收官！成功抓取 {success_count} 家公司。")

if __name__ == "__main__":
    run_prices_batch_import()