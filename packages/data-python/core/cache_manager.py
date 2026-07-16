import json
import os
import sys
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

def save_to_kv_cache(ticker: str, data: dict, max_age_days: int = 7):
    if not all((config.CF_ACCOUNT_ID, config.CF_NAMESPACE_ID, config.CF_API_TOKEN)):
        return
    ticker = ticker.upper()
    ttl_seconds = int(max_age_days * 24 * 3600)
    url = f"https://api.cloudflare.com/client/v4/accounts/{config.CF_ACCOUNT_ID}/storage/kv/namespaces/{config.CF_NAMESPACE_ID}/values/{ticker}?expiration_ttl={ttl_seconds}"
    headers = {"Authorization": f"Bearer {config.CF_API_TOKEN}", "Content-Type": "application/json"}
    try:
        response = requests.put(
            url,
            headers=headers,
            data=json.dumps(data, ensure_ascii=False),
            timeout=15,
        )
        if response.status_code == 200:
            print(f"🧊 [KV cache] Stored {ticker} in Cloudflare (TTL: {max_age_days} days)")
    except Exception as e:
        print(f"❌ Failed to write to Cloudflare KV: {e}")

def load_from_kv_cache(ticker: str):
    if not all((config.CF_ACCOUNT_ID, config.CF_NAMESPACE_ID, config.CF_API_TOKEN)):
        return None
    ticker = ticker.upper()
    url = f"https://api.cloudflare.com/client/v4/accounts/{config.CF_ACCOUNT_ID}/storage/kv/namespaces/{config.CF_NAMESPACE_ID}/values/{ticker}"
    headers = {"Authorization": f"Bearer {config.CF_API_TOKEN}"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            print(f"⚡ [KV cache] Cache hit for {ticker}")
            return response.json()
    except Exception as e:
        print(f"⚠️ Failed to read from Cloudflare KV: {e}")
    return None
