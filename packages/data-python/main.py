from tools.alpha_vantage import get_stock_data
from agents.market_analyst import executor, parser
from core.cache_manager import save_to_cache, load_from_cache
from utils.storage import save_analysis_report

def analyze_ticker(ticker: str):
    print(f"\n🚀 终端请求：开始深度调查 {ticker}")
    
    result = executor.invoke({
        "input": f"客户想要投资 {ticker}，请动用工具帮我做一份尽职调查报告。"
    })
    
    try:
        # 1. 强制解析 AI 输出为结构化 Pydantic 对象
        final_parsed_obj = parser.parse(result["output"])
        # 将 Pydantic 对象转换为普通的 Python 字典，方便后面存 JSON
        final_json_dict = final_parsed_obj.dict() 
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        return {"error": "AI 输出解析失败"}

    # 2. 提取底层数据
    raw_data = load_from_cache(ticker) 
    if not raw_data:
        raw_data = {"status": "unlisted", "note": f"No public financial data available for {ticker} (Alternative data used)."}

    # 3. ⭐️ 先保存到硬盘！(这里把解析好的字典传过去)
    save_analysis_report(ticker, final_json_dict, raw_data)
    print(f"✅ {ticker} 研报已生成！")

    # 4. ⭐️ 最后再 return 给后端 API (Node.js)，让它发给前端
    return final_json_dict

if __name__ == "__main__":
    analyze_ticker("NVDA")
    # analyze_ticker("SpaceX")