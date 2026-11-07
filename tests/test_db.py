import sqlite3

import pytest

from kisan import db


def test_seed_and_lookup():
    assert len(db.list_farmers()) == 8
    f = db.get_farmer("F001")
    assert f["crop"] == "Wheat"
    assert f["state"] == "Madhya Pradesh"


def test_unknown_farmer_is_none():
    assert db.get_farmer("F999") is None


def test_read_only_connection_cannot_write():
    with db._ro() as c:
        with pytest.raises(sqlite3.OperationalError):
            c.execute("DELETE FROM farmers")


def test_run_and_review_roundtrip():
    db.save_run("r1", "F001", "PENDING_HUMAN_REVIEW", '{"a": 1}')
    assert db.get_run("r1") == {"a": 1}
    db.save_review("r1", "approve", "tester", "ok")
    with db._ro() as c:
        row = c.execute("SELECT status FROM runs WHERE run_id='r1'").fetchone()
    assert row["status"] == "REVIEW_APPROVE"

