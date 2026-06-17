import os

def get_llm():
    model_provider = os.getenv("MODEL_PROVIDER", "ollama")
    
    if model_provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
    
    elif model_provider == "deepseek":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
        
    else:
        from langchain_ollama import ChatOllama
        return ChatOllama(model="qwen2.5:7b", temperature=0)