from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from core.llm_factory import get_llm
from tools.tool_registry import get_all_tools
from pydantic import BaseModel, Field
from datetime import datetime # ⭐️ 必须引入

class InvestmentReport(BaseModel):
    conclusion: str = Field(description="必须是 BUY, HOLD 或 SELL")
    target_price: str = Field(description="分析师目标价")
    reasoning: str = Field(description="300字以内的投资逻辑分析")
    risk_level: str = Field(description="风险等级: High, Medium, Low")
    full_report: str = Field(description="完整的 Markdown 格式分析内容，必须包含公司的核心业务分析、财务数据深度解读、以及潜在风险提示。字数不得少于 500 字，必须使用多级标题和列表。")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat()) # ⭐️ AI 生成的具体时间

def create_analyst_agent():
    """初始化并返回一个配置好的金融分析师 Agent Executor"""
    llm = get_llm()
    tools = get_all_tools()
    
    # ⭐️ 必须先定义 parser！
    parser = PydanticOutputParser(pydantic_object=InvestmentReport)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个面向顶级投行客户的量化与基本面分析师。你的任务是基于手头工具收集到的数据，直接向客户交付最终的投资研报。
        
        【报告撰写标准】:
        在 `full_report` 字段中，你必须写出一份详尽的、排版精美的 Markdown 报告。报告必须包含：
        1. 业务概览与护城河分析
        2. 财务健康度深度剖析（引用 PE、利润率等数据）
        3. 投资风险与未来展望
        严禁只写一两句话敷衍了事！必须分段、使用加粗和列表。

        请严格按照以下 JSON 格式要求输出你的最终分析：
        {format_instructions}

        【分析策略】：
        - 如果是上市公司，请利用 Alpha Vantage 的财务数据进行计算和推演。
        - 如果是未上市公司 (如 SpaceX)，请生成另类投资策略（例如推荐竞品 RKLB 或相关供应链股）。
        """),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"), 
    ])

    # 注入 JSON 格式指令
    prompt = prompt.partial(format_instructions=parser.get_format_instructions())
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    return AgentExecutor(agent=agent, tools=tools, verbose=True), parser

executor, parser = create_analyst_agent()