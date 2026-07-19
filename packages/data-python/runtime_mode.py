import os

VALID_APP_MODES = {"live", "sample"}


class RuntimeSafetyError(RuntimeError):
    """Raised when a process could access the wrong runtime database."""


def get_app_mode() -> str:
    value = os.getenv("APP_MODE", "live").strip().lower()
    if value not in VALID_APP_MODES:
        expected = ", ".join(sorted(VALID_APP_MODES))
        raise RuntimeSafetyError(
            f"Invalid APP_MODE '{value}'. Expected one of: {expected}."
        )
    return value


def assert_live_read_source(operation: str) -> None:
    mode = get_app_mode()
    database = os.getenv("DB_NAME", "signal_ledger").strip().lower()
    if mode != "live" or database != "signal_ledger":
        raise RuntimeSafetyError(
            f"Refusing to {operation}: expected APP_MODE=live and "
            "DB_NAME=signal_ledger."
        )


def assert_live_write_target(operation: str) -> None:
    mode = get_app_mode()
    database = os.getenv("DB_NAME", "signal_ledger").strip().lower()
    if mode != "live":
        raise RuntimeSafetyError(
            f"Refusing to {operation}: APP_MODE must be 'live', got '{mode}'."
        )
    if database.endswith("_sample"):
        raise RuntimeSafetyError(
            f"Refusing to {operation}: live writers cannot target sample database '{database}'."
        )


def assert_sample_seed_target() -> None:
    mode = get_app_mode()
    database = os.getenv("DB_NAME", "").strip().lower()
    if mode != "sample" or database != "signal_ledger_sample":
        raise RuntimeSafetyError(
            "Refusing to seed sample data: expected APP_MODE=sample and "
            "DB_NAME=signal_ledger_sample."
        )
