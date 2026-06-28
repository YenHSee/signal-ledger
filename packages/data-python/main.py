# main.py
import os
import sys
import time
import json  # 🌟 必须引入 json 处理字典转化

# 确保能正常导入核心模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.market_analyst import create_analyst_agent
from utils.storage import save_analysis_report, build_ai_context, insert_investment_report, init_db_pool, close_db_pool
from core.llm_factory import ModelTier

CHOSEN_TIER = ModelTier.NORMAL
TIER_LETTER_MAP = {
    ModelTier.SMART: "S",
    ModelTier.NORMAL: "N",
    ModelTier.LOCAL: "L"
}
model_letter = TIER_LETTER_MAP.get(CHOSEN_TIER, "U")
# ==========================================
# 🧠 全局初始化：唤醒 AI
# ==========================================
print("🔄 正在初始化 AI 投行分析师...")
try:
    executor, parser = create_analyst_agent(tier=CHOSEN_TIER)
    print("✅ AI 投行分析师已就位！\n")
except Exception as e:
    print(f"❌ 致命错误：无法唤醒 AI 智能体: {e}")
    sys.exit(1)


def run_analysis(tickers: list):
    """
    终极研报流水线：无论你传 1 个还是 500 个 Ticker，它都能完美消化。
    """
    print(f"📋 研报生成任务启动！共需处理 {len(tickers)} 支股票。")
    init_db_pool(min_conn=1, max_conn=5)

    results = {}
    success_count = 0
    failed_tickers = []

    for index, ticker in enumerate(tickers):
        ticker = ticker.upper()
        print(f"\n" + "="*60)
        print(f"🚀 进度: [{index + 1}/{len(tickers)}] 开始深度调查: {ticker}")
        print("="*60)
        
        # 🌟 步骤 A: 读时计算！在数据库里秒级组装最新数据
        raw_data = build_ai_context(ticker) 
        if not raw_data:
            print(f"⚠️ 警告: 数据库中未找到 {ticker} 的完整数据，将依赖 AI 自行搜索。")
            raw_data = {"status": "unlisted_or_missing", "note": f"No internal data for {ticker}."}

        try:
            # 🌟 步骤 B: 喂给大模型！
            ai_prompt = f"""
            客户想要投资 {ticker}。
            这是量化系统刚刚为你准备好的核心财务与技术指标数据：
            {json.dumps(raw_data, indent=2, ensure_ascii=False)}
            
            请结合上述数据，并动用你的工具，做一份尽职调查报告。
            """
            
            # 🌟 引擎升级了，现在的调用格式是以消息(messages)的形式传入
            result = executor.invoke({"messages": [("user", ai_prompt)]})
            
            # 🌟 LangGraph 返回的是一个消息流，最后一条消息(messages[-1])就是 AI 的最终结论
            ai_output_text = result["messages"][-1].content
            
            # 🌟 步骤 C: 解析为结构化字典
            final_parsed_obj = parser.parse(ai_output_text)
            if hasattr(final_parsed_obj, 'model_dump'):
                final_json_dict = final_parsed_obj.model_dump()
            else:
                final_json_dict = final_parsed_obj.dict()
                
        except Exception as e:
            print(f"❌ {ticker} AI 推理或结构化解析失败: {e}")
            results[ticker] = {"error": "AI 输出解析失败", "details": str(e)}
            failed_tickers.append(ticker)
            continue # 失败了就跳过，绝对不能阻断下一只股票！

        # 🌟 步骤 D: 落盘持久化
        try:
            # 1. 存本地 JSON 文件 (保留原来的物理备份)
            save_analysis_report(ticker, final_json_dict, raw_data, model_letter)
            
            # 2. 存进 Supabase 数据库 (全新的工业级流程！)
            is_saved = insert_investment_report(ticker, final_json_dict, raw_data, model_letter)
            
            if is_saved:
                print(f"💾 ✨ 成功！{ticker} 研报已安全写入本地及 Supabase 数据库！")
                success_count += 1
                results[ticker] = final_json_dict
            else:
                failed_tickers.append(ticker)

        except Exception as e:
            print(f"⚠️ 警告：{ticker} 保存落盘失败: {e}")
            failed_tickers.append(ticker)

        # 🌟 步骤 E: 连续调用的冷却保护机制
        if index < len(tickers) - 1:
            print("💤 冷却 5 秒钟，防止 GPU 过热及 API 被风控...")
            time.sleep(5)

    # 任务总结汇报
    print("\n" + "#"*60)
    print(f"🎉 任务完美收官！成功生成: {success_count} 份，失败: {len(failed_tickers)} 份")
    if failed_tickers:
        print(f"⚠️ 失败名单请核查: {failed_tickers}")
    print("#"*60)
    close_db_pool()
    
    return results


# ==========================================
# 🎮 测试触发区
# ==========================================
if __name__ == "__main__":
    # 想要单跑一个？就写 ["NVDA"]
    # 想要跑科技七姐妹？全塞进去！
    target_ticker_list = [
        "AAPL"
    ]
    
    run_analysis(target_ticker_list)