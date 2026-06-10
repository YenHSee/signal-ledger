from tools.alpha_vantage import get_stock_data
from agents.first_agent import executor
from core.cache_manager import save_to_cache, load_from_cache
from utils.storage import save_analysis_report

def run_pipeline(ticker: str):
    print(f"🚀 开始分析股票: {ticker}")
    data = get_stock_data(ticker)
    
    if data:
        print("🤖 AI 正在推理分析...")
        prompt_text = f"""
        请分析 {ticker} 的基本面，基于以下数据: {str(data)[:2000]}
        请直接给出 Buy/Hold/Sell 建议及分析理由。
        """
        result = executor.invoke({"input": prompt_text})
        
        print("\n✅ 分析完成，输出结论:")
        # print(result["output"])
        save_analysis_report(ticker, result["output"], data)
        print("\n🎉 分析已完成并存入 JSON!")
    else:
        print("❌ 获取数据失败，无法进行分析。")

if __name__ == "__main__":
    target_ticker = "NVDA"
    run_pipeline(target_ticker)