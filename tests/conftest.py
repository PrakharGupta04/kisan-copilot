"""Test safety rules: temp database, no network keys, no LLM keys. Runs BEFORE any kisan import."""
import os
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="kisan_test_")
os.environ["KISAN_DB"] = str(Path(_TMP) / "test.db")
os.environ["DATA_GOV_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["OFFLINE"] = "1"
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _seed_db():
    from kisan import db
    db.seed()
    yield


@pytest.fixture(autouse=True)
def _clear_cache():
    from kisan import core_tools as ct
    ct._CACHE.clear()
    yield

