import json
import os
from datetime import datetime

def save_analysis_report(ticker: str, analysis_output: str, raw_data: dict):
    """将分析结果和原始数据存为一个结构化的 JSON 文件"""
    report = {
        "ticker": ticker,
        "timestamp": datetime.now().isoformat(),
        "ai_analysis": analysis_output,
        "raw_financial_data": raw_data
    }
    
    # 存入 reports/ 文件夹
    output_dir = "reports"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    file_path = os.path.join(output_dir, f"{ticker}_report.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
    
    print(f"✅ 报告已持久化: {file_path}")