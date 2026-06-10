import json
import os

CACHE_DIR = "data_cache"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def save_to_cache(ticker: str, data: dict):
    """把股票数据存成 JSON 文件"""
    file_path = os.path.join(CACHE_DIR, f"{ticker}.json")
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4) 
    print(f"💾 数据已存入: {file_path}")

def load_from_cache(ticker: str):
    """从本地读取数据"""
    file_path = os.path.join(CACHE_DIR, f"{ticker}.json")
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return None