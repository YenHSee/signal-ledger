import requests
import json
from langchain.tools import tool
from config import Config
from dotenv import load_dotenv
import os

load_dotenv()
# 假设你在 config.py 里加了 PERPLEXITY_API_KEY
# PERPLEXITY_API_KEY = "pplx-xxxxxxxxxxxxxxxxxxxx"

@tool
def get_latest_market_news(ticker: str) -> str:
    """
    当你需要了解公司的最新新闻、突发事件、财报电话会议摘要或市场情绪时，调用此工具。
    输入参数为股票代码 (例如 NVDA, AAPL)。
    """
    print(f"🕵️‍♂️ [Perplexity 搜索] 正在全网检索 {ticker} 的最新情报...")
    
    url = "https://api.perplexity.ai/chat/completions"
    
    # 构造给 Perplexity 的检索指令
    payload = {
        "model": "llama-3.1-sonar-small-128k-online", # 这是它最新的联网搜索模型
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的华尔街情报收集员。请在全网搜索该公司的最新动态。请提供准确、客观的摘要，并重点关注：1. 突发新闻或财报 2. 高管变动或并购 3. 供应链异动 4. 华尔街机构评级变化。字数控制在 300 字以内。"
            },
            {
                "role": "user",
                "content": f"帮我搜索关于 {ticker} 过去一周的最核心市场动态。"
            }
        ],
        "temperature": 0.2 # 保持低温度，确保新闻客观不瞎编
    }
    
    headers = {
        "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        
        # 提取总结好的新闻情报
        news_summary = response_data['choices'][0]['message']['content']
        print(f"✅ [Perplexity 搜索完成] 已获取 {ticker} 最新情报！")
        return news_summary
        
    except Exception as e:
        print(f"⚠️ [Perplexity 警告] 检索失败: {e}")
        return f"无法获取 {ticker} 的最新新闻，请依赖现有财务数据进行分析。"