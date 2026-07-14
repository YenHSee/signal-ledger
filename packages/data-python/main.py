# main.py
import argparse
import os
import sys
import time
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.market_analyst import create_analyst_agent
from db.connection import init_db_pool, close_db_pool
from db.context_builder import build_ai_context
from db.repositories import save_report_to_file, save_report_to_db
from core.llm_factory import ModelTier

TIER_LETTER_MAP = {
    ModelTier.SMART: "S",
    ModelTier.NORMAL: "N",
    ModelTier.LOCAL: "L"
}


def generate_reports(tickers: list, tier: ModelTier = ModelTier.NORMAL) -> dict:
    """Generate and persist structured investment reports for the requested tickers."""
    model_letter = TIER_LETTER_MAP.get(tier, "U")

    print("Initializing the AI equity analyst...")
    try:
        executor, parser = create_analyst_agent(tier=tier)
        print("AI equity analyst initialized.\n")
    except Exception as e:
        print(f"Unable to initialize the AI analyst: {e}")
        sys.exit(1)

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
        
        raw_data = build_ai_context(ticker) 
        if not raw_data:
            print(f"No database context found for {ticker}; the report will disclose the missing data.")
            raw_data = {"status": "unlisted_or_missing", "note": f"No internal data for {ticker}."}

        try:
            ai_prompt = f"""
            Prepare an equity research report for {ticker}.
            The following point-in-time snapshot contains the available financial,
            valuation, technical, and catalyst data:
            {json.dumps(raw_data, indent=2, ensure_ascii=False)}

            Analyze only this supplied snapshot and clearly disclose missing evidence.
            """
            
            result = executor.invoke({"messages": [("user", ai_prompt)]})
            
            ai_output_text = result["messages"][-1].content
            
            final_parsed_obj = parser.parse(ai_output_text)
            if hasattr(final_parsed_obj, 'model_dump'):
                final_json_dict = final_parsed_obj.model_dump()
            else:
                final_json_dict = final_parsed_obj.dict()
                
        except Exception as e:
            print(f"AI inference or structured-output parsing failed for {ticker}: {e}")
            results[ticker] = {"error": "AI output parsing failed", "details": str(e)}
            failed_tickers.append(ticker)
            continue

        try:
            save_report_to_file(ticker, final_json_dict, raw_data, model_letter)
            is_saved = save_report_to_db(ticker, final_json_dict, raw_data, model_letter)
            
            if is_saved:
                print(f"Saved the {ticker} report to local storage and PostgreSQL.")
                success_count += 1
                results[ticker] = final_json_dict
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
