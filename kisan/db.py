"""SQLite access. Tool processes open the DB read-only (least privilege)."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS farmers(
 farmer_id TEXT PRIMARY KEY, name TEXT, state TEXT, district TEXT, lat REAL, lon REAL,
 crop TEXT, season TEXT, area_acres REAL, sowing_date TEXT, harvest_date TEXT,
 kcc_limit REAL, outstanding REAL, disbursed_date TEXT, due_date TEXT,
 pmfby_enrolled INTEGER, has_crop_loan INTEGER, language TEXT);
CREATE TABLE IF NOT EXISTS runs(
 run_id TEXT PRIMARY KEY, farmer_id TEXT, status TEXT, report_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS reviews(
 id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, decision TEXT, reviewer TEXT, note TEXT, created_at TEXT);
"""


@contextmanager
def _rw():
    c = sqlite3.connect(config.DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


@contextmanager
def _ro():
    if not config.DB_PATH.exists():
        raise FileNotFoundError("Database missing. Run: python -m kisan.cli seed")
    c = sqlite3.connect(f"file:{config.DB_PATH.as_posix()}?mode=ro", uri=True, timeout=15)
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()


def days_until(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    return (date.fromisoformat(iso) - date.today()).days


def get_farmer(farmer_id: str) -> Optional[dict]:
    with _ro() as c:
        r = c.execute("SELECT * FROM farmers WHERE farmer_id=?", (farmer_id,)).fetchone()
        return dict(r) if r else None


def list_farmers() -> list:
    with _ro() as c:
        rows = c.execute("SELECT farmer_id,name,state,district,crop,season FROM farmers ORDER BY farmer_id").fetchall()
        return [dict(r) for r in rows]


def save_run(run_id: str, farmer_id: str, status: str, report_json: str) -> None:
    with _rw() as c:
        c.execute("INSERT OR REPLACE INTO runs VALUES(?,?,?,?,?)",
                  (run_id, farmer_id, status, report_json, datetime.now(timezone.utc).isoformat()))


def get_run(run_id: str) -> Optional[dict]:
    with _ro() as c:
        r = c.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return json.loads(r["report_json"]) if r else None


def save_review(run_id: str, decision: str, reviewer: str, note: str) -> None:
    with _rw() as c:
        c.execute("INSERT INTO reviews(run_id,decision,reviewer,note,created_at) VALUES(?,?,?,?,?)",
                  (run_id, decision, reviewer[:60], note[:500], datetime.now(timezone.utc).isoformat()))
        c.execute("UPDATE runs SET status=? WHERE run_id=?", ("REVIEW_" + decision.upper(), run_id))


def seed() -> int:
    """Synthetic farmers. Dates are relative to today so demos stay meaningful (tuned for Oct-Nov)."""
    t = date.today()

    def d(n):
        return (t + timedelta(days=n)).isoformat()

    rows = [
        ("F001", "Ramesh Yadav", "Madhya Pradesh", "Sehore", 23.20, 77.08, "Wheat", "rabi", 3.5, d(-25), d(125), 200000, 145000, d(-25), d(340), 0, 1, "hi"),
        ("F002", "Sunita Devi", "Uttar Pradesh", "Lucknow", 26.85, 80.95, "Paddy", "kharif", 2.0, d(-120), d(12), 150000, 148000, d(-200), d(-10), 0, 1, "hi"),
        ("F003", "Gurpreet Singh", "Punjab", "Ludhiana", 30.90, 75.85, "Wheat", "rabi", 6.0, d(-20), d(130), 300000, 90000, d(-20), d(345), 1, 1, "pa"),
        ("F004", "Lakshmi Reddy", "Telangana", "Warangal", 17.97, 79.59, "Cotton", "kharif", 4.0, d(-125), d(10), 250000, 210000, d(-190), d(18), 1, 1, "te"),
        ("F005", "Mohan Patil", "Maharashtra", "Nashik", 20.00, 73.79, "Soybean", "kharif", 2.5, d(-118), d(5), 100000, 60000, d(-190), d(40), 0, 0, "mr"),
        ("F006", "Anita Kumari", "Bihar", "Patna", 25.59, 85.14, "Maize", "rabi", 1.5, d(-15), d(135), 80000, 0, None, None, 0, 0, "hi"),
        ("F007", "Bhagwan Das", "Rajasthan", "Alwar", 27.55, 76.63, "Mustard", "rabi", 3.0, d(-30), d(100), 120000, 100000, d(-30), d(335), 1, 1, "hi"),
        ("F008", "Karthik Raman", "Tamil Nadu", "Thanjavur", 10.79, 79.14, "Paddy", "rabi", 2.2, d(-20), d(110), 90000, 50000, d(-100), d(25), 0, 1, "ta"),
    ]
    with _rw() as c:
        c.executescript(SCHEMA)
        c.execute("DELETE FROM farmers")
        c.executemany("INSERT INTO farmers VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)