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
# ==========================================
class InvestmentReport(BaseModel):
    conclusion: str = Field(description="必须严格输出：BUY, HOLD 或 SELL")
    target_price: str = Field(description="分析师目标价，例如 '$150' 或 'N/A'")
    reasoning: str = Field(description="300字以内的核心投资逻辑分析")
    risk_level: str = Field(description="风险等级: High, Medium, Low")
    full_report: str = Field(
        description="完整的 Markdown 格式分析内容，必须包含：1.业务概览与护城河 2.财务健康度深度剖析(引用真实数据) 3.投资风险与展望。字数不少于500字，必须使用多级标题和列表。"
    )
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ==========================================
# 2. 组装 AI 智能体工厂 (LangGraph 引擎)
# ==========================================
def create_analyst_agent():
    """初始化并返回一个配置好的金融分析师 LangGraph 引擎和 Parser"""
    
    llm = get_llm(tier=ModelTier.LOCAL, temperature=0.1)
    tools = get_all_tools()
    parser = PydanticOutputParser(pydantic_object=InvestmentReport)
    
    # LangGraph 直接把系统提示词当做 state_modifier 传进去，极其优雅
    system_prompt = f"""你是一个面向顶级投行客户的首席量化与基本面分析师。
    
    【核心数据来源 - 严禁乱编】：
    用户已经为你准备好了这只股票的最新基本面、估值、机构持股以及技术面指标数据。
    你必须且只能基于用户发给你的 JSON 数据来进行推理分析！不要自己去幻想或查找额外的财务数据！
    
    【严格输出要求 - 致命规则】：
    你必须严格按照以下 JSON 格式返回结果，作为你唯一的最终输出。
    绝不允许在 JSON 前后输出任何思考过程、Markdown 标记（如 ```json）或问候语！
    
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