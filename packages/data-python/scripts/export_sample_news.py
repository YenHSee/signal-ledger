"""Fetch and freeze a compact 2026 YTD news fixture for sample mode."""

import argparse
import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from runtime_mode import assert_live_read_source
from scripts.seed_sample_data import load_fixture
from tools.finnhub_news import get_company_news
from utils.data_transformer import transform_finnhub_news_to_db


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_DIR = REPO_ROOT / "sample-data" / "v1"
DEFAULT_START = date(2026, 1, 2)
DEFAULT_END = date(2026, 7, 17)
DEFAULT_ANOMALY_START = date(2026, 4, 1)
DEFAULT_REPORT_DATES = (
    date(2026, 1, 9),
    date(2026, 1, 23),
    date(2026, 2, 6),
    date(2026, 2, 20),
    date(2026, 3, 6),
    date(2026, 3, 20),
    date(2026, 3, 31),
)
BIG_MOVE_PCT = 2.0
VOLUME_SPIKE_RATIO = 2.0
VOLUME_AVG_WINDOW = 30
CHECKPOINT_SCHEMA_VERSION = 1
DATASET_VERSION = "v1-draft.5"

SOURCE_TIERS = {
    "reuters": 1,
    "bloomberg": 1,
    "wall street journal": 1,
    "the wall street journal": 1,
    "associated press": 1,
    "dow jones": 1,
    "dowjones": 1,
    "cnbc": 2,
    "marketwatch": 2,
    "barrons": 2,
    "barron's": 2,
    "yahoo finance": 3,
    "yahoo": 3,
    "seeking alpha": 3,
    "seekingalpha": 3,
    "business wire": 3,
    "businesswire": 3,
    "pr newswire": 3,
    "prnewswire": 3,
    "benzinga": 4,
    "motley fool": 4,
    "the motley fool": 4,
    "zacks": 4,
}
DEFAULT_SOURCE_TIER = 5
TICKER_HEADLINE_ALIASES = {
    "AAPL": ("aapl", "apple"),
    "MSFT": ("msft", "microsoft"),
    "NVDA": ("nvda", "nvidia"),
    "GOOGL": ("googl", "alphabet", "google"),
    "AMZN": ("amzn", "amazon"),
    "META": ("meta", "facebook", "instagram", "whatsapp"),
    "TSLA": ("tsla", "tesla"),
    "AMD": ("amd", "advanced micro devices"),
    "JPM": ("jpm", "jpmorgan", "jp morgan"),
    "WMT": ("wmt", "walmart", "sams club", "sam s club"),
}


class SampleNewsExportError(RuntimeError):
    """Raised when YTD news cannot be frozen safely."""


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


