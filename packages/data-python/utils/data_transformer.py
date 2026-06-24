# Helper Function
def _safe_float(value):
    if not value or value in ["None", "N/A"]: return None
    try: return float(value)
    except ValueError: return None


def _safe_int(value):
    if not value or value in ["None", "N/A"]: return None
    try: return int(value)
    except ValueError: return None


def _safe_date(value):
    if not value or value in ["None", "N/A"]: return None
    return value


def transform_alpha_overview_to_db(raw_json: dict) -> dict:
    """
    把 Alpha Vantage 的 PascalCase 格式，转换为
    PostgreSQL 数据库需要的全小写下划线(snake_case)格式，并做好类型转换。
    """
    if not raw_json or "Symbol" not in raw_json:
        return {}
        
    return {
        "symbol": raw_json["Symbol"].upper(),
        "asset_type": raw_json.get("AssetType"),
        "name": raw_json.get("Name"),
        "description": raw_json.get("Description"),
        "cik": raw_json.get("CIK"),
        "exchange": raw_json.get("Exchange"),
        "currency": raw_json.get("Currency"),
        "country": raw_json.get("Country"),
        "sector": raw_json.get("Sector"),
        "industry": raw_json.get("Industry"),
        "address": raw_json.get("Address"),
        "official_site": raw_json.get("OfficialSite"),
        "fiscal_year_end": raw_json.get("FiscalYearEnd"),
        "latest_quarter": _safe_date(raw_json.get("LatestQuarter")),
        "market_capitalization": _safe_int(raw_json.get("MarketCapitalization")),
        "ebitda": _safe_int(raw_json.get("EBITDA")),
        "pe_ratio": _safe_float(raw_json.get("PERatio")),
        "peg_ratio": _safe_float(raw_json.get("PEGRatio")),
        "book_value": _safe_float(raw_json.get("BookValue")),
        "dividend_per_share": _safe_float(raw_json.get("DividendPerShare")),
        "dividend_yield": _safe_float(raw_json.get("DividendYield")),
        "eps": _safe_float(raw_json.get("EPS")),
        "revenue_per_share_ttm": _safe_float(raw_json.get("RevenuePerShareTTM")),
        "profit_margin": _safe_float(raw_json.get("ProfitMargin")),
        "operating_margin_ttm": _safe_float(raw_json.get("OperatingMarginTTM")),
        "return_on_assets_ttm": _safe_float(raw_json.get("ReturnOnAssetsTTM")),
        "return_on_equity_ttm": _safe_float(raw_json.get("ReturnOnEquityTTM")),
        "revenue_ttm": _safe_int(raw_json.get("RevenueTTM")),
        "gross_profit_ttm": _safe_int(raw_json.get("GrossProfitTTM")),
        "diluted_eps_ttm": _safe_float(raw_json.get("DilutedEPSTTM")),
        "quarterly_earnings_growth_yoy": _safe_float(raw_json.get("QuarterlyEarningsGrowthYOY")),
        "quarterly_revenue_growth_yoy": _safe_float(raw_json.get("QuarterlyRevenueGrowthYOY")),
        "analyst_target_price": _safe_float(raw_json.get("AnalystTargetPrice")),
        "analyst_rating_strong_buy": _safe_int(raw_json.get("AnalystRatingStrongBuy")),
        "analyst_rating_buy": _safe_int(raw_json.get("AnalystRatingBuy")),
        "analyst_rating_hold": _safe_int(raw_json.get("AnalystRatingHold")),
        "analyst_rating_sell": _safe_int(raw_json.get("AnalystRatingSell")),
        "analyst_rating_strong_sell": _safe_int(raw_json.get("AnalystRatingStrongSell")),
        "trailing_pe": _safe_float(raw_json.get("TrailingPE")),
        "forward_pe": _safe_float(raw_json.get("ForwardPE")),
        "price_to_sales_ratio_ttm": _safe_float(raw_json.get("PriceToSalesRatioTTM")),
        "price_to_book_ratio": _safe_float(raw_json.get("PriceToBookRatio")),
        "ev_to_revenue": _safe_float(raw_json.get("EVToRevenue")),
        "ev_to_ebitda": _safe_float(raw_json.get("EVToEBITDA")),
        "beta": _safe_float(raw_json.get("Beta")),
        "week_52_high": _safe_float(raw_json.get("52WeekHigh")),
        "week_52_low": _safe_float(raw_json.get("52WeekLow")),
        "day_50_moving_average": _safe_float(raw_json.get("50DayMovingAverage")),
        "day_200_moving_average": _safe_float(raw_json.get("200DayMovingAverage")),
        "shares_outstanding": _safe_int(raw_json.get("SharesOutstanding")),
        "shares_float": _safe_int(raw_json.get("SharesFloat")),
        "percent_insiders": _safe_float(raw_json.get("PercentInsiders")),
        "percent_institutions": _safe_float(raw_json.get("PercentInstitutions")),
        "dividend_date": _safe_date(raw_json.get("DividendDate")),
        "ex_dividend_date": _safe_date(raw_json.get("ExDividendDate"))
    }


