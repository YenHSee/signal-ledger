import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not ALPHA_VANTAGE_API_KEY:
        raise ValueError("❌ 错误: 未找到 ALPHA_VANTAGE_API_KEY，请检查 .env 文件")
    
    MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "ollama")