"""Shared auditable investment-report generation workflow."""

import json
import math
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from agents.market_analyst import create_analyst_agent
from core.llm_factory import ModelSpec, ModelTier, get_model_spec, preflight_model


REPORT_SCHEMA_VERSION = 2
WORKFLOW_NAME = "equity_research"
WORKFLOW_VERSION = "1.0.0"
AGENT_KEY = "market_analyst"
AGENT_VERSION = "1.0.0"
OUTPUT_SCHEMA_VERSION = 1
PROMPT_VERSION = "market-analyst/2.1.0"
TIER_LETTERS = {
    ModelTier.SMART: "S",
    ModelTier.NORMAL: "N",
    ModelTier.LOCAL: "L",
}
LEVELS = {"high": "High", "medium": "Medium", "low": "Low"}


class ReportGenerationError(ValueError):
    """Raised when a model response cannot become a canonical report."""


def _canonical_level(value: Any) -> str | None:
    normalized = str(value or "").strip().lower()
    for suffix in (" conviction", " risk"):
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()
    return LEVELS.get(normalized)


def _positive_number(value: Any, field: str) -> float:
    try:
        parsed = float(str(value).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError) as error:
        raise ReportGenerationError(f"Model returned an invalid {field}: {value!r}.") from error
    if not math.isfinite(parsed) or parsed <= 0:
        raise ReportGenerationError(f"Model returned an invalid {field}: {value!r}.")
    return parsed


def normalize_canonical_analysis(analysis: dict, snapshot: dict) -> dict:
    """Apply one canonical representation for live and historical reports."""
    conclusion = str(analysis.get("conclusion", "")).strip().upper()
    if conclusion not in {"BUY", "HOLD", "SELL"}:
        raise ReportGenerationError(
            f"Model returned an invalid conclusion: {analysis.get('conclusion')!r}."
        )
    conviction = _canonical_level(analysis.get("conviction_level"))
    risk = _canonical_level(analysis.get("risk_level"))
    if conviction is None:
        raise ReportGenerationError(
            f"Model returned an invalid conviction level: {analysis.get('conviction_level')!r}."
        )
    if risk is None:
        raise ReportGenerationError(
            f"Model returned an invalid risk level: {analysis.get('risk_level')!r}."
        )

    current_price = _positive_number(
        (snapshot.get("smart_money_consensus") or {}).get("current_price"),
        "snapshot current price",
    )
    target_price = round(_positive_number(analysis.get("target_price"), "target price"), 2)
    upside = (target_price / current_price - 1) * 100
    reasoning = str(analysis.get("reasoning") or "").strip()
    full_report = str(analysis.get("full_report") or "").strip()
    if not reasoning or not full_report:
        raise ReportGenerationError("Model returned an empty reasoning or full_report field.")

    return {
        **analysis,
        "conclusion": conclusion,
        "conviction_level": conviction,
        "target_price": target_price,
        "upside_downside_pct": f"{upside:+.1f}%",
        "risk_level": risk,
        "reasoning": reasoning,
        "full_report": full_report,
    }


def build_analysis_prompt(ticker: str, analysis_as_of: datetime, snapshot: dict) -> str:
    previous = snapshot.get("previous_report")
    prior_instruction = (
        "Review the supplied previous_report and assess it only against evidence available "
        "at this analysis date."
        if previous
        else "State in a Prior Call Review section that no earlier SignalLedger call exists."
    )
    return f"""Prepare an equity research report for {ticker} as of {analysis_as_of.isoformat()}.
Use only the supplied point-in-time JSON snapshot. Do not use company-specific knowledge,
events, filings, or prices after the analysis date. Missing values remain unavailable and
must reduce conviction; never infer them from later data. {prior_instruction}
Fields ending in `_pct` and `percent_institutions` are percentage points: for example,
`62.97` means 62.97%, not 0.6297% or 6,297%.

PERIOD AND VALUATION RULES
- Treat each block's statement metadata as authoritative. Never relabel an annual value
  with the latest quarterly period end.
- Never calculate a ratio from annual, quarterly, YTD, TTM, or instant values unless their
  periods are compatible. In particular, do not divide YTD free cash flow by annual revenue.
- `trailing_pe_basis` states whether the P/E is true provider TTM or a latest-annual-EPS
  fallback. Describe that limitation exactly.
- The 12-month target is an illustrative scenario target, not analyst consensus. In the
  Financial and Valuation Analysis section, state the EPS basis and period, assumed 12-month
  EPS growth, derived forward EPS, exit P/E, and the formula `forward EPS × exit P/E = target`.
  Clearly label growth and multiple inputs as assumptions. If the basis is incomplete or
  stale, reduce conviction and call the target speculative.

The Markdown report must state `Analysis As Of: {analysis_as_of.date().isoformat()}`.

{json.dumps(snapshot, indent=2, ensure_ascii=False)}
"""


