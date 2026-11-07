"""Pure tool logic shared by the MCP server, the ADK agent and the rule-based fallback."""
import random
import statistics
import time
from datetime import date
from typing import Optional

import httpx

from . import config, db
from .schemas import CreditMetrics, MandiSummary, PmfbyAssessment, WeatherSummary


class ToolError(Exception):
    pass


# ---- tiny TTL cache (replaces Redis for a single-server prototype) ----
_CACHE: dict = {}


def _cached(ttl: int):
    def deco(fn):
        def wrap(*args):
            key = (fn.__name__,) + args
            hit = _CACHE.get(key)
            now = time.time()
            if hit and now - hit[0] < ttl:
                return hit[1]
            val = fn(*args)
            _CACHE[key] = (now, val)
            return val
        wrap.__name__ = fn.__name__
        return wrap
    return deco


# ---- INDICATIVE reference data: verify against official sources before real use ----
AGMARK_NAME = {"wheat": "Wheat", "paddy": "Paddy(Dhan)(Common)", "cotton": "Cotton",
               "soybean": "Soyabean", "maize": "Maize", "mustard": "Mustard"}
INDICATIVE_MSP = {"wheat": 2585, "paddy": 2369, "cotton": 7710, "soybean": 5328, "maize": 2400, "mustard": 6200}
BASE_PRICE = {"wheat": 2650, "paddy": 2400, "cotton": 7300, "soybean": 4600, "maize": 2150, "mustard": 6000}
MANDI_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"


@_cached(1800)
def weather_summary(lat: float, lon: float) -> WeatherSummary:
    try:
        r = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "timezone": "Asia/Kolkata", "forecast_days": 7,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum"},
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()["daily"]
        rain = [float(x or 0) for x in d["precipitation_sum"]]
        tmax = [float(x) for x in d["temperature_2m_max"] if x is not None]
        tmin = [float(x) for x in d["temperature_2m_min"] if x is not None]
    except Exception as e:
        raise ToolError(f"weather service unavailable ({type(e).__name__})") from e

    notes, risk = [], "low"
    if max(rain) >= 50 or sum(rain) >= 100:
        risk, notes = "high", notes + ["Heavy rain expected: drainage, harvest and storage risk."]
    elif max(rain) >= 20 or sum(rain) >= 40:
        risk, notes = "medium", notes + ["Moderate rain expected: plan field work around dry days."]
    if tmax and max(tmax) >= 42:
        risk, notes = "high", notes + ["Extreme heat: irrigate in the evening."]
    elif tmax and max(tmax) >= 38 and risk == "low":
        risk, notes = "medium", notes + ["High temperatures expected."]
    if tmin and min(tmin) <= 4:
        risk, notes = ("high" if min(tmin) <= 2 else "medium"), notes + ["Frost risk at night."]
    return WeatherSummary(source="open-meteo", total_rain_mm=round(sum(rain), 1),
                          max_daily_rain_mm=round(max(rain), 1), rain_days=sum(1 for x in rain if x >= 2.5),
                          max_temp_c=round(max(tmax), 1) if tmax else 0.0,
                          min_temp_c=round(min(tmin), 1) if tmin else 0.0, risk_level=risk, notes=notes)


def _live_mandi(commodity: str, state: str) -> Optional[list]:
    if not config.DATA_GOV_API_KEY:
        return None
    try:
        r = httpx.get(
            f"https://api.data.gov.in/resource/{MANDI_RESOURCE}",
            params={"api-key": config.DATA_GOV_API_KEY, "format": "json", "limit": 100,
                    "filters[commodity]": commodity, "filters[state]": state},
            timeout=12,
        )
        r.raise_for_status()
        recs = r.json().get("records", [])
        out = []
        for x in recs:
            try:
                out.append((float(x["modal_price"]), str(x.get("market", ""))))
            except (KeyError, ValueError, TypeError):
                continue
        return out or None
    except Exception:
        return None


