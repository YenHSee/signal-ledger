import os
import sys
import time
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

FINNHUB_COMPANY_NEWS_URL = "https://finnhub.io/api/v1/company-news"

# Finnhub 免费版限 60 calls/分钟，稳妥起见 pacing 到 ~1 call/秒
_MIN_CALL_INTERVAL_SECONDS = 1.0
_last_call_at = 0.0


def _pace():
    """简单的全局 rate-limit pacing，保证两次请求间隔至少 1 秒"""
    global _last_call_at
    elapsed = time.time() - _last_call_at
    if elapsed < _MIN_CALL_INTERVAL_SECONDS:
        time.sleep(_MIN_CALL_INTERVAL_SECONDS - elapsed)
    _last_call_at = time.time()


def get_company_news(symbol: str, from_date: str, to_date: str, max_retries: int = 2):
    """
    调 Finnhub company-news 接口，拉取一支股票在 [from_date, to_date] 区间的新闻。
    日期格式均为 YYYY-MM-DD。返回原始新闻 dict 列表；失败时重试，最终失败返回空列表（跳过该股票）。
    """
    api_key = config.FINNHUB_API_KEY
    if not api_key:
        print("⚠️ [Finnhub] 未配置 FINNHUB_API_KEY，跳过新闻拉取")
        return []

    symbol = symbol.upper()
    params = {"symbol": symbol, "from": from_date, "to": to_date, "token": api_key}

    for attempt in range(max_retries + 1):
        _pace()
        try:
            response = requests.get(FINNHUB_COMPANY_NEWS_URL, params=params, timeout=15)

            # 429 = 触发限流，等一会再试
            if response.status_code == 429:
                print(f"⚠️ [Finnhub] {symbol} 触发限流 (429)，等待 15 秒后重试...")
                time.sleep(15)
                continue

            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list):
                print(f"⚠️ [Finnhub] {symbol} 返回异常结构: {data}")
                return []

            return data

        except Exception as e:
            if attempt < max_retries:
                print(f"⚠️ [Finnhub] {symbol} 第 {attempt + 1} 次请求失败: {e}，重试中...")
                time.sleep(2)
            else:
                print(f"❌ [Finnhub] {symbol} 新闻拉取最终失败，跳过: {e}")

    return []


if __name__ == "__main__":
    from datetime import date, timedelta

    today = date.today()
    news = get_company_news("AAPL", (today - timedelta(days=3)).isoformat(), today.isoformat())
    print(f"✅ 拿到 {len(news)} 条 AAPL 新闻")
    for item in news[:3]:
        print(f"  - [{item.get('source')}] {item.get('headline')}")
