"""Rule-based engine: used for OFFLINE mode, tests, and as graceful degradation if the LLM path fails."""
from . import core_tools as ct, db
from .schemas import FarmerMessage, FinalReport, Recommendation, RunState


def build_report(profile: dict, state: RunState, mode: str) -> FinalReport:
    fid = profile["farmer_id"]
    evidence, recs, his = [], [], []

    def safe(name, fn):
        try:
            r = fn()
            evidence.append({"tool": name, "result": r.model_dump_json()[:600]})
            return r
        except Exception as e:
            state.errors.append(f"{name}: {e}")
            return None

    w = safe("weather", lambda: ct.weather_summary(profile["lat"], profile["lon"]))
    m = safe("mandi", lambda: ct.mandi_summary(profile["crop"], profile["state"]))
    c = safe("credit", lambda: ct.kcc_metrics(fid))
    i = safe("insurance", lambda: ct.pmfby_assessment(fid))

    def add(p, title, detail, src, conf, hi):
        recs.append(Recommendation(priority=p, title=title, detail=detail, source_agents=src, confidence=conf))
        his.append(hi)

    if c and c.outstanding > 0:
        if c.overdue:
            add(1, "Repay overdue KCC dues now",
                f"Your KCC dues of Rs {c.outstanding:,.0f} are {abs(c.days_to_due)} days overdue and the interest benefit "
                "is lost. Visit your bank branch to repay or discuss restructuring.", ["credit"], 0.9,
                f"आपके KCC के Rs {c.outstanding:,.0f} {abs(c.days_to_due)} दिन से बकाया हैं। जल्द बैंक शाखा जाकर भुगतान करें।")
        elif c.days_to_due is not None and c.days_to_due <= 45:
            add(2, "Plan KCC repayment before the due date",
                f"Dues of Rs {c.outstanding:,.0f} fall due in {c.days_to_due} days. Repaying on time keeps interest near "
                f"{c.effective_rate_pct}% and saves about Rs {c.interest_saving_inr:,.0f}.", ["credit"], 0.85,
                f"KCC का Rs {c.outstanding:,.0f} {c.days_to_due} दिन में देय है। समय पर भुगतान से ब्याज कम रहेगा।")
    if i:
        if i.action == "enroll_now":
            add(1, "Enroll in PMFBY crop insurance",
                f"You are not enrolled. Premium is about {i.premium_rate_pct}% and the window closes in "
                f"{i.deadline_days_left} days ({i.enrollment_deadline}).", ["insurance"], 0.85,
                f"आपने फसल बीमा नहीं कराया है। {i.deadline_days_left} दिन में प्रीमियम (लगभग {i.premium_rate_pct}%) जमा कर बीमा कराएँ।")
        elif i.action == "enrollment_closed_check_bank_or_csc":
            add(3, "PMFBY window closed: confirm cover with your bank",
                "Enrollment is closed and no policy is recorded. Ask your bank/CSC whether you were auto-enrolled, "
                "and report any crop loss within 72 hours.", ["insurance"], 0.7,
                "बीमा की अंतिम तिथि निकल चुकी है। बैंक/CSC से पूछें कि क्या आप स्वतः नामांकित हैं।")
        else:
            add(4, "Keep your PMFBY cover active",
                "You are enrolled. Report any localized loss (hail, flood) within 72 hours.", ["insurance"], 0.8,
                "आपका फसल बीमा चालू है। नुकसान होने पर 72 घंटे में सूचना दें।")
    hd = db.days_until(profile.get("harvest_date"))
    if m and hd is not None and hd <= 60:
        if m.signal == "below_msp":
            add(2, "Avoid distress sale: price is below MSP",
                f"Mandi price Rs {m.current_modal_price:,.0f}/qtl is {abs(m.vs_msp_pct)}% below indicative MSP "
                f"(Rs {m.msp:,.0f}). Hold if you can store safely and check MSP procurement.", ["mandi"], 0.7,
                f"मंडी भाव Rs {m.current_modal_price:,.0f}/क्विंटल MSP से कम है। सुरक्षित भंडारण हो तो रुकें।")
        elif m.signal == "rising":
            add(3, "Prices rising: consider holding briefly",
                f"Price Rs {m.current_modal_price:,.0f}/qtl is up {m.trend_7d_pct}% this week. Hold a few days if storage is dry.",
                ["mandi"], 0.6, f"भाव बढ़ रहे हैं (Rs {m.current_modal_price:,.0f})। भंडारण सुरक्षित हो तो कुछ दिन रुकें।")
        elif m.signal == "falling":
            add(3, "Prices falling: plan to sell soon after harvest",
                f"Price Rs {m.current_modal_price:,.0f}/qtl is down {abs(m.trend_7d_pct)}% this week.", ["mandi"], 0.6,
                f"भाव गिर रहे हैं (Rs {m.current_modal_price:,.0f})। कटाई के बाद जल्द बेचने की योजना बनाएँ।")
        else:
            add(4, "Prices stable: sell at harvest or stagger sales",
                f"Price is steady near Rs {m.current_modal_price:,.0f}/qtl.", ["mandi"], 0.6,
                f"भाव स्थिर हैं (Rs {m.current_modal_price:,.0f})। कटाई पर या किस्तों में बेचें।")
    if w and w.risk_level != "low":
        add(2 if w.risk_level == "high" else 4, f"Weather alert ({w.risk_level} risk)",
            " ".join(w.notes) + f" Expected rain: {w.total_rain_mm} mm over 7 days.", ["weather"], 0.75,
            "अगले 7 दिनों में मौसम का जोखिम है। खेत की निकासी और फसल/भंडारण की सुरक्षा करें।")

    risks = [x for x in (
        "Weather data unavailable." if w is None else None,
        "Mandi data synthetic or unavailable." if (m is None or m.source != "agmarknet_live") else None,
        "Credit data unavailable." if c is None else None,
        "Insurance data unavailable." if i is None else None) if x]
    recs = recs or [Recommendation(priority=5, title="No urgent actions", detail="No urgent issues found.",
                                   source_agents=[], confidence=0.5)]
    top = sorted(zip(recs, his or [""]), key=lambda x: x[0].priority)[:2]
    msg = FarmerMessage(hindi=" ".join(h for _, h in top if h) or "अभी कोई ज़रूरी सलाह नहीं है।",
                        english=" ".join(r.title + "." for r, _ in top),
                        sms=(top[0][0].title if top else "No urgent actions")[:160])
    return FinalReport(run_id=state.run_id, farmer_id=fid, mode=mode,
                       summary=f"Rule-based advice for a {profile['crop']} farmer in {profile['district']}.",
                       recommendations=recs, risks=risks, overall_confidence=0.7,
                       agents_run=["weather", "mandi", "credit", "insurance"], message=msg, evidence=evidence)