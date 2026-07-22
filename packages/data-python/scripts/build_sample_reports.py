"""Generate frozen historical sample reports from the versioned fixture only."""

import argparse
import json
import math
import os
import sys
import tempfile
import time
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))
load_dotenv(PACKAGE_ROOT / ".env")

from agents.market_analyst import create_analyst_agent
from core.llm_factory import ModelTier, get_model_spec, preflight_model
from core.news_relevance import headline_matches_ticker
from core.report_generation import PROMPT_VERSION, generate_investment_analysis
from core.previous_call import build_previous_call_review
from runtime_mode import assert_live_read_source
from scripts.seed_sample_data import _validate_investment_reports, load_fixture
from tools.sec_financials import fact_provenance, select_sec_snapshot


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_DIR = REPO_ROOT / "sample-data" / "v1"
DEFAULT_REPORT_OUTPUT_DIR = PACKAGE_ROOT / "reports"
ACTIVE_REPORT_DATES = (
    date(2026, 1, 9),
    date(2026, 2, 20),
    date(2026, 3, 31),
    date(2026, 5, 15),
    date(2026, 7, 17),
)
DEFAULT_SINGLE_REPORT_DATE = date(2026, 7, 17)
ACTIVE_TICKERS = {
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "AMD",
    "JPM",
    "WMT",
}
LEVELS = {"high": "High", "medium": "Medium", "low": "Low"}


class SampleReportBuildError(RuntimeError):
    """Raised when frozen historical reports cannot be built safely."""


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def historical_report_output_path(report: dict, output_dir: Path) -> Path:
    analysis_date = report["analysis_as_of"][:10]
    return output_dir.resolve() / (
        f"{analysis_date}_{report['ticker']}_{report['model_tier']}_report.json"
    )


def _write_historical_report_archive(report: dict, output_dir: Path) -> Path:
    output_path = historical_report_output_path(report, output_dir)
    _write_json_atomic(output_path, report)
    return output_path


def _average(values: list[float], minimum: int) -> float | None:
    if len(values) < minimum:
        return None
    return round(sum(values[-minimum:]) / minimum, 4)


def _latest_fact(sec_snapshot: dict | None, key: str) -> float | None:
    fact = (sec_snapshot or {}).get("facts", {}).get(key)
    history = fact.get("history") if isinstance(fact, dict) else None
    if not history:
        return None
    value = history[-1].get("value")
    return float(value) if value is not None else None


def _previous_fact(sec_snapshot: dict | None, key: str) -> float | None:
    fact = (sec_snapshot or {}).get("facts", {}).get(key)
    history = fact.get("history") if isinstance(fact, dict) else None
    if not history or len(history) < 2:
        return None
    latest_end = history[-1].get("period_end")
    for row in reversed(history[:-1]):
        if row.get("period_end") != latest_end and row.get("value") is not None:
            return float(row["value"])
    return None


