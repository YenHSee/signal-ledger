import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from runtime_mode import (  # noqa: E402
    RuntimeSafetyError,
    assert_live_read_source,
    assert_live_write_target,
    assert_sample_seed_target,
    get_app_mode,
)


class RuntimeModeTests(unittest.TestCase):
    def test_live_is_the_default_mode(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_app_mode(), "live")

    def test_invalid_mode_is_rejected(self):
        with patch.dict(os.environ, {"APP_MODE": "preview"}, clear=True):
            with self.assertRaises(RuntimeSafetyError):
                get_app_mode()

    def test_live_reader_requires_exact_live_source(self):
        with patch.dict(
            os.environ,
            {"APP_MODE": "live", "DB_NAME": "signal_ledger"},
            clear=True,
        ):
            assert_live_read_source("export fixtures")

        invalid_environments = [
            {"APP_MODE": "sample", "DB_NAME": "signal_ledger_sample"},
            {"APP_MODE": "live", "DB_NAME": "signal_ledger_sample"},
            {"APP_MODE": "sample", "DB_NAME": "signal_ledger"},
        ]
        for environment in invalid_environments:
            with self.subTest(environment=environment):
                with patch.dict(os.environ, environment, clear=True):
                    with self.assertRaises(RuntimeSafetyError):
                        assert_live_read_source("export fixtures")

    def test_live_writer_accepts_live_database(self):
        with patch.dict(
            os.environ,
            {"APP_MODE": "live", "DB_NAME": "signal_ledger"},
            clear=True,
        ):
            assert_live_write_target("run test write")

    def test_live_writer_rejects_sample_mode_and_database(self):
        environments = [
            {"APP_MODE": "sample", "DB_NAME": "signal_ledger_sample"},
            {"APP_MODE": "live", "DB_NAME": "signal_ledger_sample"},
        ]
        for environment in environments:
            with self.subTest(environment=environment):
                with patch.dict(os.environ, environment, clear=True):
                    with self.assertRaises(RuntimeSafetyError):
                        assert_live_write_target("run test write")

    def test_sample_seed_requires_exact_sample_target(self):
        with patch.dict(
            os.environ,
            {"APP_MODE": "sample", "DB_NAME": "signal_ledger_sample"},
            clear=True,
        ):
            assert_sample_seed_target()


if __name__ == "__main__":
    unittest.main()
