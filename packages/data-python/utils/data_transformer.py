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
    Convert yfinance camelCase fields to the snake_case database schema.
    Fields unavailable from Yahoo Finance are returned as None and stored as NULL.
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
        
        # Core financial metrics
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
        
        # Growth and valuation
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
        
        # Trading data and share ownership
        "week_52_high": _safe_float(raw_json.get("fiftyTwoWeekHigh")),
        "week_52_low": _safe_float(raw_json.get("fiftyTwoWeekLow")),
        "day_50_moving_average": _safe_float(raw_json.get("fiftyDayAverage")),
        "day_200_moving_average": _safe_float(raw_json.get("twoHundredDayAverage")),
        "shares_outstanding": _safe_int(raw_json.get("sharesOutstanding")),
        "shares_float": _safe_int(raw_json.get("floatShares")),
        "percent_insiders": _safe_float(raw_json.get("heldPercentInsiders")),
        "percent_institutions": _safe_float(raw_json.get("heldPercentInstitutions")),
        
        # Date fields are left empty until timestamp normalization is implemented.
        "dividend_date": None,
        "ex_dividend_date": None,

        # Quote fallback: currentPrice -> regularMarketPrice -> previousClose.
        "current_price": _safe_float(
            raw_json.get("currentPrice")
            or raw_json.get("regularMarketPrice")
            or raw_json.get("previousClose")
        ),
        "price_as_of": datetime.now(timezone.utc)
    }


# Daily price normalization
def transform_yfinance_prices_to_db(symbol: str, raw_data: dict) -> list:
    """Convert a pandas-derived Yahoo Finance dictionary into database rows."""
    prices_list = []
    
    if not raw_data:
        return prices_list
        
    # Iterate over {Timestamp('2023-10-01'): {"Open": 150, ...}}.
    for date_obj, row in raw_data.items():
        # Normalize every date to YYYY-MM-DD.
        date_str = date_obj.strftime("%Y-%m-%d") if hasattr(date_obj, 'strftime') else str(date_obj)[:10]
        
        prices_list.append({
            "symbol": symbol.upper(),
            "trade_date": date_str,
            "open_price": _safe_float(row.get("Open")),
            "high_price": _safe_float(row.get("High")),
            "low_price": _safe_float(row.get("Low")),
            "close_price": _safe_float(row.get("Close")),
            # Batch downloads may omit Adj Close; use Close as a fallback.
            "adjusted_close": _safe_float(row.get("Adj Close", row.get("Close"))),
            "volume": _safe_int(row.get("Volume"))
        })
        
    return prices_list


# Company news normalization
def transform_finnhub_news_to_db(symbol: str, raw_news_list: list) -> list:
    """
    Convert Finnhub company-news items into stock_news rows.
    Derive trade_date from each Unix timestamp for daily chart alignment.
    """
    from datetime import datetime, timezone

    news_rows = []
    if not raw_news_list:
        return news_rows

    for item in raw_news_list:
        finnhub_id = item.get("id")
        unix_ts = item.get("datetime")
        headline = item.get("headline")
        # Drop incomplete upstream records.
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