def _to_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_provider_metadata(message: Any, spec: ModelSpec, local_digest: str | None) -> dict:
    response = getattr(message, "response_metadata", None) or {}
    usage_metadata = getattr(message, "usage_metadata", None) or {}
    token_usage = response.get("token_usage") or response.get("usage") or {}

    input_tokens = _to_int(
        usage_metadata.get("input_tokens", token_usage.get("prompt_tokens"))
    )
    output_tokens = _to_int(
        usage_metadata.get("output_tokens", token_usage.get("completion_tokens"))
    )
    total_tokens = _to_int(
        usage_metadata.get("total_tokens", token_usage.get("total_tokens"))
    )
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    response_model = response.get("model_name") or response.get("model")
    finish_reason = response.get("finish_reason") or response.get("done_reason")
    fingerprint = response.get("system_fingerprint")
    return {
        "response_model": str(response_model) if response_model else None,
        "system_fingerprint": str(fingerprint) if fingerprint else None,
        "local_model_digest": local_digest if spec.provider == "ollama" else None,
        "finish_reason": str(finish_reason) if finish_reason else None,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        },
    }


def _evidence_refs(ticker: str, snapshot: dict) -> list[str]:
    refs: list[str] = []
    consensus = snapshot.get("smart_money_consensus") or {}
    price_date = consensus.get("price_trade_date")
    if price_date:
        refs.append(f"price:{ticker}:{price_date}")
    metadata = snapshot.get("snapshot_metadata") or {}
    accession = metadata.get("sec_accession")
    if accession:
        refs.append(f"sec:{ticker}:{accession}")
    for catalyst in snapshot.get("recent_catalysts") or []:
        evidence_ref = catalyst.get("evidence_ref") if isinstance(catalyst, dict) else None
        if evidence_ref:
            refs.append(str(evidence_ref))
        elif isinstance(catalyst, dict) and catalyst.get("finnhub_id") is not None:
            refs.append(f"news:{ticker}:{catalyst['finnhub_id']}")
    return list(dict.fromkeys(refs))


def _provenance_status(run: dict) -> str:
    usage = run["usage"]
    complete = (
        bool(run["response_model"])
        and bool(run["finish_reason"])
        and all(usage[key] is not None for key in ("input_tokens", "output_tokens", "total_tokens"))
        and (run["provider"] != "ollama" or bool(run["local_model_digest"]))
    )
    return "complete" if complete else "partial"


def generate_investment_analysis(
    ticker: str,
    snapshot: dict,
    *,
    analysis_as_of: datetime,
    generation_mode: str,
    tier: ModelTier = ModelTier.NORMAL,
    model_spec: ModelSpec | None = None,
    executor=None,
    parser=None,
    run_preflight: bool = True,
    local_model_digest: str | None = None,
) -> dict:
    """Run the current one-agent workflow and return a schema-v2 report envelope."""
    if analysis_as_of.tzinfo is None:
        raise ValueError("analysis_as_of must include a timezone.")
    ticker = ticker.upper()
    spec = model_spec or get_model_spec(tier=tier, temperature=0.1)
    local_digest = preflight_model(spec) if run_preflight else local_model_digest
    if executor is None or parser is None:
        executor, parser = create_analyst_agent(tier=tier, model_spec=spec)

    prompt = build_analysis_prompt(ticker, analysis_as_of, snapshot)
    result = executor.invoke({"messages": [("user", prompt)]})
    message = result["messages"][-1]
    parsed = parser.parse(message.content)
    analysis = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed.dict()
    analysis = normalize_canonical_analysis(analysis, snapshot)

    run_id = f"run-market-analyst-{uuid4()}"
    provider_metadata = normalize_provider_metadata(message, spec, local_digest)
    run = {
        "run_id": run_id,
        "agent_key": AGENT_KEY,
        "agent_version": AGENT_VERSION,
        "sequence": 1,
        "depends_on": [],
        "provider": spec.provider,
        "tier": spec.tier.value,
        "requested_model": spec.requested_model,
        **provider_metadata,
        "prompt_version": PROMPT_VERSION,
        "temperature": spec.temperature,
        "response_format": spec.response_format,
    }
    usage = run["usage"]
    model_key = run["response_model"] or run["requested_model"]
    generation_metadata = {
        "schema_version": 2,
        "workflow_name": WORKFLOW_NAME,
        "workflow_version": WORKFLOW_VERSION,
        "final_run_id": run_id,
        "provenance_status": _provenance_status(run),
        "aggregate_usage": {
            "calls": 1,
            **usage,
            "by_model": [
                {
                    "provider": spec.provider,
                    "model": model_key,
                    "calls": 1,
                    **usage,
                }
            ],
        },
        "agent_runs": [run],
    }
    agent_outputs = [
        {
            "run_id": run_id,
            "agent_key": AGENT_KEY,
            "agent_version": AGENT_VERSION,
            "output_schema_version": OUTPUT_SCHEMA_VERSION,
            "status": "completed",
            "output": {
                "stance": str(analysis.get("conclusion", "")).upper(),
                "confidence": str(analysis.get("conviction_level", "")),
                "summary": str(analysis.get("reasoning", "")),
                "evidence_refs": _evidence_refs(ticker, snapshot),
            },
        }
    ]
    return {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "ticker": ticker,
        "analysis_as_of": analysis_as_of.astimezone(timezone.utc).isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generation_mode": generation_mode,
        "model_tier": TIER_LETTERS[tier],
        "model_provider": spec.provider,
        "model_name": run["response_model"],
        "prompt_version": PROMPT_VERSION,
        **analysis,
        "raw_financial_data": snapshot,
        "agent_outputs": agent_outputs,
        "generation_metadata": generation_metadata,
    }