@_cached(900)
def mandi_summary(crop: str, state: str) -> MandiSummary:
    key = crop.strip().lower()
    if key not in AGMARK_NAME:
        raise ToolError(f"unsupported crop '{crop}'. Supported: {sorted(AGMARK_NAME)}")
    msp = float(INDICATIVE_MSP[key])
    live = _live_mandi(AGMARK_NAME[key], state)
    if live:
        price = statistics.median(p for p, _ in live)
        trend, src, n = None, "agmarknet_live", len({m for _, m in live})
        note = "Live modal price (Rs/quintal). No history in this feed, so no trend."
    else:
        rnd = random.Random(f"{key}-{date.today().isocalendar()[1]}")
        p, series = float(BASE_PRICE[key]), []
        for _ in range(14):
            p *= 1 + rnd.uniform(-0.015, 0.02)
            series.append(p)
        price = round(series[-1], 0)
        base = statistics.mean(series[:7])
        trend = round((statistics.mean(series[-3:]) - base) / base * 100, 1)
        src, n = "synthetic_fallback", 0
        note = "SYNTHETIC price series used (no live key/network). Do not use for real decisions."
    vs_msp = round((price - msp) / msp * 100, 1)
    if vs_msp < 0:
        signal = "below_msp"
    elif trend is not None and trend > 3:
        signal = "rising"
    elif trend is not None and trend < -3:
        signal = "falling"
    else:
        signal = "stable"
    return MandiSummary(source=src, commodity=AGMARK_NAME[key], current_modal_price=round(price, 0), msp=msp,
                        vs_msp_pct=vs_msp, trend_7d_pct=trend, markets_reporting=n, signal=signal, note=note)


def _farmer(fid: str) -> dict:
    f = db.get_farmer(fid)
    if not f:
        raise ToolError(f"farmer {fid} not found")
    return f


def kcc_metrics(farmer_id: str) -> CreditMetrics:
    """Indicative KCC maths: 9% base, 2% interest subvention, +3% prompt-repayment incentive => ~4% if repaid on time."""
    f = _farmer(farmer_id)
    limit, out = float(f["kcc_limit"] or 0), float(f["outstanding"] or 0)
    dtd = db.days_until(f["due_date"])
    overdue = bool(dtd is not None and dtd < 0 and out > 0)
    std, on_time = 9.0, 4.0
    eff = std if overdue else on_time
    since = -db.days_until(f["disbursed_date"]) if f["disbursed_date"] else 0
    saving = round(out * (std - on_time) / 100 * max(since, 0) / 365, 0)
    return CreditMetrics(
        farmer_id=farmer_id, kcc_limit=limit, outstanding=out, headroom=max(limit - out, 0),
        utilization_pct=round(out / limit * 100, 1) if limit else 0.0, due_date=f["due_date"], days_to_due=dtd,
        overdue=overdue, effective_rate_pct=eff, standard_rate_pct=std, interest_saving_inr=saving,
        note="Indicative rates; confirm with your bank branch.")


def pmfby_assessment(farmer_id: str) -> PmfbyAssessment:
    """Indicative PMFBY rules: 2% kharif / 1.5% rabi food+oilseeds, 5% commercial (cotton). Cut-offs 31 Jul / 31 Dec."""
    f = _farmer(farmer_id)
    sow = date.fromisoformat(f["sowing_date"])
    season, crop = f["season"], f["crop"].lower()
    deadline = date(sow.year, 7, 31) if season == "kharif" else date(sow.year, 12, 31)
    left = (deadline - date.today()).days
    rate = 5.0 if crop == "cotton" else (2.0 if season == "kharif" else 1.5)
    enrolled = bool(f["pmfby_enrolled"])
    if enrolled:
        action = "keep_policy_and_report_losses"
    elif left >= 0:
        action = "enroll_now"
    else:
        action = "enrollment_closed_check_bank_or_csc"
    notes = ["Report localized calamity losses within 72 hours via the crop insurance app/helpline/bank.",
             "Dates and rates are indicative; verify on pmfby.gov.in."]
    if f["has_crop_loan"] and not enrolled:
        notes.append("Loanee farmers are often auto-enrolled for notified crops unless they opted out; confirm with the bank.")
    return PmfbyAssessment(farmer_id=farmer_id, crop=f["crop"], season=season, eligible=crop in AGMARK_NAME,
                           enrolled=enrolled, premium_rate_pct=rate, enrollment_deadline=deadline.isoformat(),
                           deadline_days_left=left, action=action, notes=notes)