"""Deterministic interim evaluation for the previous investment call."""

from datetime import date, datetime
from typing import Any


VERDICT_METHOD = "interim-price-direction/1.0.0"
BUY_SELL_THRESHOLD_PCT = 2.0
HOLD_BAND_PCT = 5.0


def _date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


def _price_then(report: dict) -> float | None:
    direct = report.get("price_then")
    if direct is not None:
        return float(direct)
    snapshot = report.get("raw_financial_data") or {}
    value = (snapshot.get("smart_money_consensus") or {}).get("current_price")
    return float(value) if value is not None else None


def classify_previous_call(conclusion: str, performance_pct: float) -> str:
    signal = conclusion.strip().upper()
    if signal == "BUY":
        if performance_pct >= BUY_SELL_THRESHOLD_PCT:
            return "FAVORABLE"
        if performance_pct <= -BUY_SELL_THRESHOLD_PCT:
            return "ADVERSE"
        return "FLAT"
    if signal == "SELL":
        if performance_pct <= -BUY_SELL_THRESHOLD_PCT:
            return "FAVORABLE"
        if performance_pct >= BUY_SELL_THRESHOLD_PCT:
            return "ADVERSE"
        return "FLAT"
    if signal == "HOLD":
        if performance_pct > HOLD_BAND_PCT:
            return "UPSIDE_BREAKOUT"
        if performance_pct < -HOLD_BAND_PCT:
            return "DOWNSIDE_BREAKDOWN"
        return "STABLE"
    return "UNCLASSIFIED"


def build_previous_call_review(
    previous_report: dict | None,
    *,
    evaluation_as_of: date,
    evaluation_price: float,
) -> dict | None:
    if not previous_report:
        return None
    analysis_as_of = previous_report.get("analysis_as_of") or previous_report.get("generated_at")
    price_then = _price_then(previous_report)
    conclusion = str(previous_report.get("conclusion") or "").upper()
    if not analysis_as_of or not price_then or evaluation_price <= 0:
        return None
    performance = round((evaluation_price / price_then - 1) * 100, 2)
    return {
        "report_schema_version": previous_report.get("report_schema_version"),
        "analysis_as_of": str(analysis_as_of),
        "conclusion": conclusion,
        "conviction_level": previous_report.get("conviction_level"),
        "target_price": previous_report.get("target_price"),
        "price_then": round(price_then, 4),
        "evaluation_as_of": evaluation_as_of.isoformat(),
        "evaluation_price": round(float(evaluation_price), 4),
        "days_elapsed": (evaluation_as_of - _date(analysis_as_of)).days,
        "performance_since_pct": performance,
        "verdict": classify_previous_call(conclusion, performance),
        "verdict_status": "interim",
        "verdict_method": VERDICT_METHOD,
    }