def transform_yfinance_overview_to_db(raw_json: dict) -> dict:
    """
    把 yfinance (Yahoo) 的 camelCase 格式，转换为
    PostgreSQL 数据库需要的全小写下划线(snake_case)格式。
    注意：雅虎有些数据(如 CIK, 详细的分析师打分)没有提供，我们会安全地返回 None，数据库会自动存为 NULL。
    """
    if not raw_json or "symbol" not in raw_json:
        return {}
        
    return {
        "symbol": raw_json["symbol"].upper(),
        "asset_type": raw_json.get("quoteType"),
        "name": raw_json.get("shortName") or raw_json.get("longName"),
        "description": raw_json.get("longBusinessSummary"),
        "cik": None,  
        "exchange": raw_json.get("exchange"),
        "currency": raw_json.get("currency"),
        "country": raw_json.get("country"),
        "sector": raw_json.get("sector"),
        "industry": raw_json.get("industry"),
        "address": raw_json.get("address1"),
        "official_site": raw_json.get("website"),
        "fiscal_year_end": None,
        "latest_quarter": None, 
        
        # 核心财务指标映射
        "market_capitalization": _safe_int(raw_json.get("marketCap")),
        "ebitda": _safe_int(raw_json.get("ebitda")),
        "pe_ratio": _safe_float(raw_json.get("trailingPE")),
        "peg_ratio": _safe_float(raw_json.get("pegRatio")),
        "book_value": _safe_float(raw_json.get("bookValue")),
        "dividend_per_share": _safe_float(raw_json.get("dividendRate")),
        "dividend_yield": _safe_float(raw_json.get("dividendYield")),
        "eps": _safe_float(raw_json.get("trailingEps")),
        "revenue_per_share_ttm": _safe_float(raw_json.get("revenuePerShare")),
        "profit_margin": _safe_float(raw_json.get("profitMargins")),
        "operating_margin_ttm": _safe_float(raw_json.get("operatingMargins")),
        "return_on_assets_ttm": _safe_float(raw_json.get("returnOnAssets")),
        "return_on_equity_ttm": _safe_float(raw_json.get("returnOnEquity")),
        "revenue_ttm": _safe_int(raw_json.get("totalRevenue")),
        "gross_profit_ttm": _safe_int(raw_json.get("grossProfits")),
        "diluted_eps_ttm": _safe_float(raw_json.get("trailingEps")),
        
        # 增长与估值
        "quarterly_earnings_growth_yoy": _safe_float(raw_json.get("earningsQuarterlyGrowth")),
        "quarterly_revenue_growth_yoy": _safe_float(raw_json.get("revenueGrowth")),
        "analyst_target_price": _safe_float(raw_json.get("targetMeanPrice")),
        "analyst_rating_strong_buy": None,
        "analyst_rating_buy": None,
        "analyst_rating_hold": None,
        "analyst_rating_sell": None,
        "analyst_rating_strong_sell": None,
        "trailing_pe": _safe_float(raw_json.get("trailingPE")),
        "forward_pe": _safe_float(raw_json.get("forwardPE")),
        "price_to_sales_ratio_ttm": _safe_float(raw_json.get("priceToSalesTrailing12Months")),
        "price_to_book_ratio": _safe_float(raw_json.get("priceToBook")),
        "ev_to_revenue": _safe_float(raw_json.get("enterpriseToRevenue")),
        "ev_to_ebitda": _safe_float(raw_json.get("enterpriseToEbitda")),
        "beta": _safe_float(raw_json.get("beta")),
        
        # 交易数据与股本
        "week_52_high": _safe_float(raw_json.get("fiftyTwoWeekHigh")),
        "week_52_low": _safe_float(raw_json.get("fiftyTwoWeekLow")),
        "day_50_moving_average": _safe_float(raw_json.get("fiftyDayAverage")),
        "day_200_moving_average": _safe_float(raw_json.get("twoHundredDayAverage")),
        "shares_outstanding": _safe_int(raw_json.get("sharesOutstanding")),
        "shares_float": _safe_int(raw_json.get("floatShares")),
        "percent_insiders": _safe_float(raw_json.get("heldPercentInsiders")),
        "percent_institutions": _safe_float(raw_json.get("heldPercentInstitutions")),
        
        # 日期类数据雅虎返回的是 Unix 时间戳，直接存入比较麻烦，为了稳定性先置空
        "dividend_date": None,
        "ex_dividend_date": None
    }