def _growth_pct(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return round((current / previous - 1) * 100, 2)


def build_fixture_context(
    ticker: str,
    as_of: date,
    overview_rows: list[dict],
    price_rows: list[dict],
    news_rows: list[dict],
    report_input: dict | None = None,
    dataset_version: str = "v1-draft.5",
    previous_report: dict | None = None,
) -> dict:
    """Build a point-in-time context without reading the live or sample database."""
    ticker = ticker.upper()
    overview = next((row for row in overview_rows if row["symbol"] == ticker), None)
    if not overview:
        raise SampleReportBuildError(f"Missing company overview for {ticker}.")

    historical_price_rows = [
        {**row, "symbol": ticker} for row in (report_input or {}).get("prices", [])
    ]
    prices_by_date = {
        row["trade_date"]: row
        for row in [*historical_price_rows, *price_rows]
        if row.get("symbol") == ticker
        and date.fromisoformat(row["trade_date"]) <= as_of
    }
    prices = sorted(
        (
            row for row in prices_by_date.values()
        ),
        key=lambda row: row["trade_date"],
    )
    if not prices:
        raise SampleReportBuildError(f"No frozen price exists for {ticker} on or before {as_of}.")
    current_row = prices[-1]
    closes = [float(row["close_price"]) for row in prices if row.get("close_price")]
    current_price = float(current_row["close_price"])
    prior_15 = closes[-15:]
    change_3_weeks = None
    if len(prior_15) == 15 and prior_15[0] > 0:
        change_3_weeks = round((current_price / prior_15[0] - 1) * 100, 2)
    trailing_year = closes[-252:]
    low = min(trailing_year)
    high = max(trailing_year)
    range_position = round((current_price - low) / (high - low) * 100, 2) if high > low else None

    news_start = as_of - timedelta(days=30)
    catalysts = sorted(
        (
            {
                "date": row["trade_date"],
                "source": row.get("source") or "Unknown",
                "headline": row["headline"],
                "finnhub_id": row.get("finnhub_id"),
                "evidence_ref": f"news:{ticker}:{row['finnhub_id']}",
            }
            for row in news_rows
            if row["symbol"] == ticker
            and news_start <= date.fromisoformat(row["trade_date"]) <= as_of
            and headline_matches_ticker(ticker, row["headline"])
        ),
        key=lambda row: (row["date"], row["headline"]),
        reverse=True,
    )

    sec_snapshot = select_sec_snapshot(report_input, as_of)
    annual_sec_snapshot = select_sec_snapshot(report_input, as_of, {"10-K"})
    filing = sec_snapshot.get("filing") or {}
    revenue = _latest_fact(annual_sec_snapshot, "revenue")
    gross_profit = _latest_fact(annual_sec_snapshot, "gross_profit")
    operating_income = _latest_fact(annual_sec_snapshot, "operating_income")
    net_income = _latest_fact(annual_sec_snapshot, "net_income")
    diluted_eps = _latest_fact(annual_sec_snapshot, "diluted_eps")
    equity = _latest_fact(sec_snapshot, "stockholders_equity")
    shares = _latest_fact(sec_snapshot, "shares_outstanding")
    operating_cash_flow = _latest_fact(sec_snapshot, "operating_cash_flow")
    capex = _latest_fact(sec_snapshot, "capital_expenditures")
    debt_parts = [
        _latest_fact(sec_snapshot, "long_term_debt_current"),
        _latest_fact(sec_snapshot, "long_term_debt_noncurrent"),
    ]
    total_debt = _latest_fact(sec_snapshot, "long_term_debt_total")
    if total_debt is None and any(value is not None for value in debt_parts):
        total_debt = sum(value for value in debt_parts if value is not None)
    total_assets = _latest_fact(sec_snapshot, "total_assets")
    total_liabilities = _latest_fact(sec_snapshot, "total_liabilities")
    if total_liabilities is None and total_assets is not None and equity is not None:
        total_liabilities = total_assets - equity
    sec_events = []
    if filing.get("filed_at"):
        filing_age = (as_of - date.fromisoformat(filing["filed_at"])).days
        if 0 <= filing_age <= 90:
            sec_events.append({
                "date": filing["filed_at"],
                "source": "SEC",
                "form": filing.get("form"),
                "accession": filing.get("accession"),
                "primary_document": filing.get("primary_document"),
                "evidence_ref": f"sec:{ticker}:{filing.get('accession')}",
            })
    for event in (report_input or {}).get(
        "recent_8k_events", sec_snapshot.get("recent_8k_events", [])
    ):
        filed_at = event.get("filingDate")
        if not filed_at:
            continue
        age_days = (as_of - date.fromisoformat(filed_at)).days
        if age_days < 0 or age_days > 90:
            continue
        accession = event.get("accessionNumber")
        sec_events.append({
            "date": filed_at,
            "source": "SEC",
            "form": "8-K",
            "accession": accession,
            "primary_document": event.get("primaryDocument"),
            "evidence_ref": f"sec:{ticker}:{accession}",
        })
    sec_events = sorted(
        {event["accession"]: event for event in sec_events}.values(),
        key=lambda event: (event["date"], event.get("accession") or ""),
        reverse=True,
    )

    news_latest_date = max(
        (date.fromisoformat(item["date"]) for item in catalysts),
        default=None,
    )

    return {
        "company_identity": {
            "symbol": ticker,
            "name": overview.get("name"),
            "sector": overview.get("sector"),
            "industry": overview.get("industry"),
            "business_summary": (overview.get("description") or "")[:500],
        },
        "profitability_and_scale": {
            "market_cap": round(current_price * shares, 2) if shares else None,
            "annual_revenue": revenue,
            "gross_profit": gross_profit,
            "operating_income": operating_income,
            "net_income": net_income,
            "diluted_eps": diluted_eps,
            "gross_margin_pct": round(gross_profit / revenue * 100, 2)
            if gross_profit and revenue else None,
            "profit_margin_pct": round(net_income / revenue * 100, 2)
            if net_income and revenue else None,
            "return_on_equity_pct": round(net_income / equity * 100, 2)
            if net_income and equity else None,
            "statement_metadata": fact_provenance(
                annual_sec_snapshot, "revenue", "annual"
            ),
        },
        "balance_sheet_and_cash_flow": {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "stockholders_equity": equity,
            "cash_and_equivalents": _latest_fact(sec_snapshot, "cash"),
            "long_term_debt": total_debt,
            "operating_cash_flow": operating_cash_flow,
            "capital_expenditures": capex,
            "free_cash_flow": operating_cash_flow - capex
            if operating_cash_flow is not None and capex is not None else None,
            "balance_sheet_metadata": fact_provenance(
                sec_snapshot, "total_assets", "instant"
            ),
            "cash_flow_metadata": fact_provenance(
                sec_snapshot,
                "operating_cash_flow",
                "annual" if filing.get("form") == "10-K" else "year_to_date",
            ),
        },
        "valuation_and_growth": {
            "trailing_pe": round(current_price / diluted_eps, 2) if diluted_eps else None,
            "forward_pe": None,
            "peg_ratio": None,
            "earnings_growth_yoy_pct": _growth_pct(
                net_income, _previous_fact(annual_sec_snapshot, "net_income")
            ),
            "revenue_growth_yoy_pct": _growth_pct(
                revenue, _previous_fact(annual_sec_snapshot, "revenue")
            ),
            "price_to_sales": round(current_price * shares / revenue, 2)
            if shares and revenue else None,
            "note": "Forward estimates and point-in-time analyst consensus are unavailable.",
            "trailing_pe_basis": {
                "method": "price_divided_by_latest_filed_annual_diluted_eps",
                "eps": diluted_eps,
                "eps_metadata": fact_provenance(
                    annual_sec_snapshot, "diluted_eps", "annual"
                ),
                "warning": "This is not a reconstructed TTM P/E.",
            },
        },
        "smart_money_consensus": {
            "percent_institutions": None,
            "analyst_target_price": None,
            "current_price": round(current_price, 4),
            "price_trade_date": current_row["trade_date"],
        },
        "technical_and_momentum": {
            "moving_averages": {
                "day_50_ma": _average(closes, 50),
                "day_200_ma": _average(closes, 200),
            },
            "week_52_range": {
                "start": prices[-len(trailing_year)]["trade_date"],
                "end": current_row["trade_date"],
                "high": round(high, 4),
                "low": round(low, 4),
                "current_position_pct": range_position,
            },
            "recent_3_weeks_action": {"price_change_pct": change_3_weeks},
        },
        "recent_catalysts": catalysts,
        "recent_sec_filings": sec_events,
        "previous_report": build_previous_call_review(
            previous_report,
            evaluation_as_of=as_of,
            evaluation_price=current_price,
        ),
        "snapshot_metadata": {
            "schema_version": 2,
            "dataset_version": dataset_version,
            "price_as_of": current_row["trade_date"],
            "fundamentals_period_end": filing.get("period_end"),
            "fundamentals_filed_at": filing.get("filed_at"),
            "fundamentals_form": filing.get("form"),
            "sec_accession": filing.get("accession"),
            "annual_fundamentals_filed_at": (
                annual_sec_snapshot.get("filing") or {}
            ).get("filed_at"),
            "annual_sec_accession": (
                annual_sec_snapshot.get("filing") or {}
            ).get("accession"),
            "news_window_start": news_start.isoformat(),
            "news_as_of": (
                datetime.combine(
                    news_latest_date, datetime_time(21, 0), tzinfo=timezone.utc
                ).isoformat()
                if news_latest_date else None
            ),
            "look_ahead_protection": True,
        },
    }


def _parse_target(value: Any) -> float:
    try:
        parsed = float(str(value).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError) as error:
        raise SampleReportBuildError(f"Model returned an invalid target price: {value!r}.") from error
    if not math.isfinite(parsed) or parsed <= 0:
        raise SampleReportBuildError(f"Model returned an invalid target price: {value!r}.")
    return round(parsed, 2)


def _level(value: Any, field: str) -> str:
    text = str(value).strip().lower()
    for suffix in (" conviction", " risk"):
        if text.endswith(suffix):
            text = text[:-len(suffix)].strip()
    normalized = LEVELS.get(text)
    if normalized is None:
        raise SampleReportBuildError(f"Model returned an invalid {field}: {value!r}.")
    return normalized


def _format_metric(value: Any, suffix: str = "") -> str:
    if value is None:
        return "Unavailable"
    return f"{value}{suffix}"


def normalize_report(ticker: str, as_of: date, snapshot: dict, generated: dict) -> dict:
    """Normalize structured fields while preserving the model's report verbatim."""
    conclusion = str(generated.get("conclusion", "")).strip().upper()
    if conclusion not in {"BUY", "HOLD", "SELL"}:
        raise SampleReportBuildError(
            f"Model returned an invalid conclusion: {generated.get('conclusion')!r}."
        )
    conviction = _level(generated.get("conviction_level"), "conviction level")
    risk = _level(generated.get("risk_level"), "risk level")
    current_price = float(snapshot["smart_money_consensus"]["current_price"])
    target_price = _parse_target(generated.get("target_price"))
    upside = (target_price / current_price - 1) * 100
    upside_text = f"{upside:+.1f}%"
    reasoning = str(generated.get("reasoning") or "").strip()
    full_report = str(generated.get("full_report") or "").strip()
    if not reasoning:
        raise SampleReportBuildError("Model returned an empty reasoning field.")
    if not full_report:
        raise SampleReportBuildError("Model returned an empty full_report field.")

    required_envelope = {
        "report_schema_version", "analysis_as_of", "generated_at", "generation_mode",
        "model_tier", "model_provider", "model_name", "prompt_version",
        "agent_outputs", "generation_metadata",
    }
    missing = required_envelope - generated.keys()
    if missing:
        raise SampleReportBuildError(
            f"Generated report is missing provenance fields: {', '.join(sorted(missing))}."
        )
    report = {
        **generated,
        "ticker": ticker,
        "conclusion": conclusion,
        "conviction_level": conviction,
        "target_price": target_price,
        "upside_downside_pct": upside_text,
        "risk_level": risk,
        "reasoning": reasoning,
        "full_report": full_report,
        "raw_financial_data": snapshot,
    }
    report["agent_outputs"][0]["output"]["stance"] = conclusion
    report["agent_outputs"][0]["output"]["confidence"] = conviction
    return report


def build_pilot_report(
    ticker: str,
    as_of: date,
    output_path: Path,
    fixture_dir: Path = DEFAULT_FIXTURE_DIR,
    tier: ModelTier = ModelTier.LOCAL,
    retries: int = 3,
) -> dict:
    """Generate exactly one isolated report without changing the fixture or a database."""
    assert_live_read_source("build a frozen sample report pilot")
    fixture_dir = fixture_dir.resolve()
    manifest, data = load_fixture(fixture_dir, allow_draft=True)
    ticker = ticker.upper()
    if ticker not in manifest["tickers"]:
        raise SampleReportBuildError(f"Ticker {ticker} is not declared in the sample fixture.")

    snapshot = build_fixture_context(
        ticker,
        as_of,
        data["company_overview"],
        data["daily_prices"],
        data["stock_news"],
        report_input=_read_json(fixture_dir / "report_inputs" / f"{ticker}.json"),
        dataset_version=manifest["datasetVersion"],
    )
    analysis_as_of = datetime.combine(as_of, datetime_time(21, 0), tzinfo=timezone.utc)
    model_spec = get_model_spec(tier, temperature=0.1)
    local_digest = preflight_model(model_spec)
    executor, parser = create_analyst_agent(tier=tier, model_spec=model_spec)
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            generated = generate_investment_analysis(
                ticker,
                snapshot,
                analysis_as_of=analysis_as_of,
                generation_mode="historical_backfill",
                tier=tier,
                model_spec=model_spec,
                executor=executor,
                parser=parser,
                run_preflight=False,
                local_model_digest=local_digest,
            )
            report = normalize_report(ticker, as_of, snapshot, generated)
            _validate_investment_reports(
                manifest, {**data, "investment_reports": [report]}
            )
            break
        except Exception as error:
            last_error = error
            print(f"Pilot attempt {attempt}/{retries} failed: {error}", flush=True)
    else:
        raise SampleReportBuildError(
            f"Unable to generate pilot after {retries} attempts: {last_error}"
        )
    _write_json_atomic(output_path.resolve(), report)
    return report


def validate_pilot_report(
    report_path: Path,
    fixture_dir: Path = DEFAULT_FIXTURE_DIR,
) -> dict:
    """Validate an isolated pilot with the same rules used by the sample seeder."""
    manifest, data = load_fixture(fixture_dir.resolve(), allow_draft=True)
    report = _read_json(report_path.resolve())
    _validate_investment_reports(manifest, {**data, "investment_reports": [report]})
    return report


def build_pilot_snapshot(
    ticker: str,
    as_of: date,
    output_path: Path,
    fixture_dir: Path = DEFAULT_FIXTURE_DIR,
) -> dict:
    """Build and validate one point-in-time snapshot without calling an LLM."""
    fixture_dir = fixture_dir.resolve()
    manifest, data = load_fixture(fixture_dir, allow_draft=True)
    ticker = ticker.upper()
    report_input_path = fixture_dir / "report_inputs" / f"{ticker}.json"
    if not report_input_path.exists():
        raise SampleReportBuildError(f"Missing frozen report input: {report_input_path}")
    snapshot = build_fixture_context(
        ticker,
        as_of,
        data["company_overview"],
        data["daily_prices"],
        data["stock_news"],
        report_input=_read_json(report_input_path),
        dataset_version=manifest["datasetVersion"],
    )
    metadata = snapshot["snapshot_metadata"]
    if metadata["price_as_of"] > as_of.isoformat():
        raise SampleReportBuildError("Snapshot contains a future price.")
    if not metadata.get("fundamentals_filed_at") or metadata["fundamentals_filed_at"] > as_of.isoformat():
        raise SampleReportBuildError("Snapshot lacks point-in-time SEC fundamentals.")
    moving_averages = snapshot["technical_and_momentum"]["moving_averages"]
    if moving_averages["day_50_ma"] is None or moving_averages["day_200_ma"] is None:
        raise SampleReportBuildError("Snapshot lacks enough historical prices for 50/200-day MAs.")
    _write_json_atomic(output_path.resolve(), snapshot)
    return snapshot


def build_reports(
    fixture_dir: Path = DEFAULT_FIXTURE_DIR,
    schedule: dict[str, tuple[date, ...]] | None = None,
    selected_tickers: list[str] | None = None,
    import_reports: list[Path] | None = None,
    report_output_dir: Path = DEFAULT_REPORT_OUTPUT_DIR,
    tier: ModelTier = ModelTier.LOCAL,
    delay_seconds: float = 1.0,
    retries: int = 3,
) -> dict:
    assert_live_read_source("build frozen sample reports")
    fixture_dir = fixture_dir.resolve()
    manifest, data = load_fixture(fixture_dir, allow_draft=True)
    checkpoint_path = fixture_dir / ".investment_reports.checkpoint.json"
    reports = _read_json(checkpoint_path) if checkpoint_path.exists() else []

    schedule = schedule or {
        ticker: ACTIVE_REPORT_DATES if ticker in ACTIVE_TICKERS else (DEFAULT_SINGLE_REPORT_DATE,)
        for ticker in manifest["tickers"]
    }
    unknown = set(schedule) - set(manifest["tickers"])
    missing = set(manifest["tickers"]) - set(schedule)
    if unknown or missing:
        raise SampleReportBuildError(
            f"Schedule ticker mismatch: missing={sorted(missing)}, unknown={sorted(unknown)}"
        )

    expected_keys = {
        (ticker, as_of.isoformat())
        for ticker, dates in schedule.items()
        for as_of in dates
    }
    unexpected_checkpoint_keys = {
        (row["ticker"], row["analysis_as_of"][:10]) for row in reports
    } - expected_keys
    if unexpected_checkpoint_keys:
        raise SampleReportBuildError(
            f"Checkpoint contains reports outside the current schedule: "
            f"{sorted(unexpected_checkpoint_keys)}"
        )

    for report_path in import_reports or []:
        report = validate_pilot_report(report_path, fixture_dir=fixture_dir)
        key = (report["ticker"], report["analysis_as_of"][:10])
        if key not in expected_keys:
            raise SampleReportBuildError(
                f"Imported report {key} is outside the current schedule."
            )
        existing = next(
            (
                row for row in reports
                if (row["ticker"], row["analysis_as_of"][:10]) == key
            ),
            None,
        )
        if existing and existing != report:
            raise SampleReportBuildError(
                f"Checkpoint already contains a different report for {key}."
            )
        if not existing:
            reports.append(report)
        _write_historical_report_archive(report, report_output_dir)
    reports.sort(key=lambda row: (row["ticker"], row["analysis_as_of"]))
    if import_reports:
        _write_json_atomic(checkpoint_path, reports)

    completed = {(row["ticker"], row["analysis_as_of"][:10]) for row in reports}
    selected = [ticker.upper() for ticker in selected_tickers] if selected_tickers else list(manifest["tickers"])
    unknown_selected = set(selected) - set(manifest["tickers"])
    if unknown_selected:
        raise SampleReportBuildError(
            f"Unknown selected tickers: {sorted(unknown_selected)}"
        )

    model_spec = get_model_spec(tier, temperature=0.1)
    local_digest = preflight_model(model_spec)
    incompatible = [
        (row["ticker"], row["analysis_as_of"][:10])
        for row in reports
        if row.get("model_provider") != model_spec.provider
        or row.get("model_name") != model_spec.requested_model
        or row.get("prompt_version") != PROMPT_VERSION
    ]
    if incompatible:
        raise SampleReportBuildError(
            "Checkpoint/imported reports use a different provider, model, or prompt: "
            f"{incompatible}"
        )
    executor, parser = create_analyst_agent(
        tier=tier, model_spec=model_spec
    )
    total = len(expected_keys)
    for ticker in manifest["tickers"]:
        if ticker not in selected:
            continue
        for as_of in schedule[ticker]:
            key = (ticker, as_of.isoformat())
            if key in completed:
                continue
            prior_reports = [
                row for row in reports
                if row["ticker"] == ticker
                and row["analysis_as_of"][:10] < as_of.isoformat()
            ]
            previous_report = max(
                prior_reports,
                key=lambda row: row["analysis_as_of"],
                default=None,
            )
            snapshot = build_fixture_context(
                ticker,
                as_of,
                data["company_overview"],
                data["daily_prices"],
                data["stock_news"],
                report_input=_read_json(
                    fixture_dir / "report_inputs" / f"{ticker}.json"
                ),
                dataset_version=manifest["datasetVersion"],
                previous_report=previous_report,
            )
            last_error = None
            for attempt in range(1, retries + 1):
                try:
                    generated = generate_investment_analysis(
                        ticker,
                        snapshot,
                        analysis_as_of=datetime.combine(
                            as_of, datetime_time(21, 0), tzinfo=timezone.utc
                        ),
                        generation_mode="historical_backfill",
                        tier=tier,
                        model_spec=model_spec,
                        executor=executor,
                        parser=parser,
                        run_preflight=False,
                        local_model_digest=local_digest,
                    )
                    report = normalize_report(ticker, as_of, snapshot, generated)
                    _validate_investment_reports(
                        manifest, {**data, "investment_reports": [report]}
                    )
                    reports.append(report)
                    reports.sort(key=lambda row: (row["ticker"], row["analysis_as_of"]))
                    _write_json_atomic(checkpoint_path, reports)
                    _write_historical_report_archive(report, report_output_dir)
                    completed.add(key)
                    print(
                        f"[{len(completed & expected_keys)}/{total}] "
                        f"{ticker} {as_of} complete",
                        flush=True,
                    )
                    break
                except Exception as error:  # network/provider/parser failures are retried
                    last_error = error
                    print(
                        f"{ticker} {as_of} attempt {attempt}/{retries} failed: {error}",
                        flush=True,
                    )
                    if attempt < retries:
                        time.sleep(max(delay_seconds, 1.0))
            else:
                raise SampleReportBuildError(
                    f"Unable to generate {ticker} {as_of} after {retries} attempts: {last_error}"
                )
            if delay_seconds > 0 and len(completed) < total:
                time.sleep(delay_seconds)

    completed_expected = completed & expected_keys
    if completed_expected != expected_keys:
        pending = sorted(expected_keys - completed_expected)
        return {
            "rows": len(completed_expected),
            "staged": True,
            "pending": pending,
            "per_ticker": {
                ticker: sum(1 for row in reports if row["ticker"] == ticker)
                for ticker in manifest["tickers"]
            },
        }

    output_path = fixture_dir / manifest["files"]["investment_reports"]
    _write_json_atomic(output_path, reports)
    manifest["expectedRows"]["investment_reports"] = len(reports)
    coverage = [len(dates) for dates in schedule.values()]
    manifest["targetCoverage"]["reportsPerTickerMin"] = min(coverage)
    manifest["targetCoverage"]["reportsPerTickerMax"] = max(coverage)
    manifest["sources"]["investmentReports"] = (
        f"{model_spec.provider}/{model_spec.requested_model} historical analysis "
        "from frozen sample-data/v1 inputs"
    )
    manifest["datasetVersion"] = "v1-draft.6"
    _write_json_atomic(fixture_dir / "manifest.json", manifest)
    load_fixture(fixture_dir, allow_draft=True)
    checkpoint_path.unlink(missing_ok=True)
    return {
        "rows": len(reports),
        "staged": False,
        "pending": [],
        "per_ticker": {ticker: len(dates) for ticker, dates in schedule.items()},
    }


def materialize_checkpoint_reports(
    fixture_dir: Path = DEFAULT_FIXTURE_DIR,
    report_output_dir: Path = DEFAULT_REPORT_OUTPUT_DIR,
) -> list[Path]:
    """Write every validated staged report as an individual local archive file."""
    fixture_dir = fixture_dir.resolve()
    checkpoint_path = fixture_dir / ".investment_reports.checkpoint.json"
    if not checkpoint_path.exists():
        raise SampleReportBuildError(f"Checkpoint does not exist: {checkpoint_path}")
    manifest, data = load_fixture(fixture_dir, allow_draft=True)
    reports = _read_json(checkpoint_path)
    _validate_investment_reports(
        manifest, {**data, "investment_reports": reports}
    )
    return [
        _write_historical_report_archive(report, report_output_dir)
        for report in reports
    ]


def validate_report_schedule(
    fixture_dir: Path = DEFAULT_FIXTURE_DIR,
    schedule: dict[str, tuple[date, ...]] | None = None,
) -> dict[str, int]:
    """Validate every frozen point-in-time snapshot without invoking a model."""
    fixture_dir = fixture_dir.resolve()
    manifest, data = load_fixture(fixture_dir, allow_draft=True)
    schedule = schedule or {
        ticker: ACTIVE_REPORT_DATES if ticker in ACTIVE_TICKERS else (DEFAULT_SINGLE_REPORT_DATE,)
        for ticker in manifest["tickers"]
    }
    counts = {}
    for ticker in manifest["tickers"]:
        input_path = fixture_dir / "report_inputs" / f"{ticker}.json"
        if not input_path.exists():
            raise SampleReportBuildError(f"Missing frozen report input: {input_path}")
        report_input = _read_json(input_path)
        for as_of in schedule[ticker]:
            snapshot = build_fixture_context(
                ticker,
                as_of,
                data["company_overview"],
                data["daily_prices"],
                data["stock_news"],
                report_input=report_input,
                dataset_version=manifest["datasetVersion"],
            )
            metadata = snapshot["snapshot_metadata"]
            if metadata["price_as_of"] > as_of.isoformat():
                raise SampleReportBuildError(f"{ticker} {as_of} contains a future price.")
            if not metadata.get("fundamentals_filed_at"):
                raise SampleReportBuildError(f"{ticker} {as_of} has no SEC snapshot.")
            if metadata["fundamentals_filed_at"] > as_of.isoformat():
                raise SampleReportBuildError(f"{ticker} {as_of} contains a future filing.")
            if any(
                date.fromisoformat(item["date"]) > as_of
                for item in snapshot["recent_sec_filings"]
            ):
                raise SampleReportBuildError(
                    f"{ticker} {as_of} contains a future recent SEC filing."
                )
            if any(
                date.fromisoformat(item["date"]) > as_of
                for item in snapshot["recent_catalysts"]
            ):
                raise SampleReportBuildError(f"{ticker} {as_of} contains future news.")
            moving = snapshot["technical_and_momentum"]["moving_averages"]
            if moving["day_50_ma"] is None or moving["day_200_ma"] is None:
                raise SampleReportBuildError(f"{ticker} {as_of} lacks 50/200-day MAs.")
        counts[ticker] = len(schedule[ticker])
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument(
        "--report-output-dir",
        type=Path,
        default=DEFAULT_REPORT_OUTPUT_DIR,
    )
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Generate only these scheduled tickers into the resumable checkpoint.",
    )
    parser.add_argument(
        "--import-report",
        action="append",
        type=Path,
        help="Import one validated pilot into the checkpoint before generation.",
    )
    parser.add_argument(
        "--tier",
        choices=[tier.value for tier in ModelTier],
        default=ModelTier.LOCAL.value,
        help="Model tier; defaults to local Ollama.",
    )
    parser.add_argument("--pilot-ticker", help="Generate one isolated pilot ticker only.")
    parser.add_argument("--pilot-date", type=date.fromisoformat, help="Pilot date in YYYY-MM-DD.")
    parser.add_argument("--pilot-output", type=Path, help="Path for the isolated pilot JSON.")
    parser.add_argument(
        "--dry-run-output",
        type=Path,
        help="Write a point-in-time snapshot only; do not call a model.",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Verify the configured DeepSeek model ID without generating a report.",
    )
    parser.add_argument(
        "--validate-schedule",
        action="store_true",
        help="Validate all 50 frozen snapshots without calling a model.",
    )
    parser.add_argument(
        "--materialize-checkpoint",
        action="store_true",
        help="Write staged checkpoint reports as individual local JSON files without an LLM call.",
    )
    parser.add_argument(
        "--validate-pilot",
        type=Path,
        help="Validate an isolated pilot file without calling a model or writing a database.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tier = ModelTier(args.tier)
    if args.validate_pilot:
        report = validate_pilot_report(args.validate_pilot, fixture_dir=args.fixture_dir)
        print(
            f"Pilot validation passed: {report['ticker']} "
            f"{report['analysis_as_of'][:10]}"
        )
        return
    if args.preflight_only:
        model_spec = get_model_spec(tier, temperature=0.1)
        preflight_model(model_spec)
        print(
            f"Provider preflight passed: {model_spec.provider}/"
            f"{model_spec.requested_model}"
        )
        return
    if args.validate_schedule:
        counts = validate_report_schedule(args.fixture_dir)
        print(f"Schedule validation passed: {sum(counts.values())} reports {counts}")
        return
    if args.materialize_checkpoint:
        paths = materialize_checkpoint_reports(
            args.fixture_dir,
            report_output_dir=args.report_output_dir,
        )
        print(f"Materialized checkpoint reports: {len(paths)}")
        for path in paths:
            print(path)
        return
    if args.dry_run_output:
        if not args.pilot_ticker or not args.pilot_date or args.pilot_output:
            raise SampleReportBuildError(
                "Dry-run mode requires --pilot-ticker, --pilot-date, and --dry-run-output."
            )
        snapshot = build_pilot_snapshot(
            args.pilot_ticker,
            args.pilot_date,
            args.dry_run_output,
            fixture_dir=args.fixture_dir,
        )
        print(
            f"Dry-run snapshot: {args.pilot_ticker.upper()} "
            f"price={snapshot['snapshot_metadata']['price_as_of']} "
            f"filing={snapshot['snapshot_metadata']['fundamentals_filed_at']}"
        )
        print(f"Saved to: {args.dry_run_output.resolve()}")
        return
    if args.pilot_ticker or args.pilot_date or args.pilot_output:
        if not args.pilot_ticker or not args.pilot_date or not args.pilot_output:
            raise SampleReportBuildError(
                "Pilot mode requires --pilot-ticker, --pilot-date, and --pilot-output."
            )
        report = build_pilot_report(
            args.pilot_ticker,
            args.pilot_date,
            args.pilot_output,
            fixture_dir=args.fixture_dir,
            tier=tier,
            retries=args.retries,
        )
        print(
            f"Pilot report: {report['ticker']} {report['analysis_as_of'][:10]} "
            f"{report['conclusion']} ({report['conviction_level']})"
        )
        print(f"Saved to: {args.pilot_output.resolve()}")
        return
    result = build_reports(
        args.fixture_dir,
        selected_tickers=args.tickers,
        import_reports=args.import_report,
        report_output_dir=args.report_output_dir,
        tier=tier,
        delay_seconds=args.delay_seconds,
        retries=args.retries,
    )
    label = "Staged reports" if result["staged"] else "Frozen reports"
    print(f"{label}: {result['rows']} ({result['per_ticker']})")
    if result["staged"]:
        print(f"Pending scheduled reports: {len(result['pending'])}")
    print("DRAFT ONLY — redistribution review is still pending.")


if __name__ == "__main__":
    main()
