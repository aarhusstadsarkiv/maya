import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[2]
TEST_SESSION_SECRET = "test-only-persistent-session-secret"
UNSET = object()
IMPORT_APP = "from maya.app import app"
CHECK_SECRET = """
from maya.app import app
from starlette.middleware.sessions import SessionMiddleware
import os
session = next(entry for entry in app.user_middleware if entry.cls is SessionMiddleware)
assert session.kwargs['secret_key'] == os.environ['EXPECTED_SESSION_SECRET']
"""


class SessionSecretTest(TestCase):
    def start_app(self, variables=None, site_secret=UNSET):
        with tempfile.TemporaryDirectory(prefix="maya-session-test-") as directory:
            env = os.environ.copy()
            for name in ("SECRET", "SESSION_SECRET", "TEST", "EXPECTED_SESSION_SECRET"):
                env.pop(name, None)
            env["BASE_DIR"] = directory
            env.update(variables or {})
            if site_secret is not UNSET:
                Path(directory, "settings.py").write_text(f"settings = {{'session_secret': {site_secret!r}}}\n")
            code = CHECK_SECRET if "EXPECTED_SESSION_SECRET" in env else IMPORT_APP
            return subprocess.run(
                [sys.executable, "-c", code],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )

    def test_missing_secret_prevents_startup(self):
        result = self.start_app()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("A valid session_secret is required", result.stderr)

    def test_invalid_secret_prevents_startup(self):
        for value in ("", " \t", "None", " None "):
            with self.subTest(value=value):
                result = self.start_app({"SESSION_SECRET": value})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("A valid session_secret is required", result.stderr)

    def test_configured_secret_is_used_by_middleware(self):
        result = self.start_app({"SESSION_SECRET": TEST_SESSION_SECRET, "EXPECTED_SESSION_SECRET": TEST_SESSION_SECRET})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_secret_is_ignored(self):
        result = self.start_app({"SECRET": TEST_SESSION_SECRET})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("A valid session_secret is required", result.stderr)

        result = self.start_app({"SESSION_SECRET": TEST_SESSION_SECRET, "SECRET": "None", "EXPECTED_SESSION_SECRET": TEST_SESSION_SECRET})
        self.assertEqual(result.returncode, 0, result.stderr)

        result = self.start_app({"SESSION_SECRET": "", "SECRET": TEST_SESSION_SECRET})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("A valid session_secret is required", result.stderr)

    def test_site_setting_is_used_and_validated(self):
        result = self.start_app(
            {"SESSION_SECRET": "None", "EXPECTED_SESSION_SECRET": TEST_SESSION_SECRET},
            site_secret=TEST_SESSION_SECRET,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        for value in (None, "", "None", 123):
            with self.subTest(value=value):
                result = self.start_app({"SESSION_SECRET": TEST_SESSION_SECRET}, site_secret=value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("A valid session_secret is required", result.stderr)
