import json
import os
import sys
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

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