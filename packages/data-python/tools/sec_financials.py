"""Free SEC filing ingestion with point-in-time financial snapshots."""

import os
import subprocess
from datetime import date, timedelta
from typing import Any

import requests


SEC_DATA_BASE = "https://data.sec.gov"
SEC_WWW_BASE = "https://www.sec.gov"
FINANCIAL_FORMS = {"10-K", "10-Q"}
FACT_TAGS = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "diluted_eps": ("EarningsPerShareDiluted",),
    "total_assets": ("Assets",),
    "total_liabilities": ("Liabilities",),
    "stockholders_equity": (
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ),
    "cash": (
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ),
    "long_term_debt_current": (
        "LongTermDebtCurrent",
        "LongTermDebtAndFinanceLeaseObligationsCurrent",
    ),
    "long_term_debt_noncurrent": (
        "LongTermDebtNoncurrent",
        "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
    ),
    "long_term_debt_total": (
        "LongTermDebt",
        "LongTermDebtAndCapitalLeaseObligations",
    ),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capital_expenditures": (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsForProceedsFromProductiveAssets",
    ),
    "shares_outstanding": (
        "CommonStockSharesOutstanding",
        "EntityCommonStockSharesOutstanding",
    ),
}


class SecFinancialsError(RuntimeError):
    """Raised when a usable SEC snapshot cannot be produced."""


