from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from core.llm_factory import get_llm

@tool
def get_stock_price(ticker: str) -> str:
    """根据股票代码 (ticker) 获取最新的股票价格。"""
    prices = {"NVDA": "120.50", "AAPL": "190.00"}
    price = prices.get(ticker.upper(), "未知")
    return f"{ticker} 的当前价格是 {price} 美元。"
    
llm = get_llm()

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个资深的金融分析师助理。请使用你手头的工具来准确回答用户的问题。"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"), 
])

tools = [get_stock_price]
agent = create_tool_calling_agent(llm, tools, prompt)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

if __name__ == "__main__":
    print("\n🚀 Agent 启动！正在提出问题...")
    response = agent_executor.invoke({"input": "请帮我查一下 NVDA 现在的价格是多少？"})
    print("\n✅ 最终输出结果给前端:")
    print(response["output"])


executor = AgentExecutor(agent=agent, tools=tools, verbose=True)