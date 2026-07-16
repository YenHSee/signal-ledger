import os
from enum import Enum


class ModelTier(Enum):
    SMART = "smart"     # Highest-quality model
    NORMAL = "normal"   # Cost-effective hosted model
    LOCAL = "local"     # Local model

def get_llm(tier: ModelTier = ModelTier.NORMAL, temperature: float = 0):
    """Return the configured model for the requested tier."""
    
    if tier == ModelTier.SMART:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"), temperature=temperature)
    
    elif tier == ModelTier.NORMAL:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="deepseek-chat", 
            api_key=os.getenv("DEEPSEEK_API_KEY"), 
            base_url="https://api.deepseek.com",
            temperature=temperature
        )
        
    else:
        from langchain_ollama import ChatOllama
        return ChatOllama(model="qwen2.5:7b", temperature=temperature)
