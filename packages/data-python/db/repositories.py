import json
import os
from datetime import datetime

import psycopg2.extras
from psycopg2.extras import execute_values

from runtime_mode import assert_live_write_target

from db.connection import get_connection, release_connection


def insert_company_overview(clean_data: dict) -> bool:
    """Upsert normalized company fundamentals into company_overview."""
    assert_live_write_target("insert company overview")
    if not clean_data or "symbol" not in clean_data:
        return False

    symbol = clean_data["symbol"]
    connection = None
    cursor = None
    is_from_pool = False
    try:
        connection, is_from_pool = get_connection()
        cursor = connection.cursor()

        upsert_sql = """
        INSERT INTO company_overview (
            symbol, asset_type, name, description, cik, exchange, currency, country, 
            sector, industry, address, official_site, fiscal_year_end, latest_quarter, 
            market_capitalization, ebitda, pe_ratio, peg_ratio, book_value, 
            dividend_per_share, dividend_yield, eps, revenue_per_share_ttm, 
            profit_margin, operating_margin_ttm, return_on_assets_ttm, return_on_equity_ttm, 
            revenue_ttm, gross_profit_ttm, diluted_eps_ttm, quarterly_earnings_growth_yoy, 
            quarterly_revenue_growth_yoy, analyst_target_price, analyst_rating_strong_buy, 
            analyst_rating_buy, analyst_rating_hold, analyst_rating_sell, analyst_rating_strong_sell, 
            trailing_pe, forward_pe, price_to_sales_ratio_ttm, price_to_book_ratio, 
            ev_to_revenue, ev_to_ebitda, beta, week_52_high, week_52_low, 
            day_50_moving_average, day_200_moving_average, shares_outstanding, shares_float, 
            percent_insiders, percent_institutions, dividend_date, ex_dividend_date, 
            is_sp500, last_updated, current_price, price_as_of
        ) VALUES (
            %(symbol)s, %(asset_type)s, %(name)s, %(description)s, %(cik)s, %(exchange)s, %(currency)s, %(country)s, 
            %(sector)s, %(industry)s, %(address)s, %(official_site)s, %(fiscal_year_end)s, %(latest_quarter)s, 
            %(market_capitalization)s, %(ebitda)s, %(pe_ratio)s, %(peg_ratio)s, %(book_value)s, 
            %(dividend_per_share)s, %(dividend_yield)s, %(eps)s, %(revenue_per_share_ttm)s, 
            %(profit_margin)s, %(operating_margin_ttm)s, %(return_on_assets_ttm)s, %(return_on_equity_ttm)s, 
            %(revenue_ttm)s, %(gross_profit_ttm)s, %(diluted_eps_ttm)s, %(quarterly_earnings_growth_yoy)s, 
            %(quarterly_revenue_growth_yoy)s, %(analyst_target_price)s, %(analyst_rating_strong_buy)s, 
            %(analyst_rating_buy)s, %(analyst_rating_hold)s, %(analyst_rating_sell)s, %(analyst_rating_strong_sell)s, 
            %(trailing_pe)s, %(forward_pe)s, %(price_to_sales_ratio_ttm)s, %(price_to_book_ratio)s, 
            %(ev_to_revenue)s, %(ev_to_ebitda)s, %(beta)s, %(week_52_high)s, %(week_52_low)s, 
            %(day_50_moving_average)s, %(day_200_moving_average)s, %(shares_outstanding)s, %(shares_float)s, 
            %(percent_insiders)s, %(percent_institutions)s, %(dividend_date)s, %(ex_dividend_date)s, 
            %(is_sp500)s, CURRENT_TIMESTAMP, %(current_price)s, %(price_as_of)s
        )
        ON CONFLICT (symbol) 
        DO UPDATE SET 
            asset_type = EXCLUDED.asset_type, name = EXCLUDED.name, description = EXCLUDED.description,
            exchange = EXCLUDED.exchange, sector = EXCLUDED.sector, industry = EXCLUDED.industry,
            latest_quarter = EXCLUDED.latest_quarter, market_capitalization = EXCLUDED.market_capitalization,
            ebitda = EXCLUDED.ebitda, pe_ratio = EXCLUDED.pe_ratio, peg_ratio = EXCLUDED.peg_ratio,
            eps = EXCLUDED.eps, profit_margin = EXCLUDED.profit_margin, revenue_ttm = EXCLUDED.revenue_ttm,
            return_on_equity_ttm = EXCLUDED.return_on_equity_ttm, quarterly_earnings_growth_yoy = EXCLUDED.quarterly_earnings_growth_yoy,
            analyst_target_price = EXCLUDED.analyst_target_price, trailing_pe = EXCLUDED.trailing_pe,
            forward_pe = EXCLUDED.forward_pe, week_52_high = EXCLUDED.week_52_high, week_52_low = EXCLUDED.week_52_low,
            day_50_moving_average = EXCLUDED.day_50_moving_average, day_200_moving_average = EXCLUDED.day_200_moving_average,
            percent_institutions = EXCLUDED.percent_institutions, is_sp500 = EXCLUDED.is_sp500, last_updated = CURRENT_TIMESTAMP,
            current_price = EXCLUDED.current_price, price_as_of = EXCLUDED.price_as_of;
        """
        cursor.execute(upsert_sql, clean_data)
        connection.commit()
        return True
    except Exception as error:
        print(f"❌ Failed to synchronize fundamentals for {symbol}: {error}")
        if connection: connection.rollback()
        return False
    finally:
        if cursor: cursor.close()
        release_connection(connection, is_from_pool)


