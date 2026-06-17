import json
import os
from datetime import datetime

def save_analysis_report(ticker: str, analysis_output: dict, raw_data: dict):
    """将分析结果和原始数据存为一个结构化的 JSON 文件"""
    
    # 文件名只要年月日 (方便排序和查找)
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # ⭐️ 内部自带精确到秒的 timestamp，给前端用的！
    exact_time = datetime.now().isoformat() 

    report = {
        "ticker": ticker.upper(),
        "timestamp": exact_time,          # 明确的生成时间
        "ai_analysis": analysis_output,   # 这里面也有 generated_at，双保险
        "raw_financial_data": raw_data
    }
    
    output_dir = "reports"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    file_path = os.path.join(output_dir, f"{date_str}_{ticker.upper()}_report.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
    
    print(f"✅ 研报已持久化 (保留历史): {file_path}")