def sec_user_agent() -> str:
    configured = os.getenv("SEC_USER_AGENT", "").strip()
    if configured:
        return configured
    email = subprocess.run(
        ["git", "config", "--get", "user.email"],
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not email:
        raise SecFinancialsError(
            "Set SEC_USER_AGENT to an application name and contact email."
        )
    return f"SignalLedger/1.0 {email}"


def get_sec_json(path: str, user_agent: str, base_url: str = SEC_DATA_BASE) -> dict:
    response = requests.get(
        f"{base_url}{path}",
        headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def find_cik(ticker: str, user_agent: str) -> str:
    tickers = get_sec_json(
        "/files/company_tickers.json", user_agent, base_url=SEC_WWW_BASE
    )
    for item in tickers.values():
        if item.get("ticker", "").upper() == ticker.upper():
            return str(item["cik_str"]).zfill(10)
    raise SecFinancialsError(f"SEC company_tickers.json has no CIK for {ticker}.")


def filing_rows(submissions: dict) -> list[dict]:
    recent = submissions.get("filings", {}).get("recent", {})
    keys = (
        "accessionNumber",
        "filingDate",
        "reportDate",
        "acceptanceDateTime",
        "form",
        "primaryDocument",
    )
    count = len(recent.get("accessionNumber", []))
    return [
        {key: recent.get(key, [None] * count)[index] for key in keys}
        for index in range(count)
    ]


def _fact_history(
    companyfacts: dict, aliases: tuple[str, ...], filing: dict
) -> dict | None:
    us_gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    for tag in aliases:
        fact = us_gaap.get(tag)
        if not fact:
            continue
        candidates: list[dict[str, Any]] = []
        for unit, entries in fact.get("units", {}).items():
            for entry in entries:
                if (
                    entry.get("accn") == filing["accessionNumber"]
                    and entry.get("form") == filing["form"]
                    and entry.get("filed") == filing["filingDate"]
                ):
                    candidates.append(
                        {
                            "period_start": entry.get("start"),
                            "period_end": entry.get("end"),
                            "value": entry.get("val"),
                            "unit": unit,
                            "fiscal_year": entry.get("fy"),
                            "fiscal_period": entry.get("fp"),
                            "frame": entry.get("frame"),
                        }
                    )
        if candidates:
            unique = {
                (
                    row["period_start"],
                    row["period_end"],
                    row["value"],
                    row["unit"],
                ): row
                for row in candidates
            }
            history = sorted(
                unique.values(),
                key=lambda row: (row["period_end"] or "", row["period_start"] or ""),
            )
            return {"tag": tag, "label": fact.get("label"), "history": history}
    return None


def build_sec_snapshots(
    ticker: str,
    as_of: date,
    *,
    earliest_as_of: date | None = None,
    user_agent: str | None = None,
    submissions: dict | None = None,
    companyfacts: dict | None = None,
) -> dict:
    """Return all 10-K/10-Q snapshots available on or before ``as_of``."""
    ticker = ticker.upper()
    user_agent = user_agent or sec_user_agent()
    cik = find_cik(ticker, user_agent) if submissions is None or companyfacts is None else None
    if submissions is None:
        submissions = get_sec_json(f"/submissions/CIK{cik}.json", user_agent)
    if companyfacts is None:
        companyfacts = get_sec_json(f"/api/xbrl/companyfacts/CIK{cik}.json", user_agent)
    if cik is None:
        cik = str(submissions.get("cik") or companyfacts.get("cik") or "").zfill(10)

    rows = filing_rows(submissions)
    all_eligible = [
        row
        for row in rows
        if row.get("form") in FINANCIAL_FORMS
        and row.get("filingDate")
        and date.fromisoformat(row["filingDate"]) <= as_of
    ]
    if not all_eligible:
        raise SecFinancialsError(
            f"No SEC 10-K/10-Q filed for {ticker} on or before {as_of}."
        )

    cutoff = earliest_as_of or (as_of - timedelta(days=550))
    baselines = [
        baseline
        for form in FINANCIAL_FORMS
        if (baseline := max(
            (
                row for row in all_eligible
                if row["form"] == form
                and date.fromisoformat(row["filingDate"]) <= cutoff
            ),
            key=lambda row: row["filingDate"],
            default=None,
        )) is not None
    ]
    eligible = [
        row for row in all_eligible
        if date.fromisoformat(row["filingDate"]) >= cutoff
    ]
    for baseline in baselines:
        if baseline not in eligible:
            eligible.append(baseline)

    snapshots = []
    for filing in sorted(eligible, key=lambda row: row["filingDate"]):
        facts = {
            key: _fact_history(companyfacts, aliases, filing)
            for key, aliases in FACT_TAGS.items()
        }
        snapshots.append(
            {
                "cik": cik,
                "entity_name": companyfacts.get("entityName"),
                "filing": {
                    "form": filing["form"],
                    "accession": filing["accessionNumber"],
                    "filed_at": filing["filingDate"],
                    "accepted_at": filing.get("acceptanceDateTime"),
                    "period_end": filing.get("reportDate"),
                    "primary_document": filing.get("primaryDocument"),
                },
                "facts": facts,
            }
        )

    recent_events = [
        row
        for row in rows
        if row.get("form") == "8-K"
        and row.get("filingDate")
        and date.fromisoformat(row["filingDate"]) <= as_of
    ]
    return {
        "ticker": ticker,
        "cik": cik,
        "entity_name": companyfacts.get("entityName"),
        "snapshots": snapshots,
        "recent_8k_events": recent_events,
    }


def select_sec_snapshot(
    report_input: dict | None,
    as_of: date,
    forms: set[str] | None = None,
) -> dict:
    """Select the latest filing known at ``as_of``; supports legacy v1 inputs."""
    if not report_input:
        return {}
    snapshots = report_input.get("sec_snapshots")
    if snapshots is None:
        legacy = report_input.get("sec_snapshot")
        snapshots = [legacy] if legacy else []
    eligible = [
        snapshot
        for snapshot in snapshots
        if (snapshot.get("filing") or {}).get("filed_at")
        and date.fromisoformat(snapshot["filing"]["filed_at"]) <= as_of
        and (forms is None or snapshot["filing"].get("form") in forms)
    ]
    if not eligible:
        return {}
    return max(eligible, key=lambda item: item["filing"]["filed_at"])


def latest_fact_value(snapshot: dict | None, key: str) -> float | None:
    fact = (snapshot or {}).get("facts", {}).get(key)
    history = fact.get("history") if isinstance(fact, dict) else None
    if not history:
        return None
    value = history[-1].get("value")
    return float(value) if value is not None else None


def previous_fact_value(snapshot: dict | None, key: str) -> float | None:
    fact = (snapshot or {}).get("facts", {}).get(key)
    history = fact.get("history") if isinstance(fact, dict) else None
    if not history or len(history) < 2:
        return None
    latest_end = history[-1].get("period_end")
    for row in reversed(history[:-1]):
        if row.get("period_end") != latest_end and row.get("value") is not None:
            return float(row["value"])
    return None


def fact_provenance(
    snapshot: dict | None,
    key: str,
    period_type: str,
) -> dict | None:
    fact = (snapshot or {}).get("facts", {}).get(key)
    history = fact.get("history") if isinstance(fact, dict) else None
    if not history:
        return None
    row = history[-1]
    filing = (snapshot or {}).get("filing") or {}
    return {
        "source": "SEC companyfacts",
        "tag": fact.get("tag"),
        "accession": filing.get("accession"),
        "form": filing.get("form"),
        "filed_at": filing.get("filed_at"),
        "period_start": row.get("period_start"),
        "period_end": row.get("period_end"),
        "period_type": period_type,
        "unit": row.get("unit"),
    }
