import os
from datetime import datetime
from pydantic import BaseModel, Field

# 🌟 抛弃旧时代的 AgentExecutor，引入最新的 LangGraph 引擎
from langgraph.prebuilt import create_react_agent
from langchain_core.output_parsers import PydanticOutputParser

# 你的本地核心模块
from core.llm_factory import get_llm, ModelTier
from tools.tool_registry import get_all_tools

# ==========================================
# 1. 定义数据结构的“宪兵” (Pydantic Schema)
class InvestmentReport(BaseModel):
    conclusion: str = Field(description="BUY, HOLD 或 SELL")
    conviction_level: str = Field(description="你的评级信念度：High, Medium, Low") # 🌟 偷来的亮点
    target_price: str = Field(description="12个月目标价")
    upside_downside_pct: str = Field(description="潜在涨跌幅，例如 '+15.5%'") # 🌟 偷来的亮点
    reasoning: str = Field(description="300字以内的核心逻辑")
    risk_level: str = Field(description="High, Medium, Low")
    full_report: str = Field(
        description="""完整的机构级Markdown研报，必须且严格包含以下模块：
        1. Executive Summary (执行摘要)
        2. Business & Revenue Mix (业务与营收拆解)
        3. Financial Performance (财务健康度，必须使用表格呈现关键指标)
        4. Valuation Analysis (估值分析，结合 PE/PEG 及历史均值)
        5. Bull/Base/Bear Scenarios (牛/熊/基准三种情景推演)
        6. Key Risks & Probability (核心风险及其发生概率)
        必须使用多级标题，语调要求：Analytical, precise, institutional (分析性强、精准、机构做派)。"""
    )
# ==========================================
# 2. 组装 AI 智能体工厂 (LangGraph 引擎)
# ==========================================
def create_analyst_agent(tier: ModelTier = ModelTier.LOCAL):
    """初始化并返回一个配置好的金融分析师 LangGraph 引擎和 Parser"""
    
    llm = get_llm(tier=tier, temperature=0.1)
    tools = get_all_tools()
    parser = PydanticOutputParser(pydantic_object=InvestmentReport)
    
    # LangGraph 直接把系统提示词当做 state_modifier 传进去，极其优雅
    system_prompt = f"""你是一个面向全球顶级量化对冲基金（如 Citadel, Two Sigma）的首席量化与基本面分析师。你的语言风格必须极其专业、冷酷、数据驱动，绝不使用任何营销或主观抒情词汇。
        
        【核心数据限制 - 严禁幻觉】：
        用户会为你提供目标股票的最新基本面、估值、机构持股以及技术面指标数据（JSON格式）。
        你必须且只能基于这些传入的数据进行测算！绝不能幻想财务数据。但你可以调用你内在的金融常识（如行业竞争格局、宏观经济背景）来辅助解释这些数据。
        
        【深度投研分析框架 - 你必须遵循以下逻辑进行思考】：
        1. 估值审视：不要只念数字，要对比 trailing_pe 和 forward_pe，结合 revenue_growth_yoy 来判断是否存在“戴维斯双击”或“估值陷阱”。
        2. 技术面结合基本面：结合 50日/200日均线 和 52周位置，判断目前是“左侧抄底”、“右侧追涨”还是“破位止损”。
        3. 胜率与盈亏比：参考分析师目标价 (analyst_target_price) 与当前价的距离，评估潜在的上行/下行空间。
        
        【对于 full_report 字段的硬性排版要求】：
        在生成 JSON 中的 `full_report` 字段时，你必须使用高级 Markdown 格式，并且必须包含以下 5 个核心章节：
        - **📌 Executive Summary (执行摘要)**：一句话核心结论与评级逻辑。
        - **🏢 Business Moat & Catalysts (护城河与催化剂)**：该公司的核心商业模式，以及近期可能推动股价的催化剂。
        - **📊 Financial & Valuation (财务与估值剖析)**：强制要求使用 Markdown 表格 总结核心财务指标，并给出专业点评。
        - **⚖️ Bull & Bear Scenarios (牛熊情景推演)**：分别推演在最乐观和最悲观情况下的股价预期。
        - **⚠️ Risk Assessment (核心风险提示)**：列出 2-3 个重大风险，并给出发生概率（高/中/低）。

        【致命输出规则】：
        你必须严格按照以下指定的 JSON Schema 返回结果，作为你唯一的最终输出。
        绝不允许在 JSON 前后输出任何思考过程、Markdown 标记（如 ```json）或问候语！如果不遵守，系统将崩溃！
        
        {parser.get_format_instructions()}
        """
    
    # 🌟 核心：使用 LangGraph 引擎创建 Agent (自带工具调用循环防崩溃机制)
    executor = create_react_agent(
        model=llm, 
        tools=tools, 
        prompt=system_prompt
    )
    
    return executor, parser

# ==========================================
# 3. 暴露给外部调用的实例
# ==========================================
executor, parser = create_analyst_agent()