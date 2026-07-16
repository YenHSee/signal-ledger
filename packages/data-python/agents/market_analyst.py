from pydantic import BaseModel, Field

from langgraph.prebuilt import create_react_agent
from langchain_core.output_parsers import PydanticOutputParser

from core.llm_factory import get_llm, ModelTier


class InvestmentReport(BaseModel):
    conclusion: str = Field(description="BUY, HOLD, or SELL")
    conviction_level: str = Field(description="High, Medium, or Low conviction")
    target_price: str = Field(description="12-month target price")
    upside_downside_pct: str = Field(description="Potential return, for example '+15.5%'")
    reasoning: str = Field(description="Core investment rationale in no more than 200 words")
    risk_level: str = Field(description="High, Medium, Low")
    full_report: str = Field(
        description="""An institutional-style Markdown research report containing:
        1. Executive Summary
        2. Business and Revenue Mix
        3. Financial Performance, with a table of key metrics
        4. Valuation Analysis using the supplied valuation metrics
        5. Bull, Base, and Bear Scenarios
        6. Key Risks and Probability
        Use clear headings and an analytical, precise, professional tone."""
    )


def create_analyst_agent(tier: ModelTier = ModelTier.LOCAL):
    """Create the financial analyst graph and its structured-output parser."""
    
    llm = get_llm(tier=tier, temperature=0.1)
    tools = []
    parser = PydanticOutputParser(pydantic_object=InvestmentReport)
    
    system_prompt = f"""You are a fundamental and quantitative equity research analyst.
        Write in English with an analytical, precise, evidence-driven tone. Avoid marketing
        language and unsupported certainty.

        DATA BOUNDARIES
        The user supplies a JSON snapshot containing fundamentals, valuation, ownership,
        technical indicators, and possibly recent news. Use only the supplied snapshot for
        company-specific facts and calculations. You may use general financial knowledge to
        explain concepts, but never invent company figures, events, or sources. Treat missing
        values as unavailable rather than zero unless the snapshot explicitly supplies zero.

        ANALYSIS FRAMEWORK
        1. Compare trailing and forward P/E with revenue and earnings growth. Explain whether
           the valuation appears supported by the supplied growth metrics.
        2. Combine the 50-day and 200-day moving averages with the 52-week range position to
           describe momentum without presenting technical signals as certainty.
        3. Compare the supplied analyst target with the current price and evaluate the implied
           upside or downside and the associated risk/reward.
        4. If `recent_catalysts` contains news items, cite their exact date, source, and headline.
           If it is empty, do not invent news or catalysts.
        5. State material data limitations and reduce conviction when important evidence is
           missing or stale.

        FULL_REPORT REQUIREMENTS
        The `full_report` value must be valid Markdown and contain these sections:
        - Executive Summary: one concise conclusion and its supporting rationale.
        - Business Moat and Catalysts: business model, competitive context, and supplied news.
        - Financial and Valuation Analysis: a Markdown table of supplied key metrics.
        - Bull, Base, and Bear Scenarios: explicit assumptions for each scenario.
        - Risk Assessment: two or three material risks with High, Medium, or Low probability.
        - Data Limitations: important missing or stale inputs that affect confidence.

        OUTPUT RULES
        Return only JSON that conforms to the schema below. Do not add code fences,
        commentary, reasoning traces, greetings, or text outside the JSON object.
        
        {parser.get_format_instructions()}
        """
    
    executor = create_react_agent(
        model=llm, 
        tools=tools, 
        prompt=system_prompt
    )
    
    return executor, parser
