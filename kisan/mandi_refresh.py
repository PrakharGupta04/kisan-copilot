"""Refresh the on-disk mandi snapshot (the government server is slow and erratic): python -m kisan.mandi_refresh"""
import json
import time

import httpx

from . import config, db
from .core_tools import AGMARK_NAME, MANDI_RESOURCE


def fetch(commodity: str, state: str, timeout: float = 25.0) -> list:
    r = httpx.get(f"https://api.data.gov.in/resource/{MANDI_RESOURCE}",
                  params={"api-key": config.DATA_GOV_API_KEY, "format": "json", "limit": 50,
                          "filters[commodity]": commodity, "filters[state]": state},
                  headers={"User-Agent": "kisan-copilot/1.0", "Accept": "*/*"},
            timeout=httpx.Timeout(timeout, connect=10.0))
    r.raise_for_status()
    out = []
    for x in r.json().get("records", []):
        try:
            out.append([float(x["modal_price"]), str(x.get("market", ""))])
        except (KeyError, ValueError, TypeError):
            continue
    return out


def main() -> None:
    if not config.DATA_GOV_API_KEY:
        print("DATA_GOV_API_KEY not set")
        return
    snap = config.DATA_DIR / "mandi_snapshot.json"
    try:
        data = json.loads(snap.read_text())
    except Exception:
        data = {}
    pairs = sorted({(AGMARK_NAME[f["crop"].lower()], f["state"]) for f in db.list_farmers()
                    if f["crop"].lower() in AGMARK_NAME})
    for commodity, state in pairs:
        t = time.time()
        recs, err, tries = [], "", 0
        for _ in range(3):
            tries += 1
            try:
                recs = fetch(commodity, state)
                break
            except Exception as e:
                err = type(e).__name__
                time.sleep(3)
        if recs:
            data[f"{commodity}|{state}"] = {"ts": time.time(), "records": recs}
            snap.write_text(json.dumps(data))
        extra = "" if recs else f" (last error {err})"
        print(f"{commodity}|{state}: {len(recs)} records, {tries} tries, {time.time() - t:.0f}s{extra}")


if __name__ == "__main__":
    main()
