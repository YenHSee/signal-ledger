import json
import os
from datetime import datetime

CACHE_DIR = "data_cache"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_daily_filename(ticker: str) -> str:
    """生成当天的缓存文件名，例如: 2026-06-17_NVDA_cache.json"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(CACHE_DIR, f"{date_str}_{ticker.upper()}_cache.json")

def save_to_cache(ticker: str, data: dict):
    """把股票数据存成带有当天日期的 JSON 文件"""
    file_path = get_daily_filename(ticker)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4) 
    print(f"💾 数据已存入当日缓存: {file_path}")

def load_from_cache(ticker: str):
    """尝试读取【今天】的缓存数据"""
    file_path = get_daily_filename(ticker)
    
    if os.path.exists(file_path):
        print(f"⚡ [缓存命中] 发现今日数据，无需消耗 API")
        with open(file_path, "r") as f:
            return json.load(f)
            
    print(f"🔍 [缓存未命中] 今日尚未获取 {ticker.upper()} 的数据")
    return None