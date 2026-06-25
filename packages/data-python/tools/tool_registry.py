from langchain_core.tools import tool
from tools.alpha_vantage import get_company_overview
from tools.alt_data import get_private_company_data

@tool
def analyze_public_stock(ticker: str) -> str:
    """
    必须优先使用此工具！
    用于获取公开上市公司 (如 NVDA, AAPL) 的真实财务数据。
    如果返回空数据或失败，说明该公司可能未上市，请放弃此工具。
    """
    data = get_company_overview(ticker)
    if not data or "Error Message" in data:
        return "未能找到该公司的公开市场数据。它可能是私有公司，请立刻改用 analyze_private_company 工具。"
    return str(data)


@tool
def analyze_private_company(company_name: str) -> str:
    """
    备用雷达工具！
    仅当目标公司未上市 (如 SpaceX, OpenAI, 字节跳动) 或 analyze_public_stock 失败时，才使用此工具。
    它会全网检索另类数据和私募估值。
    """
    data = get_private_company_data(company_name)
    return str(data)

def get_all_tools():
    return []