def transform_to_report(raw_json: dict):
    return {
        "ticker": raw_json["Symbol"],
        "indicators": {
            "peRatio": float(raw_json["PERatio"]),
            "rsi": 0, 
            "isOverbought": False
        },
        "decision": {
            "action": "HOLD", 
            "reasoning": "待 AI 生成",
            "confidence": 0
        }
    }