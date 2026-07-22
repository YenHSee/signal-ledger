"""Load a versioned frozen fixture into the dedicated sample database."""

import argparse
import copy
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))


from runtime_mode import assert_sample_seed_target


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_DIR = REPO_ROOT / "sample-data" / "v1"
SCHEMA_PATH = REPO_ROOT / "sample-data" / "schema.sql"
TABLE_ORDER = (
    "company_overview",
    "daily_prices",
    "stock_news",
    "investment_reports",
)
TABLE_SPECS = {
    "company_overview": {
        "required": {"symbol"},
        "conflict": ("symbol",),
        "allowed": {
            "symbol", "asset_type", "name", "description", "cik", "exchange",
            "currency", "country", "sector", "industry", "address",
            "official_site", "fiscal_year_end", "latest_quarter",
            "market_capitalization", "ebitda", "pe_ratio", "peg_ratio",
            "book_value", "dividend_per_share", "dividend_yield", "eps",
            "revenue_per_share_ttm", "profit_margin", "operating_margin_ttm",
            "return_on_assets_ttm", "return_on_equity_ttm", "revenue_ttm",
            "gross_profit_ttm", "diluted_eps_ttm",
            "quarterly_earnings_growth_yoy", "quarterly_revenue_growth_yoy",
            "analyst_target_price", "analyst_rating_strong_buy",
            "analyst_rating_buy", "analyst_rating_hold", "analyst_rating_sell",
            "analyst_rating_strong_sell", "trailing_pe", "forward_pe",
            "price_to_sales_ratio_ttm", "price_to_book_ratio", "ev_to_revenue",
            "ev_to_ebitda", "beta", "week_52_high", "week_52_low",
            "day_50_moving_average", "day_200_moving_average",
            "shares_outstanding", "shares_float", "percent_insiders",
            "percent_institutions", "dividend_date", "ex_dividend_date",
            "is_sp500", "last_updated", "current_price", "price_as_of",
        },
    },
    "daily_prices": {
        "required": {"symbol", "trade_date"},
        "conflict": ("symbol", "trade_date"),
        "allowed": {
            "symbol", "trade_date", "open_price", "high_price", "low_price",
            "close_price", "adjusted_close", "volume",
        },
    },
    "stock_news": {
        "required": {"finnhub_id", "symbol", "trade_date", "datetime", "headline"},
        "conflict": ("finnhub_id", "symbol"),
        "allowed": {
            "finnhub_id", "symbol", "trade_date", "datetime", "headline",
            "summary", "source", "url", "fetched_at",
        },
    },
    "investment_reports": {
        "required": {
            "report_schema_version", "ticker", "analysis_as_of", "generated_at",
            "generation_mode", "model_tier", "model_provider", "model_name",
            "prompt_version", "conclusion", "agent_outputs", "generation_metadata",
        },
        "conflict": (
            "ticker", "analysis_as_of", "model_provider", "model_name", "prompt_version",
        ),
        "allowed": {
            "report_schema_version", "ticker", "analysis_as_of", "generation_mode",
            "model_tier", "model_provider", "model_name", "prompt_version",
            "conclusion", "conviction_level",
            "target_price", "upside_downside_pct", "risk_level", "reasoning",
            "full_report", "raw_financial_data", "generated_at", "created_at",
            "agent_outputs", "generation_metadata",
        },
    },
}


class DatasetValidationError(ValueError):
    """Raised before a connection is opened when a fixture is unsafe or incomplete."""


