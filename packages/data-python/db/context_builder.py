import psycopg2.extras
from datetime import datetime, timedelta, timezone

from db.connection import get_connection, release_connection
from core.previous_call import build_previous_call_review
from core.news_relevance import headline_matches_ticker
from tools.sec_financials import fact_provenance, latest_fact_value


def _iso(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _date_iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    return _iso(value)


def _number(value):
    return float(value) if value is not None else None


def _percent(value):
    return round(float(value) * 100, 2) if value is not None else None


def build_ai_context(ticker: str, analysis_as_of: datetime | None = None):
    """Build an LLM context from fundamentals, momentum, and 30 days of news."""
    analysis_as_of = analysis_as_of or datetime.now(timezone.utc)
    connection = None
    cursor = None
    is_from_pool = False
    try:
        connection, is_from_pool = get_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT * FROM company_overview WHERE symbol = %s", (ticker.upper(),))
        overview = cursor.fetchone()
        if not overview: return None

        cursor.execute("SELECT to_regclass('public.sec_financial_snapshots')")
        sec_table_exists = cursor.fetchone()[0] is not None
        sec_row = None
        if sec_table_exists:
            cursor.execute("""
                SELECT accession_number, form, filed_at, accepted_at, period_end,
                       primary_document, cik, entity_name, facts
                FROM sec_financial_snapshots
                WHERE symbol = %s AND filed_at <= %s::date
                ORDER BY filed_at DESC
                LIMIT 1
            """, (ticker.upper(), analysis_as_of))
            sec_row = cursor.fetchone()
        sec_snapshot = None
        if sec_row:
            sec_snapshot = {
                "cik": sec_row["cik"],
                "entity_name": sec_row["entity_name"],
                "filing": {
                    "accession": sec_row["accession_number"],
                    "form": sec_row["form"],
                    "filed_at": _date_iso(sec_row["filed_at"]),
                    "accepted_at": _iso(sec_row["accepted_at"]),
                    "period_end": _date_iso(sec_row["period_end"]),
                    "primary_document": sec_row["primary_document"],
                },
                "facts": sec_row["facts"],
            }
        sec_filing = (sec_snapshot or {}).get("filing") or {}
        sec_operating_cash_flow = latest_fact_value(sec_snapshot, "operating_cash_flow")
        sec_capex = latest_fact_value(sec_snapshot, "capital_expenditures")
        debt_parts = (
            latest_fact_value(sec_snapshot, "long_term_debt_current"),
            latest_fact_value(sec_snapshot, "long_term_debt_noncurrent"),
        )
        sec_long_term_debt = latest_fact_value(sec_snapshot, "long_term_debt_total")
        if sec_long_term_debt is None and any(value is not None for value in debt_parts):
            sec_long_term_debt = sum(value for value in debt_parts if value is not None)
        sec_total_assets = latest_fact_value(sec_snapshot, "total_assets")
        sec_equity = latest_fact_value(sec_snapshot, "stockholders_equity")
        sec_total_liabilities = latest_fact_value(sec_snapshot, "total_liabilities")
        if sec_total_liabilities is None and sec_total_assets is not None and sec_equity is not None:
            sec_total_liabilities = sec_total_assets - sec_equity

        cursor.execute("""
            SELECT trade_date, close_price FROM daily_prices 
            WHERE symbol = %s ORDER BY trade_date DESC LIMIT 15
        """, (ticker.upper(),))
        prices = cursor.fetchall()

        # Prefer the real-time quote, then fall back to the latest daily close.
        if overview['current_price']:
            current_price = float(overview['current_price'])
            price_trade_date = _date_iso(overview['price_as_of'])
        elif prices:
            current_price = float(prices[0]['close_price'])
            price_trade_date = _date_iso(prices[0]['trade_date'])
        else:
            current_price = 0
            price_trade_date = None
            print(f"⚠️ No current price is available for {ticker.upper()}")

        price_3_weeks_ago = float(prices[-1]['close_price']) if len(prices) == 15 else None

        recent_price_change_pct = None
        if price_3_weeks_ago and price_3_weeks_ago > 0:
            recent_price_change_pct = round(
                (current_price - price_3_weeks_ago) / price_3_weeks_ago * 100, 2
            )

        high_52 = _number(overview['week_52_high'])
        low_52 = _number(overview['week_52_low'])
        current_position_pct = None
        if high_52 is not None and low_52 is not None and high_52 > low_52 and current_price > 0:
            current_position_pct = round(
                (current_price - low_52) / (high_52 - low_52) * 100, 2
            )

        # Include recent headlines as potential catalysts in the report snapshot.
        cursor.execute("""
            SELECT finnhub_id, headline, source, trade_date FROM stock_news
            WHERE symbol = %s
              AND trade_date BETWEEN %s::date - INTERVAL '30 days' AND %s::date
            ORDER BY trade_date DESC, datetime DESC LIMIT 100
        """, (ticker.upper(), analysis_as_of, analysis_as_of))
        news_rows = [
            row for row in cursor.fetchall()
            if headline_matches_ticker(ticker.upper(), row['headline'])
        ][:8]
        recent_catalysts = [
            {
                "date": row['trade_date'].isoformat(),
                "source": row['source'],
                "headline": row['headline'],
                "finnhub_id": row['finnhub_id'],
                "evidence_ref": f"news:{ticker.upper()}:{row['finnhub_id']}"
            } for row in news_rows
        ]
        news_latest_date = max(
            (row['trade_date'] for row in news_rows),
            default=None,
        )
        news_stale_days = (
            (analysis_as_of.date() - news_latest_date).days
            if news_latest_date is not None else None
        )

        cursor.execute("""
            SELECT conclusion, conviction_level, target_price, reasoning,
                   COALESCE(analysis_as_of, generated_at) AS report_date,
                   raw_financial_data->'smart_money_consensus'->>'current_price' AS price_then
            FROM investment_reports
            WHERE ticker = %s
              AND COALESCE(analysis_as_of, generated_at) < %s
            ORDER BY COALESCE(analysis_as_of, generated_at) DESC
            LIMIT 1
        """, (ticker.upper(), analysis_as_of))
        previous = cursor.fetchone()
        previous_report = None
        if previous:
            previous_report_source = {
                "analysis_as_of": _iso(previous['report_date']),
                "conclusion": previous['conclusion'],
                "conviction_level": previous['conviction_level'],
                "target_price": float(previous['target_price'])
                if previous['target_price'] is not None else None,
                "price_then": float(previous['price_then'])
                if previous['price_then'] is not None else None,
                "reasoning": previous['reasoning'],
            }
            previous_report = build_previous_call_review(
                previous_report_source,
                evaluation_as_of=analysis_as_of.date(),
                evaluation_price=current_price,
            )

        return {
            "company_identity": {
                "symbol": overview['symbol'], "name": overview['name'], "sector": overview['sector'],
                "business_summary": overview['description'][:300] if overview['description'] else "N/A"
            },
            "profitability_and_scale": {
                "market_cap": _number(overview['market_capitalization']),
                "annual_revenue": _number(overview['revenue_ttm']),
                "gross_profit": _number(overview['gross_profit_ttm']),
                "operating_income": None,
                "net_income": None,
                "diluted_eps": _number(overview['diluted_eps_ttm']),
                "gross_margin_pct": None,
                "profit_margin_pct": _percent(overview['profit_margin']),
                "return_on_equity_pct": _percent(overview['return_on_equity_ttm']),
                "statement_metadata": {
                    "source": "Yahoo Finance",
                    "period_type": "ttm",
                    "period_end": _date_iso(overview['latest_quarter']),
                    "observed_at": _iso(overview['last_updated']),
                },
            },
            "balance_sheet_and_cash_flow": {
                "total_assets": sec_total_assets,
                "total_liabilities": sec_total_liabilities,
                "stockholders_equity": sec_equity,
                "cash_and_equivalents": latest_fact_value(sec_snapshot, "cash"),
                "long_term_debt": sec_long_term_debt,
                "operating_cash_flow": sec_operating_cash_flow,
                "capital_expenditures": sec_capex,
                "free_cash_flow": (
                    sec_operating_cash_flow - sec_capex
                    if sec_operating_cash_flow is not None and sec_capex is not None
                    else None
                ),
                "balance_sheet_metadata": fact_provenance(
                    sec_snapshot, "total_assets", "instant"
                ),
                "cash_flow_metadata": fact_provenance(
                    sec_snapshot,
                    "operating_cash_flow",
                    "annual" if sec_filing.get("form") == "10-K" else "year_to_date",
                ),
            },
            "valuation_and_growth": {
                "trailing_pe": _number(overview['trailing_pe']),
                "forward_pe": _number(overview['forward_pe']),
                "peg_ratio": _number(overview['peg_ratio']),
                "earnings_growth_yoy_pct": _percent(overview['quarterly_earnings_growth_yoy']),
                "revenue_growth_yoy_pct": _percent(overview['quarterly_revenue_growth_yoy']),
                "price_to_sales": _number(overview['price_to_sales_ratio_ttm']),
                "trailing_pe_basis": {
                    "method": "provider_ttm_metric",
                    "source": "Yahoo Finance",
                    "period_end": _date_iso(overview['latest_quarter']),
                },
            },
            "smart_money_consensus": {
                "percent_institutions": _percent(overview['percent_institutions']),
                "analyst_target_price": _number(overview['analyst_target_price']),
                "current_price": current_price,
                "price_trade_date": price_trade_date,
            },
            "technical_and_momentum": {
                "moving_averages": {
                    "day_50_ma": _number(overview['day_50_moving_average']),
                    "day_200_ma": _number(overview['day_200_moving_average']),
                },
                "week_52_range": {"high": high_52, "low": low_52, "current_position_pct": current_position_pct},
                "recent_3_weeks_action": {"price_change_pct": recent_price_change_pct}
            },
            "recent_catalysts": recent_catalysts,
            "recent_sec_filings": ([{
                "date": sec_filing.get("filed_at"),
                "source": "SEC",
                "form": sec_filing.get("form"),
                "accession": sec_filing.get("accession"),
                "primary_document": sec_filing.get("primary_document"),
                "evidence_ref": f"sec:{ticker.upper()}:{sec_filing.get('accession')}",
            }] if sec_snapshot else []),
            "previous_report": previous_report,
            "snapshot_metadata": {
                "schema_version": 2,
                "dataset_version": None,
                "price_as_of": price_trade_date,
                "fundamentals_period_end": sec_filing.get("period_end") or _iso(overview['latest_quarter']),
                "fundamentals_filed_at": sec_filing.get("filed_at"),
                "fundamentals_form": sec_filing.get("form"),
                "sec_accession": sec_filing.get("accession"),
                "news_window_start": (
                    analysis_as_of.date() - timedelta(days=30)
                ).isoformat(),
                "news_as_of": _date_iso(news_latest_date),
                "news_stale_days": news_stale_days,
                "look_ahead_protection": False,
            },
        }
    except Exception as e:
        print(f"❌ Failed to build the AI context: {e}")
        return None
    finally:
        if cursor: cursor.close()
        release_connection(connection, is_from_pool)
