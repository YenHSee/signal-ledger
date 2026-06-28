import os
from enum import Enum


class ModelTier(Enum):
    SMART = "smart"     # 顶级模型
    NORMAL = "normal"   # 性价比模型
    LOCAL = "local"     # 本地免费模型

def get_llm(tier: ModelTier = ModelTier.NORMAL, temperature: float = 0):
    """根据传入的等级，返回对应的模型"""
    
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