REPORT_REQUIRED_FIELDS = {
    "report_schema_version", "ticker", "analysis_as_of", "generation_mode",
    "model_tier", "model_provider", "model_name", "prompt_version",
    "conclusion", "conviction_level", "target_price",
    "upside_downside_pct", "risk_level", "reasoning", "full_report",
    "raw_financial_data", "agent_outputs", "generation_metadata", "generated_at",
}
REPORT_SNAPSHOT_SECTIONS = {
    "company_identity",
    "profitability_and_scale",
    "valuation_and_growth",
    "smart_money_consensus",
    "technical_and_momentum",
}
REPORT_MARKDOWN_SECTIONS = (
    "executive summary",
    "business",
    "financial",
    "valuation",
    "bull",
    "base",
    "bear",
    "risk",
    "data limitations",
)
REPORT_ANALYSIS_AS_OF_PATTERN = re.compile(
    r"analysis\s+as\s+of\s*:\s*(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
PERCENT_PATTERN = re.compile(r"^([+-]?\d+(?:\.\d+)?)%$")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DatasetValidationError(f"Cannot read valid JSON from {path}: {error}") from error


def _validate_iso_date(value: Any, field: str, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str):
        raise DatasetValidationError(f"{field} must be an ISO date string.")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise DatasetValidationError(f"{field} must use YYYY-MM-DD.") from error


def _parse_report_datetime(value: Any, row_number: int, field: str = "generated_at") -> datetime:
    if not isinstance(value, str):
        raise DatasetValidationError(
            f"investment_reports row {row_number} {field} must be an ISO datetime."
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise DatasetValidationError(
            f"investment_reports row {row_number} {field} must be an ISO datetime."
        ) from error
    if parsed.utcoffset() is None:
        raise DatasetValidationError(
            f"investment_reports row {row_number} {field} must include a timezone."
        )
    return parsed


def _number(value: Any, field: str, row_number: int) -> float:
    if isinstance(value, bool):
        raise DatasetValidationError(
            f"investment_reports row {row_number} {field} must be a positive number."
        )
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise DatasetValidationError(
            f"investment_reports row {row_number} {field} must be a positive number."
        ) from error
    if number <= 0:
        raise DatasetValidationError(
            f"investment_reports row {row_number} {field} must be a positive number."
        )
    return number


def _validate_investment_reports(manifest: dict, data: dict[str, list[dict]]) -> None:
    reports = data["investment_reports"]
    if not reports:
        return

    coverage = manifest["targetCoverage"]
    if not isinstance(coverage, dict) or not {"priceStart", "priceEnd"} <= coverage.keys():
        raise DatasetValidationError(
            "A fixture with investment reports must define priceStart and priceEnd."
        )
    if manifest["dataAsOf"] is None:
        raise DatasetValidationError(
            "A fixture with investment reports must define dataAsOf."
        )
    try:
        price_start = date.fromisoformat(coverage["priceStart"])
        price_end = date.fromisoformat(coverage["priceEnd"])
        data_as_of = date.fromisoformat(manifest["dataAsOf"])
    except (TypeError, ValueError) as error:
        raise DatasetValidationError(
            "Report priceStart, priceEnd, and dataAsOf must be ISO dates."
        ) from error
    prices_by_ticker: dict[str, list[tuple[date, float]]] = {}
    for row in data["daily_prices"]:
        if row.get("close_price") is None:
            continue
        prices_by_ticker.setdefault(row["symbol"], []).append(
            (date.fromisoformat(row["trade_date"]), float(row["close_price"]))
        )
    news_headlines = {
        (row["symbol"], row["headline"].strip())
        for row in data["stock_news"]
        if isinstance(row.get("headline"), str)
    }

    for row_number, row in enumerate(reports, start=1):
        missing = REPORT_REQUIRED_FIELDS - row.keys()
        if missing:
            raise DatasetValidationError(
                f"investment_reports row {row_number} is missing complete report fields: "
                f"{', '.join(sorted(missing))}."
            )
        for field in (
            "ticker", "model_tier", "conclusion", "conviction_level", "risk_level",
            "reasoning", "full_report", "upside_downside_pct",
        ):
            if not isinstance(row[field], str) or not row[field].strip():
                raise DatasetValidationError(
                    f"investment_reports row {row_number} {field} must be non-empty."
                )

        _parse_report_datetime(row["generated_at"], row_number)
        analysis_as_of = _parse_report_datetime(
            row["analysis_as_of"], row_number, "analysis_as_of"
        )
        analysis_date = analysis_as_of.date()
        if not price_start <= analysis_date <= price_end or analysis_date > data_as_of:
            raise DatasetValidationError(
                f"investment_reports row {row_number} analysis_as_of is outside the frozen range."
            )

        if row["report_schema_version"] != 2:
            raise DatasetValidationError(
                f"investment_reports row {row_number} report_schema_version must be 2."
            )
        if row["generation_mode"] != "historical_backfill":
            raise DatasetValidationError(
                f"investment_reports row {row_number} must use historical_backfill mode."
            )

        if row["model_tier"] not in {"L", "N"}:
            raise DatasetValidationError(
                f"investment_reports row {row_number} model_tier must be L or N."
            )
        if row["conclusion"].upper() not in {"BUY", "HOLD", "SELL"}:
            raise DatasetValidationError(
                f"investment_reports row {row_number} conclusion must be BUY, HOLD, or SELL."
            )
        for field in ("conviction_level", "risk_level"):
            if row[field].lower() not in {"high", "medium", "low"}:
                raise DatasetValidationError(
                    f"investment_reports row {row_number} {field} must be High, Medium, or Low."
                )

        snapshot = row["raw_financial_data"]
        if not isinstance(snapshot, dict) or not REPORT_SNAPSHOT_SECTIONS <= snapshot.keys():
            raise DatasetValidationError(
                f"investment_reports row {row_number} has an incomplete financial snapshot."
            )
        if any(not isinstance(snapshot[section], dict) for section in REPORT_SNAPSHOT_SECTIONS):
            raise DatasetValidationError(
                f"investment_reports row {row_number} has an invalid financial snapshot."
            )
        if snapshot["company_identity"].get("symbol") != row["ticker"]:
            raise DatasetValidationError(
                f"investment_reports row {row_number} snapshot ticker does not match."
            )
        for item in snapshot.get("recent_sec_filings", []):
            filed_at = item.get("date") if isinstance(item, dict) else None
            if filed_at and date.fromisoformat(filed_at) > analysis_date:
                raise DatasetValidationError(
                    f"investment_reports row {row_number} contains a future SEC filing."
                )
        for item in snapshot.get("recent_catalysts", []):
            news_date = item.get("date") if isinstance(item, dict) else None
            if news_date and date.fromisoformat(news_date) > analysis_date:
                raise DatasetValidationError(
                    f"investment_reports row {row_number} contains future news."
                )

        target_price = _number(row["target_price"], "target_price", row_number)
        snapshot_price = _number(
            snapshot["smart_money_consensus"].get("current_price"),
            "snapshot current_price",
            row_number,
        )
        recent_prices = [
            close
            for trade_date, close in prices_by_ticker.get(row["ticker"], [])
            if trade_date <= analysis_date and (analysis_date - trade_date).days <= 7
        ]
        if not any(abs(close - snapshot_price) <= 0.01 for close in recent_prices):
            raise DatasetValidationError(
                f"investment_reports row {row_number} snapshot price does not match a frozen "
                "close from the preceding seven days."
            )

        percent_match = PERCENT_PATTERN.fullmatch(row["upside_downside_pct"].strip())
        if not percent_match:
            raise DatasetValidationError(
                f"investment_reports row {row_number} upside_downside_pct is invalid."
            )
        stated_percent = float(percent_match.group(1))
        computed_percent = (target_price / snapshot_price - 1) * 100
        if abs(stated_percent - computed_percent) > 0.5:
            raise DatasetValidationError(
                f"investment_reports row {row_number} upside_downside_pct does not match its "
                "target and snapshot prices."
            )

        report_text = row["full_report"].casefold()
        missing_sections = [
            section for section in REPORT_MARKDOWN_SECTIONS if section not in report_text
        ]
        if missing_sections:
            raise DatasetValidationError(
                f"investment_reports row {row_number} is missing report sections: "
                f"{', '.join(missing_sections)}."
            )
        embedded_dates = REPORT_ANALYSIS_AS_OF_PATTERN.findall(row["full_report"])
        if any(date.fromisoformat(value) != analysis_date for value in embedded_dates):
            raise DatasetValidationError(
                f"investment_reports row {row_number} contains a conflicting analysis date."
            )

        outputs = row["agent_outputs"]
        metadata = row["generation_metadata"]
        if not isinstance(outputs, list) or not outputs:
            raise DatasetValidationError(
                f"investment_reports row {row_number} agent_outputs must be a non-empty array."
            )
        if not isinstance(metadata, dict) or metadata.get("schema_version") != 2:
            raise DatasetValidationError(
                f"investment_reports row {row_number} has invalid generation_metadata."
            )
        if metadata.get("provenance_status") != "complete":
            raise DatasetValidationError(
                f"investment_reports row {row_number} provenance must be complete."
            )
        runs = metadata.get("agent_runs")
        if not isinstance(runs, list) or not runs:
            raise DatasetValidationError(
                f"investment_reports row {row_number} agent_runs must be a non-empty array."
            )
        final_run_id = metadata.get("final_run_id")
        final_runs = [run for run in runs if run.get("run_id") == final_run_id]
        final_outputs = [output for output in outputs if output.get("run_id") == final_run_id]
        if len(final_runs) != 1 or len(final_outputs) != 1:
            raise DatasetValidationError(
                f"investment_reports row {row_number} must identify exactly one final run."
            )
        final_run = final_runs[0]
        final_output = final_outputs[0].get("output") or {}
        if final_output.get("stance", "").upper() != row["conclusion"].upper():
            raise DatasetValidationError(
                f"investment_reports row {row_number} final output conflicts with conclusion."
            )
        if (
            final_run.get("provider") != row["model_provider"]
            or final_run.get("response_model") != row["model_name"]
            or final_run.get("prompt_version") != row["prompt_version"]
        ):
            raise DatasetValidationError(
                f"investment_reports row {row_number} final model columns conflict with final run."
            )
        required_run_fields = {
            "run_id", "agent_key", "agent_version", "sequence", "depends_on",
            "provider", "tier", "requested_model", "response_model", "prompt_version",
            "temperature", "response_format", "finish_reason", "usage",
        }
        for run in runs:
            if not required_run_fields <= run.keys():
                raise DatasetValidationError(
                    f"investment_reports row {row_number} has incomplete agent run metadata."
                )
            usage = run["usage"]
            if not isinstance(usage, dict) or any(
                not isinstance(usage.get(key), int) or usage[key] < 0
                for key in ("input_tokens", "output_tokens", "total_tokens")
            ):
                raise DatasetValidationError(
                    f"investment_reports row {row_number} has incomplete token usage."
                )
            if usage["total_tokens"] != usage["input_tokens"] + usage["output_tokens"]:
                raise DatasetValidationError(
                    f"investment_reports row {row_number} has inconsistent token usage."
                )
            if not run.get("response_model") or not run.get("finish_reason"):
                raise DatasetValidationError(
                    f"investment_reports row {row_number} lacks actual provider response metadata."
                )
            if run.get("provider") == "ollama" and not run.get("local_model_digest"):
                raise DatasetValidationError(
                    f"investment_reports row {row_number} lacks an Ollama model digest."
                )
        aggregate = metadata.get("aggregate_usage") or {}
        expected_usage = {
            key: sum(run["usage"][key] for run in runs)
            for key in ("input_tokens", "output_tokens", "total_tokens")
        }
        if aggregate.get("calls") != len(runs) or any(
            aggregate.get(key) != value for key, value in expected_usage.items()
        ):
            raise DatasetValidationError(
                f"investment_reports row {row_number} aggregate usage does not match agent runs."
            )

        catalysts = snapshot.get("recent_catalysts", [])
        if not isinstance(catalysts, list):
            raise DatasetValidationError(
                f"investment_reports row {row_number} recent_catalysts must be an array."
            )
        for catalyst in catalysts:
            headline = catalyst.get("headline") if isinstance(catalyst, dict) else None
            if not isinstance(headline, str) or (row["ticker"], headline.strip()) not in news_headlines:
                raise DatasetValidationError(
                    f"investment_reports row {row_number} references news absent from the "
                    "frozen fixture."
                )
        if not catalysts:
            limitation_text = report_text.replace("-", " ")
            acknowledges_missing_news = "news" in limitation_text and any(
                phrase in limitation_text
                for phrase in ("no frozen", "no news", "not available", "unavailable")
            )
            if not acknowledges_missing_news:
                raise DatasetValidationError(
                    f"investment_reports row {row_number} must disclose that frozen news is "
                    "unavailable."
                )


def load_fixture(fixture_dir: Path, allow_draft: bool = False) -> tuple[dict, dict]:
    fixture_dir = fixture_dir.resolve()
    manifest = _read_json(fixture_dir / "manifest.json")
    if not isinstance(manifest, dict):
        raise DatasetValidationError("manifest.json must contain an object.")

    required_manifest_keys = {
        "schemaVersion", "datasetVersion", "status", "createdAt", "dataAsOf",
        "tickers", "files", "expectedRows", "targetCoverage",
    }
    missing = required_manifest_keys - manifest.keys()
    if missing:
        raise DatasetValidationError(f"Manifest is missing: {', '.join(sorted(missing))}.")
    if manifest["schemaVersion"] != 1:
        raise DatasetValidationError("Only sample schemaVersion 1 is supported.")
    if manifest["status"] not in {"draft", "ready"}:
        raise DatasetValidationError("Manifest status must be draft or ready.")
    if manifest["status"] == "draft" and not allow_draft:
        raise DatasetValidationError(
            "Refusing to seed a draft dataset. Finish it or pass --allow-draft locally."
        )
    if not isinstance(manifest["datasetVersion"], str) or not manifest["datasetVersion"].strip():
        raise DatasetValidationError("datasetVersion must be a non-empty string.")
    _validate_iso_date(manifest["createdAt"], "createdAt")
    _validate_iso_date(manifest["dataAsOf"], "dataAsOf", nullable=True)

    tickers = manifest["tickers"]
    if not isinstance(tickers, list) or not tickers:
        raise DatasetValidationError("tickers must be a non-empty array.")
    if len(tickers) != len(set(tickers)):
        raise DatasetValidationError("tickers must not contain duplicates.")
    if any(not isinstance(ticker, str) or ticker != ticker.upper() for ticker in tickers):
        raise DatasetValidationError("tickers must be uppercase strings.")
    ticker_set = set(tickers)

    files = manifest["files"]
    expected_rows = manifest["expectedRows"]
    if not isinstance(files, dict) or set(files) != set(TABLE_ORDER):
        raise DatasetValidationError("files must define exactly the four sample tables.")
    if not isinstance(expected_rows, dict) or set(expected_rows) != set(TABLE_ORDER):
        raise DatasetValidationError("expectedRows must define exactly the four sample tables.")

    data = {}
    for table in TABLE_ORDER:
        filename = files[table]
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise DatasetValidationError(f"Unsafe fixture filename for {table}.")
        rows = _read_json(fixture_dir / filename)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise DatasetValidationError(f"{filename} must contain an array of objects.")
        if expected_rows[table] != len(rows):
            raise DatasetValidationError(
                f"{table} expected {expected_rows[table]} rows but contains {len(rows)}."
            )

        spec = TABLE_SPECS[table]
        ticker_key = "ticker" if table == "investment_reports" else "symbol"
        for row_number, row in enumerate(rows, start=1):
            unknown = set(row) - spec["allowed"]
            missing_row_keys = spec["required"] - row.keys()
            if unknown or missing_row_keys:
                raise DatasetValidationError(
                    f"Invalid {table} row {row_number}; unknown={sorted(unknown)}, "
                    f"missing={sorted(missing_row_keys)}."
                )
            if row[ticker_key] not in ticker_set:
                raise DatasetValidationError(
                    f"{table} row {row_number} references ticker outside the manifest."
                )
        data[table] = rows

    _validate_investment_reports(manifest, data)

    if manifest["status"] == "ready":
        if manifest["dataAsOf"] is None:
            raise DatasetValidationError("A ready dataset must define dataAsOf.")
        if len(tickers) != 10:
            raise DatasetValidationError("The v1 ready dataset must contain exactly 10 tickers.")
        if expected_rows["company_overview"] != len(tickers):
            raise DatasetValidationError("A ready dataset needs one company overview per ticker.")

    return manifest, data


def _upsert_rows(cursor, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    from psycopg2 import sql
    from psycopg2.extras import Json, execute_values

    spec = TABLE_SPECS[table]
    columns = sorted(set().union(*(row.keys() for row in rows)))
    values = [
        [
            Json(value) if isinstance(value, (dict, list)) else value
            for column in columns
            for value in [row.get(column)]
        ]
        for row in rows
    ]
    update_columns = [column for column in columns if column not in spec["conflict"]]

    statement = sql.SQL("INSERT INTO {table} ({columns}) VALUES %s ON CONFLICT ({conflict}) ").format(
        table=sql.Identifier(table),
        columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
        conflict=sql.SQL(", ").join(map(sql.Identifier, spec["conflict"])),
    )
    if update_columns:
        statement += sql.SQL("DO UPDATE SET {updates}").format(
            updates=sql.SQL(", ").join(
                sql.SQL("{column} = EXCLUDED.{column}").format(column=sql.Identifier(column))
                for column in update_columns
            )
        )
    else:
        statement += sql.SQL("DO NOTHING")
    execute_values(cursor, statement.as_string(cursor), values)


def _apply_reports_preview(
    manifest: dict,
    data: dict,
    reports_path: Path,
) -> tuple[dict, dict]:
    reports = _read_json(reports_path.resolve())
    if not isinstance(reports, list) or any(not isinstance(row, dict) for row in reports):
        raise DatasetValidationError("Reports preview must contain an array of objects.")
    spec = TABLE_SPECS["investment_reports"]
    ticker_set = set(manifest["tickers"])
    for row_number, row in enumerate(reports, start=1):
        unknown = set(row) - spec["allowed"]
        missing = spec["required"] - row.keys()
        if unknown or missing:
            raise DatasetValidationError(
                f"Invalid preview report row {row_number}; unknown={sorted(unknown)}, "
                f"missing={sorted(missing)}."
            )
        if row["ticker"] not in ticker_set:
            raise DatasetValidationError(
                f"Preview report row {row_number} references ticker outside the manifest."
            )
    preview_manifest = copy.deepcopy(manifest)
    preview_data = {**data, "investment_reports": reports}
    preview_manifest["expectedRows"]["investment_reports"] = len(reports)
    preview_manifest["datasetVersion"] = f"{manifest['datasetVersion']}-reports-preview"
    preview_manifest["status"] = "draft"
    _validate_investment_reports(preview_manifest, preview_data)
    return preview_manifest, preview_data


def seed(
    fixture_dir: Path,
    allow_draft: bool = False,
    reports_preview: Path | None = None,
) -> dict:
    import psycopg2
    from config import config
    from psycopg2 import sql

    assert_sample_seed_target()
    manifest, data = load_fixture(fixture_dir, allow_draft=allow_draft)
    if reports_preview:
        manifest, data = _apply_reports_preview(manifest, data, reports_preview)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    connection = psycopg2.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
    )
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(schema_sql)
                cursor.execute(
                    "TRUNCATE investment_reports, stock_news, daily_prices, "
                    "company_overview RESTART IDENTITY;"
                )
                for table in TABLE_ORDER:
                    _upsert_rows(cursor, table, data[table])
                cursor.execute(
                    """
                    INSERT INTO sample_dataset_metadata (
                        singleton_id, schema_version, dataset_version, dataset_status,
                        data_as_of, ticker_count, seeded_at
                    ) VALUES (1, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (singleton_id) DO UPDATE SET
                        schema_version = EXCLUDED.schema_version,
                        dataset_version = EXCLUDED.dataset_version,
                        dataset_status = EXCLUDED.dataset_status,
                        data_as_of = EXCLUDED.data_as_of,
                        ticker_count = EXCLUDED.ticker_count,
                        seeded_at = CURRENT_TIMESTAMP;
                    """,
                    (
                        manifest["schemaVersion"],
                        manifest["datasetVersion"],
                        manifest["status"],
                        manifest["dataAsOf"],
                        len(manifest["tickers"]),
                    ),
                )
                for table in TABLE_ORDER:
                    cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
                    actual = cursor.fetchone()[0]
                    expected = manifest["expectedRows"][table]
                    if actual != expected:
                        raise RuntimeError(f"Post-seed count mismatch for {table}: {actual} != {expected}")
    finally:
        connection.close()
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Allow a local draft fixture; never use this in the published demo.",
    )
    parser.add_argument(
        "--reports-preview",
        type=Path,
        help="Temporarily seed validated staged reports without modifying the fixture.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = seed(
        args.fixture_dir,
        allow_draft=args.allow_draft,
        reports_preview=args.reports_preview,
    )
    print(f"Dataset: {manifest['datasetVersion']} ({manifest['status']})")
    print(f"Tickers declared: {len(manifest['tickers'])}")
    for table in TABLE_ORDER:
        print(f"{table} inserted: {manifest['expectedRows'][table]}")
    if manifest["status"] == "draft":
        print("DRAFT ONLY — this is not yet a complete demo dataset.")


if __name__ == "__main__":
    main()
