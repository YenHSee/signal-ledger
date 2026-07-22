"""Apply the additive report provenance migration without rewriting legacy rows."""

import sys
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))
load_dotenv(PACKAGE_ROOT / ".env")

from db.connection import get_connection, release_connection
from runtime_mode import assert_live_write_target


MIGRATION_PATH = PACKAGE_ROOT / "db" / "migrations" / "002_report_generation_metadata.sql"


def migrate() -> None:
    assert_live_write_target("migrate investment report provenance schema")
    connection = None
    cursor = None
    is_from_pool = False
    try:
        connection, is_from_pool = get_connection()
        cursor = connection.cursor()
        cursor.execute(MIGRATION_PATH.read_text(encoding="utf-8"))
        connection.commit()
    except Exception:
        if connection:
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        release_connection(connection, is_from_pool)


if __name__ == "__main__":
    migrate()
    print("Report provenance schema migration complete; legacy rows were not rewritten.")
