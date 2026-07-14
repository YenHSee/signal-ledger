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


def transform_yfinance_overview_to_db(raw_json: dict) -> dict:
    """
    把 yfinance (Yahoo) 的 camelCase 格式，转换为
    PostgreSQL 数据库需要的全小写下划线(snake_case)格式。
    注意：雅虎有些数据(如 CIK, 详细的分析师打分)没有提供，我们会安全地返回 None，数据库会自动存为 NULL。
    """
    if not raw_json or "symbol" not in raw_json:
        return {}

    from datetime import datetime, timezone

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
        "ex_dividend_date": None,

        # 实时报价：currentPrice -> regularMarketPrice -> previousClose 三级 fallback
        "current_price": _safe_float(
            raw_json.get("currentPrice")
            or raw_json.get("regularMarketPrice")
            or raw_json.get("previousClose")
        ),
        "price_as_of": datetime.now(timezone.utc)
    }


# 历史股价清洗 (Daily Prices)
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


# 公司新闻清洗 (Stock News)
def transform_finnhub_news_to_db(symbol: str, raw_news_list: list) -> list:
    """
    把 Finnhub company-news 返回的原始列表，转换为 stock_news 表需要的 dict 列表。
    datetime (unix 秒) 会额外转出 trade_date (YYYY-MM-DD)，方便按日对齐 chart。
    """
    from datetime import datetime, timezone

    news_rows = []
    if not raw_news_list:
        return news_rows

    for item in raw_news_list:
        finnhub_id = item.get("id")
        unix_ts = item.get("datetime")
        headline = item.get("headline")
        # 缺关键字段的脏数据直接丢弃
        if not finnhub_id or not unix_ts or not headline:
            continue

        trade_date = datetime.fromtimestamp(int(unix_ts), tz=timezone.utc).strftime("%Y-%m-%d")

        news_rows.append({
            "finnhub_id": int(finnhub_id),
            "symbol": symbol.upper(),
            "trade_date": trade_date,
            "datetime": int(unix_ts),
            "headline": headline,
            "summary": item.get("summary") or "",
            "source": item.get("source") or "",
            "url": item.get("url") or ""
        })

    return news_rows