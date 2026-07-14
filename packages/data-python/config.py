import os
from dotenv import load_dotenv

load_dotenv()

class AppConfig:
    @property
    def ALPHA_VANTAGE_API_KEY(self):
        key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not key:
            raise ValueError("❌ 错误: 未找到 ALPHA_VANTAGE_API_KEY，请检查 .env 文件")
        return key
    
    @property
    def FINNHUB_API_KEY(self):
        # 可选配置：没配 key 时 ETL 的 news step 会自动跳过，不影响主流水线
        return os.getenv("FINNHUB_API_KEY")

    @property
    def MODEL_PROVIDER(self):
        return os.getenv("MODEL_PROVIDER", "ollama")

    @property
    def DB_USER(self):
        return os.getenv("DB_USER", "postgres")

    @property
    def DB_PASSWORD(self):
        pwd = os.getenv("DB_PASSWORD")
        if not pwd:
            raise ValueError("❌ 错误: 未找到数据库密码 DB_PASSWORD，请检查 .env 文件")
        return pwd

    @property
    def DB_HOST(self):
        return os.getenv("DB_HOST", "127.0.0.1")

    @property
    def DB_PORT(self):
        return os.getenv("DB_PORT", "5432")

    @property
    def DB_NAME(self):
        return os.getenv("DB_NAME", "stock_analyst")

    @property
    def CF_ACCOUNT_ID(self):
        return os.getenv("CF_ACCOUNT_ID", "07c8bbd98aac574bd75ddfa1cb030163")

    @property
    def CF_NAMESPACE_ID(self):
        # 可选配置：没配 key 时 cache_manager 会自动跳过 KV 缓存，不影响主流水线
        return os.getenv("CF_NAMESPACE_ID")

    @property
    def CF_API_TOKEN(self):
        # 可选配置：没配 key 时 cache_manager 会自动跳过 KV 缓存，不影响主流水线
        return os.getenv("CF_API_TOKEN")
    
# 在底部实例化一个配置对象，导出给其他文件使用
config = AppConfig()