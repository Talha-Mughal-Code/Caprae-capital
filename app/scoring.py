"""Rule-based acquisition-fit score (0-100) with a plain-English reason per signal."""
import re
from datetime import date

TRUE = {"yes", "y", "true", "1"}

def _num(v):
    try:
        return float(re.sub(r"[^\d.]", "", str(v or "")))
    except ValueError:
        return None

def _money(v):
    s = str(v or "").lower().replace(",", "")
    m = re.search(r"\d+(\.\d+)?", s)
    if not m:
        return None
    x = float(m.group())
    return x * 1e6 if "m" in s else x * 1e3 if "k" in s else x

def score_lead(r):
    pts, why = 0, []
    rev = _money(r.get("est_revenue"))
    if rev is None:
        why.append("Revenue unknown")
    elif 5e6 <= rev <= 25e6:
        pts += 25; why.append(f"Revenue ${rev/1e6:.1f}M is in the $5-25M target range")
    elif 2e6 <= rev < 5e6 or 25e6 < rev <= 40e6:
        pts += 12; why.append(f"Revenue ${rev/1e6:.1f}M is near the target range")
    else:
        why.append(f"Revenue ${rev/1e6:.1f}M is outside the target range")

    yr = _num(r.get("year_founded"))
    if yr:
        age = date.today().year - int(yr)
        if age >= 20: pts += 20; why.append(f"{age} years in business: likely nearing owner succession")
        elif age >= 10: pts += 12; why.append(f"{age} years in business: established")
        else: pts += 4; why.append(f"Only {age} years in business")

    if str(r.get("owner_operated", "")).strip().lower() in TRUE:
        pts += 20; why.append("Owner-operated: owner is the likely decision maker")
    else:
        why.append("Not owner-operated: harder to reach a seller")

    locs = _num(r.get("locations")) or 1
    if locs <= 1: pts += 10; why.append("Single location: simple to integrate")
    elif locs <= 3: pts += 5; why.append(f"{int(locs)} locations")
    else: why.append(f"{int(locs)} locations: complex, likely PE/roll-up interest already")

    rc, rt = _num(r.get("review_count")) or 0, _num(r.get("rating")) or 0
    if rc >= 40 and rt >= 4.0: pts += 15; why.append(f"{int(rc)} reviews at {rt}: healthy customer base")
    elif rc >= 15: pts += 8; why.append(f"{int(rc)} reviews: moderate traction")
    else: why.append("Few reviews: weak demand signal")

    web = str(r.get("website", "")).strip().lower()
    if not web: pts += 10; why.append("No website: low competition from other buyers")
    elif web.startswith("http://"): pts += 5; why.append("Website not on HTTPS: likely neglected")
    else: why.append("Modern website")

    tier = "A" if pts >= 70 else "B" if pts >= 50 else "C"
    return pts, tier, why
