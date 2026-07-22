# main.py
import argparse
import os
import sys
import time
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import init_db_pool, close_db_pool
from db.context_builder import build_ai_context
from db.repositories import save_report_to_file, save_report_to_db
from core.llm_factory import ModelTier
from core.report_generation import generate_investment_analysis
from runtime_mode import assert_live_write_target

def generate_reports(tickers: list, tier: ModelTier = ModelTier.NORMAL) -> dict:
    """Generate and persist structured investment reports for the requested tickers."""
    assert_live_write_target("generate investment reports")
    print(f"Starting report generation for {len(tickers)} ticker(s).")
    init_db_pool(min_conn=1, max_conn=5)

    results = {}
    success_count = 0
    failed_tickers = []

    for index, ticker in enumerate(tickers):
        ticker = ticker.upper()
        print(f"\n" + "="*60)
        print(f"Progress [{index + 1}/{len(tickers)}]: analyzing {ticker}")
        print("="*60)
        
        analysis_as_of = datetime.now(timezone.utc)
        raw_data = build_ai_context(ticker, analysis_as_of=analysis_as_of)
        if not raw_data:
            print(f"No database context found for {ticker}; the report will disclose the missing data.")
            raw_data = {"status": "unlisted_or_missing", "note": f"No internal data for {ticker}."}

        try:
            raw_data.setdefault("snapshot_metadata", {})
            raw_data["snapshot_metadata"].setdefault(
                "look_ahead_protection", False
            )
            report = generate_investment_analysis(
                ticker,
                raw_data,
                analysis_as_of=analysis_as_of,
                generation_mode="live",
                tier=tier,
            )
        except Exception as e:
            print(f"AI inference or structured-output parsing failed for {ticker}: {e}")
            results[ticker] = {"error": "AI output parsing failed", "details": str(e)}
            failed_tickers.append(ticker)
            continue

        try:
            save_report_to_file(report)
            is_saved = save_report_to_db(report)
            
            if is_saved:
                print(f"Saved the {ticker} report to local storage and PostgreSQL.")
                success_count += 1
                results[ticker] = report
            else:
                failed_tickers.append(ticker)

        except Exception as e:
            print(f"Failed to persist the {ticker} report: {e}")
            failed_tickers.append(ticker)

        if index < len(tickers) - 1:
            print("Waiting 5 seconds before the next model request...")
            time.sleep(5)

    print("\n" + "#"*60)
    print(f"Report generation complete: {success_count} succeeded, {len(failed_tickers)} failed.")
    if failed_tickers:
        print(f"Failed tickers: {failed_tickers}")
    print("#"*60)
    close_db_pool()
    
    return results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate structured AI equity research reports")
    parser.add_argument("--tickers", nargs="+", required=True, metavar="TICKER",
                        help="Ticker symbols separated by spaces, for example: --tickers AAPL NVDA")
    parser.add_argument("--tier", choices=[t.value for t in ModelTier], default=ModelTier.NORMAL.value,
                        help="Model tier: smart=GPT-4o, normal=DeepSeek, local=Ollama (default: normal)")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    generate_reports(args.tickers, tier=ModelTier(args.tier))
