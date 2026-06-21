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


def transform_alpha_to_db(raw_json: dict) -> dict:
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
        "week_52_high": _safe_float(raw_json.get("52WeekHigh")), # 👈 顺便把数字开头的坑在 Python 层解决掉
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