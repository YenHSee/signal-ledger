import requests
import pandas as pd
import io

def get_sp500_tickers():
    """从维基百科获取 S&P 500 最新名单 (公共提取工具)"""
    print("🔍 正在从维基百科获取 S&P 500 最新名单...")
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
        
        html_buffer = io.StringIO(response.text)
        tables = pd.read_html(html_buffer)
        
        tickers = tables[0]['Symbol'].tolist()
        tickers = [str(ticker).replace('.', '-') for ticker in tickers]
        
        print(f"✅ 成功获取 {len(tickers)} 支股票代码！")
        return tickers
        
    except Exception as e:
        print(f"❌ 提取标普 500 表格失败: {e}")
        return []