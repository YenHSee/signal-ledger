import os
from dotenv import load_dotenv

load_dotenv()

class AppConfig:
    @property
    def APP_MODE(self):
        return os.getenv("APP_MODE", "live").strip().lower()

    @property
    def ALPHA_VANTAGE_API_KEY(self):
        key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not key:
            raise ValueError("ALPHA_VANTAGE_API_KEY is missing. Check your .env file.")
        return key
    
    @property
    def FINNHUB_API_KEY(self):
        # Optional: the ETL pipeline skips news ingestion when this is not set.
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
            raise ValueError("DB_PASSWORD is missing. Check your .env file.")
        return pwd

    @property
    def DB_HOST(self):
        return os.getenv("DB_HOST", "127.0.0.1")

    @property
    def DB_PORT(self):
        return os.getenv("DB_PORT", "5432")

    @property
    def DB_NAME(self):
        return os.getenv("DB_NAME", "signal_ledger")

    @property
    def CF_ACCOUNT_ID(self):
        return os.getenv("CF_ACCOUNT_ID")

    @property
    def CF_NAMESPACE_ID(self):
        # Optional: cache_manager skips Cloudflare KV when this is not set.
        return os.getenv("CF_NAMESPACE_ID")

    @property
    def CF_API_TOKEN(self):
        # Optional: cache_manager skips Cloudflare KV when this is not set.
        return os.getenv("CF_API_TOKEN")
    
config = AppConfig()
