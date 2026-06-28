import json
import os
import time
import sys
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

CACHE_DIR = "data_cache"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_filename(ticker: str) -> str:
    """生成固定的缓存文件名，例如: NVDA.json"""
    return os.path.join(CACHE_DIR, f"{ticker.upper()}.json")

# Local
def save_to_local_cache(ticker: str, data: dict):
    """把股票数据存入缓存，直接覆盖旧文件"""
    file_path = get_cache_filename(ticker)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4) 
        
    print(f"💾 数据已更新至本地缓存: {file_path}")

def load_from_local_cache(ticker: str, max_age_days: int = 7):
    """
    尝试读取缓存数据。
    如果文件存在且距今不到 max_age_days 天，则命中缓存；
    如果文件太老或不存在，则返回 None 强制重新抓取。
    """
    file_path = get_cache_filename(ticker)
    
    # 1. 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"🔍 [缓存未命中] 本地没有 {ticker.upper()} 的数据")
        return None
        
    # 2. 检查文件有多“老”
    file_mod_time = os.path.getmtime(file_path) # 获取文件的最后修改时间
    current_time = time.time()
    
    # 计算文件存在了几天
    age_in_days = (current_time - file_mod_time) / (24 * 3600)
    
    # 3. 判断是否过期
    if age_in_days > max_age_days:
        print(f"♻️ [缓存过期] {ticker.upper()} 的数据已经是 {age_in_days:.1f} 天前的了，需要重新获取")
        return None
        
    # 4. 文件新鲜，直接返回
    print(f"⚡ [缓存命中] {ticker.upper()} 的数据很新鲜 (仅 {age_in_days:.1f} 天)，直接使用！")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
    
# Cloud
def save_to_kv_cache(ticker: str, data: dict, max_age_days: int = 7):
    if not config.CF_API_TOKEN or not config.CF_NAMESPACE_ID:
        return
    ticker = ticker.upper()
    ttl_seconds = int(max_age_days * 24 * 3600)
    url = f"https://api.cloudflare.com/client/v4/accounts/{config.CF_ACCOUNT_ID}/storage/kv/namespaces/{config.CF_NAMESPACE_ID}/values/{ticker}?expiration_ttl={ttl_seconds}"
    headers = {"Authorization": f"Bearer {config.CF_API_TOKEN}", "Content-Type": "application/json"}
    try:
        response = requests.put(url, headers=headers, data=json.dumps(data, ensure_ascii=False))
        if response.status_code == 200:
            print(f"🧊 [KV缓存写入] {ticker} 已存入 Cloudflare (TTL: {max_age_days}天)")
    except Exception as e:
        print(f"❌ 写入 KV 网络异常: {e}")

def load_from_kv_cache(ticker: str):
    if not config.CF_API_TOKEN or not config.CF_NAMESPACE_ID:
        return None
    ticker = ticker.upper()
    url = f"https://api.cloudflare.com/client/v4/accounts/{config.CF_ACCOUNT_ID}/storage/kv/namespaces/{config.CF_NAMESPACE_ID}/values/{ticker}"
    headers = {"Authorization": f"Bearer {config.CF_API_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print(f"⚡ [KV缓存命中] {ticker} 极速读取成功！")
            return response.json()
    except Exception as e:
        pass
    return None