def insert_daily_prices(prices_list: list) -> bool:
    """Bulk upsert daily prices for one symbol."""
    assert_live_write_target("insert daily prices")
    if not prices_list:
        return False

    symbol = prices_list[0].get("symbol")
    data_tuples = [
        (
            p.get("symbol"), p.get("trade_date"), p.get("open_price"), p.get("high_price"),
            p.get("low_price"), p.get("close_price"), p.get("adjusted_close"), p.get("volume")
        ) for p in prices_list
    ]

    upsert_sql = """
    INSERT INTO daily_prices (
        symbol, trade_date, open_price, high_price, low_price, close_price, adjusted_close, volume
    ) VALUES %s
    ON CONFLICT (symbol, trade_date) 
    DO UPDATE SET 
        open_price = EXCLUDED.open_price, high_price = EXCLUDED.high_price, low_price = EXCLUDED.low_price,
        close_price = EXCLUDED.close_price, adjusted_close = EXCLUDED.adjusted_close, volume = EXCLUDED.volume;
    """

    connection = None
    cursor = None
    is_from_pool = False
    try:
        connection, is_from_pool = get_connection()
        cursor = connection.cursor()
        execute_values(cursor, upsert_sql, data_tuples)
        connection.commit()
        return True
    except Exception as error:
        print(f"❌ Failed to write daily prices for {symbol}: {error}")
        if connection: connection.rollback()
        return False
    finally:
        if cursor: cursor.close()
        release_connection(connection, is_from_pool)


def insert_stock_news(rows: list) -> int:
    """
    Insert news in bulk, skipping duplicate Finnhub IDs.
    Returns the number of newly inserted rows.
    """
    assert_live_write_target("insert stock news")
    if not rows:
        return 0

    connection = None
    cursor = None
    is_from_pool = False
    try:
        connection, is_from_pool = get_connection()
        cursor = connection.cursor()

        data_tuples = [
            (
                r.get("finnhub_id"), r.get("symbol"), r.get("trade_date"), r.get("datetime"),
                r.get("headline"), r.get("summary"), r.get("source"), r.get("url")
            ) for r in rows
        ]

        upsert_sql = """
        INSERT INTO stock_news (
            finnhub_id, symbol, trade_date, datetime, headline, summary, source, url
        ) VALUES %s
        ON CONFLICT (finnhub_id) DO NOTHING;
        """
        execute_values(cursor, upsert_sql, data_tuples)
        inserted = cursor.rowcount
        connection.commit()
        return inserted
    except Exception as error:
        print(f"❌ Failed to write news records: {error}")
        if connection: connection.rollback()
        return 0
    finally:
        if cursor: cursor.close()
        release_connection(connection, is_from_pool)


def count_stock_news() -> int:
    """Return the stock_news row count, or zero when the query fails."""
    connection = None
    cursor = None
    is_from_pool = False
    try:
        connection, is_from_pool = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM stock_news;")
        return cursor.fetchone()[0]
    except Exception as error:
        print(f"⚠️ Failed to count stock_news rows: {error}")
        if connection: connection.rollback()
        return 0
    finally:
        if cursor: cursor.close()
        release_connection(connection, is_from_pool)


def save_report_to_db(ticker: str, ai_analysis: dict, raw_data: dict, model_tier: str) -> bool:
    """Persist an AI report together with its source-data snapshot."""
    assert_live_write_target("save investment report")
    connection = None
    cursor = None
    is_from_pool = False
    try:
        connection, is_from_pool = get_connection()
        cursor = connection.cursor()

        insert_sql = """
        INSERT INTO investment_reports (
            ticker, model_tier, conclusion, conviction_level, target_price, 
            upside_downside_pct, risk_level, reasoning, full_report, 
            raw_financial_data, generated_at
        ) VALUES (
            %(ticker)s, %(model_tier)s, %(conclusion)s, %(conviction_level)s, %(target_price)s,
            %(upside_downside_pct)s, %(risk_level)s, %(reasoning)s, %(full_report)s,
            %(raw_financial_data)s, %(generated_at)s
        )
        """

        # Normalize target prices that may contain currency symbols or separators.
        target_price_raw = ai_analysis.get("target_price", 0)
        try:
            target_price_float = float(str(target_price_raw).replace('$', '').replace(',', ''))
        except ValueError:
            target_price_float = 0

        data_params = {
            "ticker": ticker.upper(),
            "model_tier": model_tier,
            "conclusion": ai_analysis.get("conclusion", "N/A"),
            "conviction_level": ai_analysis.get("conviction_level", "N/A"),
            "target_price": target_price_float,
            "upside_downside_pct": ai_analysis.get("upside_downside_pct", "N/A"),
            "risk_level": ai_analysis.get("risk_level", "N/A"),
            "reasoning": ai_analysis.get("reasoning", "N/A"),
            "full_report": ai_analysis.get("full_report", "N/A"),
            "raw_financial_data": psycopg2.extras.Json(raw_data),
            "generated_at": datetime.now()
        }

        cursor.execute(insert_sql, data_params)
        connection.commit()
        return True
    except Exception as error:
        print(f"❌ Failed to save the {ticker} report: {error}")
        if connection: connection.rollback()
        return False
    finally:
        if cursor: cursor.close()
        release_connection(connection, is_from_pool)


def save_report_to_file(ticker: str, analysis_output: dict, raw_data: dict, model_letter: str = "L") -> None:
    """Save a report and its source snapshot as a dated local JSON file."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    exact_time = datetime.now().isoformat()
    report = {
        "ticker": ticker.upper(), "timestamp": exact_time, "model_tier": model_letter,
        "ai_analysis": analysis_output, "raw_financial_data": raw_data
    }
    output_dir = "reports"
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    file_name = f"{date_str}_{ticker.upper()}_{model_letter}_report.json"
    file_path = os.path.join(output_dir, file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
    print(f"✅ Report saved with history preserved: {file_path}")