# 历史股价清洗 (Daily Prices)
def transform_alpha_prices_to_db(symbol: str, raw_data: dict) -> list:
    """Alpha Vantage: 接收标准 dict，返回数据库需要的列表"""
    prices_list = []
    
    if not raw_data or "Time Series (Daily)" not in raw_data:
        return prices_list
        
    time_series = raw_data["Time Series (Daily)"]
    
    # 遍历字典 { "2023-10-01": {"1. open": 150, ...} }
    for date_str, daily_data in time_series.items():
        prices_list.append({
            "symbol": symbol.upper(),
            "trade_date": date_str,
            "open_price": _safe_float(daily_data.get("1. open")),
            "high_price": _safe_float(daily_data.get("2. high")),
            "low_price": _safe_float(daily_data.get("3. low")),
            "close_price": _safe_float(daily_data.get("4. close")),
            # 容错机制
            "adjusted_close": _safe_float(daily_data.get("5. adjusted close", daily_data.get("4. close"))),
            "volume": _safe_int(daily_data.get("6. volume"))
        })
        
    return prices_list


def transform_yfinance_prices_to_db(symbol: str, raw_data: dict) -> list:
    """Yahoo Finance: 接收标准 dict (由 Pandas .to_dict() 转换而来)，返回数据库需要的列表"""
    prices_list = []
    
    if not raw_data:
        return prices_list
        
    # 遍历字典 { Timestamp('2023-10-01'): {"Open": 150, ...} }
    for date_obj, row in raw_data.items():
        # 兼容处理：确保日期变成 YYYY-MM-DD 格式的字符串
        date_str = date_obj.strftime("%Y-%m-%d") if hasattr(date_obj, 'strftime') else str(date_obj)[:10]
        
        prices_list.append({
            "symbol": symbol.upper(),
            "trade_date": date_str,
            "open_price": _safe_float(row.get("Open")),
            "high_price": _safe_float(row.get("High")),
            "low_price": _safe_float(row.get("Low")),
            "close_price": _safe_float(row.get("Close")),
            # 如果没有 Adj Close (批量下载有时会丢)，用 Close 兜底
            "adjusted_close": _safe_float(row.get("Adj Close", row.get("Close"))),
            "volume": _safe_int(row.get("Volume"))
        })
        
    return prices_list


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