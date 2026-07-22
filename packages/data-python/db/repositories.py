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


def upsert_sec_financial_snapshots(symbol: str, snapshots: list[dict]) -> int:
    """Persist immutable SEC 10-K/10-Q snapshots for later point-in-time reads."""
    assert_live_write_target("insert SEC financial snapshots")
    if not snapshots:
        return 0
    connection = None
    cursor = None
    is_from_pool = False
    try:
        connection, is_from_pool = get_connection()
        cursor = connection.cursor()
        rows = []
        for snapshot in snapshots:
            filing = snapshot["filing"]
            rows.append(
                (
                    symbol.upper(),
                    filing["accession"],
                    filing["form"],
                    filing["filed_at"],
                    filing.get("accepted_at"),
                    filing.get("period_end"),
                    filing.get("primary_document"),
                    snapshot.get("cik"),
                    snapshot.get("entity_name"),
                    json.dumps(snapshot.get("facts") or {}),
                )
            )
        execute_values(
            cursor,
            """
            INSERT INTO sec_financial_snapshots (
                symbol, accession_number, form, filed_at, accepted_at, period_end,
                primary_document, cik, entity_name, facts
            ) VALUES %s
            ON CONFLICT (symbol, accession_number) DO UPDATE SET
                form = EXCLUDED.form,
                filed_at = EXCLUDED.filed_at,
                accepted_at = EXCLUDED.accepted_at,
                period_end = EXCLUDED.period_end,
                primary_document = EXCLUDED.primary_document,
                cik = EXCLUDED.cik,
                entity_name = EXCLUDED.entity_name,
                facts = EXCLUDED.facts,
                fetched_at = CURRENT_TIMESTAMP
            """,
            rows,
        )
        connection.commit()
        return len(rows)
    except Exception as error:
        print(f"❌ Failed to write SEC financial snapshots for {symbol}: {error}")
        if connection:
            connection.rollback()
        return 0
    finally:
        if cursor:
            cursor.close()
        release_connection(connection, is_from_pool)


def save_report_to_db(report: dict) -> bool:
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
            report_schema_version, ticker, analysis_as_of, generation_mode,
            model_tier, model_provider, model_name, prompt_version,
            conclusion, conviction_level, target_price,
            upside_downside_pct, risk_level, reasoning, full_report, 
            raw_financial_data, agent_outputs, generation_metadata, generated_at
        ) VALUES (
            %(report_schema_version)s, %(ticker)s, %(analysis_as_of)s, %(generation_mode)s,
            %(model_tier)s, %(model_provider)s, %(model_name)s, %(prompt_version)s,
            %(conclusion)s, %(conviction_level)s, %(target_price)s,
            %(upside_downside_pct)s, %(risk_level)s, %(reasoning)s, %(full_report)s,
            %(raw_financial_data)s, %(agent_outputs)s, %(generation_metadata)s, %(generated_at)s
        )
        """

        data_params = {
            "report_schema_version": report["report_schema_version"],
            "ticker": report["ticker"].upper(),
            "analysis_as_of": report["analysis_as_of"],
            "generation_mode": report["generation_mode"],
            "model_tier": report["model_tier"],
            "model_provider": report["model_provider"],
            "model_name": report["model_name"],
            "prompt_version": report["prompt_version"],
            "conclusion": report.get("conclusion", "N/A"),
            "conviction_level": report.get("conviction_level", "N/A"),
            "target_price": report["target_price"],
            "upside_downside_pct": report.get("upside_downside_pct", "N/A"),
            "risk_level": report.get("risk_level", "N/A"),
            "reasoning": report.get("reasoning", "N/A"),
            "full_report": report.get("full_report", "N/A"),
            "raw_financial_data": psycopg2.extras.Json(report["raw_financial_data"]),
            "agent_outputs": psycopg2.extras.Json(report["agent_outputs"]),
            "generation_metadata": psycopg2.extras.Json(report["generation_metadata"]),
            "generated_at": report["generated_at"],
        }

        cursor.execute(insert_sql, data_params)
        connection.commit()
        return True
    except Exception as error:
        print(f"❌ Failed to save the {report.get('ticker', 'unknown')} report: {error}")
        if connection: connection.rollback()
        return False
    finally:
        if cursor: cursor.close()
        release_connection(connection, is_from_pool)


def save_report_to_file(report: dict) -> None:
    """Save a report and its source snapshot as a dated local JSON file."""
    generated_at = datetime.fromisoformat(report["generated_at"].replace("Z", "+00:00"))
    timestamp = generated_at.strftime("%Y-%m-%dT%H%M%SZ")
    ticker = report["ticker"].upper()
    model_letter = report["model_tier"]
    output_dir = "reports"
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    file_name = f"{timestamp}_{ticker}_{model_letter}_report.json"
    file_path = os.path.join(output_dir, file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
    print(f"✅ Report saved with history preserved: {file_path}")