def normalize_headline(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", value.casefold())).strip()


def _related_symbols(value: Any) -> set[str]:
    if not isinstance(value, str):
        return set()
    return {part.strip().upper() for part in value.split(",") if part.strip()}


def _source_tier(source: str) -> int:
    return SOURCE_TIERS.get(source.strip().casefold(), DEFAULT_SOURCE_TIER)


def _headline_mentions_ticker(ticker: str, headline: str) -> bool:
    normalized = f" {normalize_headline(headline)} "
    aliases = TICKER_HEADLINE_ALIASES.get(ticker.upper(), (ticker.casefold(),))
    return any(f" {normalize_headline(alias)} " in normalized for alias in aliases)


def rank_news_candidates(
    ticker: str,
    raw_rows: list[dict],
    start: date,
    end: date,
    limit: int = 10,
) -> list[dict]:
    """Rank complete, directly related headlines and remove syndicated duplicates."""
    ticker = ticker.upper()
    direct_by_id = {}
    for item in raw_rows:
        try:
            news_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        related = _related_symbols(item.get("related"))
        direct_by_id[news_id] = not related or ticker in related

    normalized = transform_finnhub_news_to_db(ticker, raw_rows)
    candidates = []
    for row in normalized:
        trade_date = date.fromisoformat(row["trade_date"])
        if not start <= trade_date <= end:
            continue
        if not row.get("source") or not row.get("url") or not row.get("headline"):
            continue
        if not direct_by_id.get(row["finnhub_id"], False):
            continue
        if not _headline_mentions_ticker(ticker, row["headline"]):
            continue
        row["summary"] = ""
        candidates.append(row)

    def rank(row: dict) -> tuple:
        return (
            0 if direct_by_id.get(row["finnhub_id"], False) else 1,
            _source_tier(row["source"]),
            -int(row["datetime"]),
            int(row["finnhub_id"]),
        )

    best_by_headline = {}
    for row in sorted(candidates, key=rank):
        headline_key = normalize_headline(row["headline"])
        if headline_key and headline_key not in best_by_headline:
            best_by_headline[headline_key] = row
    return sorted(best_by_headline.values(), key=rank)[:limit]


def compute_anomaly_candidates(
    rows: list[dict],
    start: date = DEFAULT_ANOMALY_START,
    end: date = DEFAULT_END,
) -> list[dict]:
    """Return YTD price/volume anomalies ranked by normalized strength."""
    ordered = sorted(rows, key=lambda row: row["trade_date"])
    candidates = []
    for index, row in enumerate(ordered):
        trade_date = date.fromisoformat(row["trade_date"])
        if not start <= trade_date <= end:
            continue
        previous = ordered[index - 1] if index > 0 else None
        close = float(row["close_price"]) if row.get("close_price") is not None else None
        previous_close = (
            float(previous["close_price"])
            if previous and previous.get("close_price") is not None
            else None
        )
        change_pct = (
            (close - previous_close) / previous_close * 100
            if close is not None and previous_close
            else None
        )
        window = ordered[max(0, index - (VOLUME_AVG_WINDOW - 1)):index + 1]
        volumes = [float(item["volume"]) for item in window if item.get("volume") is not None]
        average_volume = sum(volumes) / len(volumes) if volumes else None
        volume = float(row["volume"]) if row.get("volume") is not None else None
        volume_ratio = volume / average_volume if volume is not None and average_volume else None
        is_big_move = change_pct is not None and abs(change_pct) >= BIG_MOVE_PCT
        is_volume_spike = volume_ratio is not None and volume_ratio >= VOLUME_SPIKE_RATIO
        if not is_big_move and not is_volume_spike:
            continue
        candidates.append(
            {
                "date": trade_date,
                "change_pct": change_pct,
                "volume_ratio": volume_ratio,
                "score": max(
                    abs(change_pct) / BIG_MOVE_PCT if change_pct is not None else 0,
                    volume_ratio if volume_ratio is not None else 0,
                ),
            }
        )
    return sorted(candidates, key=lambda item: (-item["score"], item["date"]))


def balance_anomaly_dates(candidates: list[dict]) -> list[date]:
    """Prioritize the strongest anomaly in each month, then remaining strength."""
    by_month = defaultdict(list)
    for candidate in candidates:
        by_month[(candidate["date"].year, candidate["date"].month)].append(candidate)
    monthly_first = [by_month[month][0] for month in sorted(by_month)]
    monthly_dates = {candidate["date"] for candidate in monthly_first}
    remaining = [candidate for candidate in candidates if candidate["date"] not in monthly_dates]
    return [candidate["date"] for candidate in monthly_first + remaining]


def _checkpoint_signature(
    manifest: dict,
    start: date,
    end: date,
    report_dates: tuple[date, ...],
) -> dict:
    return {
        "tickers": manifest["tickers"],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "reportDates": [item.isoformat() for item in report_dates],
        "newsPerTickerMax": manifest["targetCoverage"]["newsPerTickerMax"],
    }


def _load_checkpoint(path: Path, signature: dict) -> dict:
    if not path.exists():
        return {
            "schemaVersion": CHECKPOINT_SCHEMA_VERSION,
            "signature": signature,
            "requests": {},
        }
    checkpoint = _read_json(path)
    if (
        checkpoint.get("schemaVersion") != CHECKPOINT_SCHEMA_VERSION
        or checkpoint.get("signature") != signature
        or not isinstance(checkpoint.get("requests"), dict)
    ):
        raise SampleNewsExportError(
            f"Checkpoint configuration does not match this backfill: {path}"
        )
    return checkpoint


def _request_candidates(
    ticker: str,
    start: date,
    end: date,
    checkpoint: dict,
    checkpoint_path: Path,
) -> list[dict]:
    key = f"{ticker}|{start.isoformat()}|{end.isoformat()}"
    cached = checkpoint["requests"].get(key)
    if cached is not None:
        return cached["candidates"]
    raw_rows = get_company_news(
        ticker,
        start.isoformat(),
        end.isoformat(),
        max_retries=3,
        strict=True,
    )
    candidates = rank_news_candidates(ticker, raw_rows, start, end)
    checkpoint["requests"][key] = {
        "rawCount": len(raw_rows),
        "candidates": candidates,
    }
    _write_json_atomic(checkpoint_path, checkpoint)
    return candidates


def _add_candidates(
    selected: list[dict],
    candidates: list[dict],
    seen_ids: set[tuple[int, str]],
    seen_headlines: set[str],
    limit: int,
) -> int:
    if limit <= 0:
        return 0
    added = 0
    for row in candidates:
        id_key = (row["finnhub_id"], row["symbol"])
        headline_key = normalize_headline(row["headline"])
        if id_key in seen_ids or headline_key in seen_headlines:
            continue
        selected.append(row)
        seen_ids.add(id_key)
        seen_headlines.add(headline_key)
        added += 1
        if added == limit:
            break
    return added


def export_news(
    fixture_dir: Path = DEFAULT_FIXTURE_DIR,
    start: date = DEFAULT_START,
    end: date = DEFAULT_END,
    report_dates: tuple[date, ...] = DEFAULT_REPORT_DATES,
    per_window: int = 2,
) -> dict:
    if end < start:
        raise SampleNewsExportError("News end date must not precede the start date.")
    if any(report_date < start or report_date > end for report_date in report_dates):
        raise SampleNewsExportError("Every report anchor must fall inside the news range.")
    assert_live_read_source("export sample news")

    fixture_dir = fixture_dir.resolve()
    manifest, data = load_fixture(fixture_dir, allow_draft=True)
    max_per_ticker = manifest["targetCoverage"]["newsPerTickerMax"]
    signature = _checkpoint_signature(manifest, start, end, report_dates)
    checkpoint_path = fixture_dir / ".news-backfill.checkpoint.json"
    checkpoint = _load_checkpoint(checkpoint_path, signature)
    fetched_at = datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc).isoformat()
    frozen_rows = []
    counts = {}

    prices_by_ticker = defaultdict(list)
    for row in data["daily_prices"]:
        prices_by_ticker[row["symbol"]].append(row)

    for ticker in manifest["tickers"]:
        selected = []
        seen_ids = set()
        seen_headlines = set()

        for report_date in report_dates:
            window_start = max(start, report_date - timedelta(days=6))
            candidates = _request_candidates(
                ticker,
                window_start,
                report_date,
                checkpoint,
                checkpoint_path,
            )
            _add_candidates(
                selected,
                candidates,
                seen_ids,
                seen_headlines,
                min(per_window, max_per_ticker - len(selected)),
            )
            print(
                f"{ticker} Q1 anchor {report_date}: {len(selected)}/{max_per_ticker} selected",
                flush=True,
            )

        anomalies = compute_anomaly_candidates(prices_by_ticker[ticker], DEFAULT_ANOMALY_START, end)
        for anomaly_date in balance_anomaly_dates(anomalies):
            if len(selected) >= max_per_ticker:
                break
            candidates = _request_candidates(
                ticker,
                anomaly_date,
                anomaly_date,
                checkpoint,
                checkpoint_path,
            )
            _add_candidates(selected, candidates, seen_ids, seen_headlines, 1)

        if not selected:
            raise SampleNewsExportError(f"No frozen news was selected for {ticker}.")
        if len(selected) > max_per_ticker:
            raise SampleNewsExportError(f"{ticker} exceeds the news fixture cap.")
        for row in selected:
            row["summary"] = ""
            row["fetched_at"] = fetched_at
        frozen_rows.extend(selected)
        counts[ticker] = len(selected)
        print(f"{ticker} complete: {len(selected)} frozen rows", flush=True)

    keys = [(row["finnhub_id"], row["symbol"]) for row in frozen_rows]
    headline_keys = [(row["symbol"], normalize_headline(row["headline"])) for row in frozen_rows]
    if len(keys) != len(set(keys)):
        raise SampleNewsExportError("Selected news contains duplicate Finnhub ID/symbol pairs.")
    if len(headline_keys) != len(set(headline_keys)):
        raise SampleNewsExportError("Selected news contains duplicate normalized headlines.")
    if len(frozen_rows) > len(manifest["tickers"]) * max_per_ticker:
        raise SampleNewsExportError("Selected news exceeds the dataset-wide cap.")
    if any(row["summary"] != "" for row in frozen_rows):
        raise SampleNewsExportError("Frozen news summaries must be empty.")
    if any(
        not start <= date.fromisoformat(row["trade_date"]) <= end
        for row in frozen_rows
    ):
        raise SampleNewsExportError("Selected news contains an out-of-range date.")

    frozen_rows.sort(key=lambda row: (row["symbol"], row["datetime"], row["finnhub_id"]))
    manifest["datasetVersion"] = DATASET_VERSION
    manifest["expectedRows"]["stock_news"] = len(frozen_rows)
    manifest["sources"]["news"] = (
        "Finnhub company-news 2026 YTD curated report-window and price-anomaly snapshot; "
        "headline metadata only"
    )

    with tempfile.TemporaryDirectory(prefix="sample-news-", dir=fixture_dir.parent) as temp_name:
        temp_dir = Path(temp_name)
        for table, filename in manifest["files"].items():
            source_path = fixture_dir / filename
            target_path = temp_dir / filename
            if table == "stock_news":
                _write_json_atomic(target_path, frozen_rows)
            else:
                target_path.write_bytes(source_path.read_bytes())
        _write_json_atomic(temp_dir / "manifest.json", manifest)
        load_fixture(temp_dir, allow_draft=True)
        os.replace(temp_dir / manifest["files"]["stock_news"], fixture_dir / manifest["files"]["stock_news"])
        os.replace(temp_dir / "manifest.json", fixture_dir / "manifest.json")

    checkpoint_path.unlink(missing_ok=True)
    return {"rows": len(frozen_rows), "counts": counts}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument("--start", type=date.fromisoformat, default=DEFAULT_START)
    parser.add_argument("--end", type=date.fromisoformat, default=DEFAULT_END)
    parser.add_argument("--per-window", type=int, default=2, choices=range(1, 4))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = export_news(args.fixture_dir, args.start, args.end, per_window=args.per_window)
    print(f"Frozen YTD news: {result['rows']}")
    for ticker, count in sorted(result["counts"].items()):
        print(f"  {ticker}: {count}")
    print("DRAFT ONLY — redistribution review is still pending.")


if __name__ == "__main__":
    main()
