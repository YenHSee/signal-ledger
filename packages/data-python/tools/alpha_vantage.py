import os
import sys
import requests

# 确保能找到根目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from core.cache_manager import save_to_cache, load_from_cache

def get_company_overview(ticker: str):
    """
    专门负责向 Alpha Vantage 获取公司基本面数据 (冷数据)。
    自带缓存机制，省下宝贵的 API 额度。
    """
    ticker = ticker.upper()
    
    # 1. 检查缓存
    cached_data = load_from_cache(ticker)
    # 严谨一点：确认缓存里真的是 Overview 数据，而不是昨天存的旧版混合数据
    if cached_data and "PERatio" in cached_data:
        print(f"⚡ [缓存命中] 正在使用本地基本面数据: {ticker}")
        return cached_data

    print(f"🌐 [API 请求] 正在向 Alpha Vantage 获取 {ticker} 的基本面数据...")
    
    # 2. 发起真实的 API 请求
    overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={config.ALPHA_VANTAGE_API_KEY}"
    
    try:
        response = requests.get(overview_url)
        overview_data = response.json()

        # 3. 校验 API 额度是否耗尽
        if "Note" in overview_data or "Information" in overview_data or not overview_data:
            print(f"⚠️ [API 警告] Alpha Vantage 额度可能耗尽或触发限制: {overview_data}")
            return None
        
        # 4. 存入缓存并返回
        # 只要成功拿到了数据，就把它存起来
        save_to_cache(ticker, overview_data)
        print(f"💾 [数据持久化] 基本面数据已保存至缓存: {ticker}")
        
        return overview_data

    except Exception as e:
        print(f"❌ [网络错误] 获取 {ticker} 基本面失败: {e}")
        return None

if __name__ == "__main__":
    # 单独测试这个工具
    data = get_company_overview("NVDA")
    if data:
        print(f"✅ 成功拿到 {data.get('Symbol')} 基本面！当前市盈率(PE): {data.get('PERatio')}")