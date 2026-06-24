import os
import sys
import yfinance as yf

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cache_manager import save_to_cache, load_from_cache

def get_company_overview(ticker: str):
    ticker = ticker.upper()
    
    # 检查缓存
    cached_data = load_from_cache(ticker, max_age_days=7)
    
    # 🌟 严谨校验：雅虎的数据里通常会有 longBusinessSummary(公司简介) 或 trailingPE
    if cached_data and "longBusinessSummary" in cached_data:
        print(f"⚡ [缓存命中] 正在使用本地基本面数据: {ticker}")
        return cached_data

    print(f"🌐 [API 请求] 正在向 Yahoo Finance 获取 {ticker} 的基本面数据...")
    
    try:
        # 发起真实的 API 请求
        yf_stock = yf.Ticker(ticker)
        
        # .info 是 yfinance 获取基本面（财报、市盈率、简介等）的核心属性
        overview_data = yf_stock.info

        # 校验数据是否有效 (雅虎如果查不到股票，可能会返回一个只有寥寥几个键的废字典)
        if not overview_data or "symbol" not in overview_data or len(overview_data) < 10:
            print(f"⚠️ [API 警告] Yahoo Finance 未返回有效的基本面数据: {ticker}")
            return None
        
        # 存入缓存并返回
        save_to_cache(ticker, overview_data)
        print(f"💾 [数据持久化] 基本面数据已保存至缓存: {ticker}")
        
        return overview_data

    except Exception as e:
        print(f"❌ [网络错误] 获取 {ticker} 基本面失败: {e}")
        return None
    
    
def get_daily_prices(tickers: str, period="3mo"):
    print(f"📥 正在通过 yfinance 批量下载 {len(tickers)} 支股票的历史股价 (周期: {period})...")
    
    try:
        df = yf.download(tickers, period=period, auto_adjust=False, group_by='ticker', progress=True)
        
        if df.empty:
            print("⚠️ 警告：批量下载返回了空数据！")
            return None
            
        print("✅ 批量拉取网络请求成功！")
        return df

    except Exception as e:
        print(f"❌ 批量获取股价失败: {e}")
        return None

if __name__ == "__main__":
    data = get_daily_prices("NVDA", period="1mo")
    
    if data:
        print("最新一天的完整数据展示:")
        print(data[-1])

