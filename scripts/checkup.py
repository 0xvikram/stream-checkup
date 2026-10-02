"""The check-up rules. Pure functions, no network or file access.

Two jobs:
  1. Decide which streams to check first, and say why in plain words.
  2. Spot records that cannot be right.
"""
import re
from collections import Counter, defaultdict
from datetime import date

HEAVY_RAIN_MM = 20.0
HOT_DAY_C = 30.0
HEATWAVE_MIN_DAYS = 3

LEVELS = {"never": "Never checked", "first": "Check first", "soon": "Check soon", "wait": "Can wait"}
FIRST_FROM, SOON_FROM = 6, 3  # points out of 8

# Ranges no real stream can leave. Wide on purpose: a value outside these is an
# error in the record, not an unusual stream. (code -> (low, high, plain name))
POSSIBLE = {
    "ph": (0, 14, "pH (acidity)"),
    "703421000": (-5, 45, "water temperature in °C"),
    "waterTemperature": (-5, 45, "water temperature in °C"),
    "dissolved-oxygen": (0, 25, "dissolved oxygen in mg/L"),
    "electrical-conductivity": (0, 100_000, "electrical conductivity in µS/cm"),
    "chloride": (0, 25_000, "chloride in mg/L"),
    "sodium": (0, 15_000, "sodium in mg/L"),
    "calcium": (0, 2_000, "calcium in mg/L"),
    "magnesium": (0, 2_000, "magnesium in mg/L"),
    "sulphate": (0, 5_000, "sulphate in mg/L"),
    "nitrate": (0, 1_000, "nitrate in mg/L"),
}

# Names that are plainly try-outs, taken from what the public list holds today.
TEST_NAME = re.compile(r"test|^random$|^this site$|^x1$|^fgdgh$", re.I)


def years_between(start, end):
    return (end - start).days / 365.25


def weather_since(rows, start, heavy_mm=HEAVY_RAIN_MM, hot_c=HOT_DAY_C):
    """Summarise daily weather rows ({d, tmax, rain}) from `start` (ISO date) onward."""
    rows = [r for r in rows if r["d"] >= start]
    if not rows:
        return None
    heatwaves, run = 0, 0
    for r in rows:
        if (r["tmax"] or -99) >= hot_c:
            run += 1
            if run == HEATWAVE_MIN_DAYS:
                heatwaves += 1
        else:
            run = 0
    wettest = max(rows, key=lambda r: r["rain"] or 0)
    hottest = max(rows, key=lambda r: r["tmax"] or -99)
    return {
        "from": rows[0]["d"],
        "to": rows[-1]["d"],
        "heavyRainDays": sum(1 for r in rows if (r["rain"] or 0) >= heavy_mm),
        "hotDays": sum(1 for r in rows if (r["tmax"] or -99) >= hot_c),
        "heatwaves": heatwaves,
        "wettestDay": {"date": wettest["d"], "mm": round(wettest["rain"] or 0, 1)},
        "hottestDay": {"date": hottest["d"], "c": round(hottest["tmax"], 1)},
    }


def monthly(rows, start):
    """Rain total and heavy-rain days per month, for the small chart on each card."""
    months = defaultdict(lambda: {"rain": 0.0, "heavy": 0})
    for r in rows:
        if r["d"] < start:
            continue
        m = months[r["d"][:7]]
        m["rain"] += r["rain"] or 0
        m["heavy"] += 1 if (r["rain"] or 0) >= HEAVY_RAIN_MM else 0
    return [{"m": k, "rain": round(v["rain"], 1), "heavy": v["heavy"]} for k, v in sorted(months.items())]


def thirds(values):
    """Return a function mapping a value to 0, 1 or 2: lower, middle or upper third."""
    ordered = sorted(values)
    if not ordered:
        return lambda v: 0
    lo = ordered[len(ordered) // 3]
    hi = ordered[(2 * len(ordered)) // 3]
    if lo == hi:  # too many ties to split three ways
        return lambda v: 0 if v < lo else (2 if v > hi else 1)
    return lambda v: 0 if v < lo else (1 if v < hi else 2)


def level_for(points, has_lab):
    if not has_lab:
        return "never"
    if points >= FIRST_FROM:
        return "first"
    return "soon" if points >= SOON_FROM else "wait"


WORD = ["low", "medium", "high"]


def worst_part(lab):
    parts = {
        "germs that can make people ill": lab["germs"],
        "signs of sewage": lab["sewage"],
        "bacteria that resist antibiotics": lab["resistant"],
    }
    return max(parts, key=parts.get)


def score_streams(streams):
    """Add `factors`, `points`, `level` and `rank` to each stream, in place.

    Each of four facts is placed in the lower, middle or upper third of all
    streams (0, 1 or 2 points). Nothing is predicted: every input is a record.
    """
    with_lab = [s for s in streams if s["lab"]]
    third = {
        "lab": thirds([s["lab"]["overall"] for s in with_lab]),
        "rain": thirds([s["since"]["heavyRainDays"] for s in streams if s["since"]]),
        "heat": thirds([s["since"]["hotDays"] for s in streams if s["since"]]),
        # closer to a sewage works scores higher, so rank on the negative distance
        "sewage": thirds([-s["near"]["sewageM"] for s in streams if s["near"]]),
    }
    for s in streams:
        factors = []
        if s["lab"]:
            p = third["lab"](s["lab"]["overall"])
            factors.append({
                "key": "lab", "points": p, "title": "Last lab result",
                "text": f"Health risk was {WORD[p]} compared with the other streams. "
                        f"The biggest concern was {worst_part(s['lab'])}.",
            })
        if s["since"]:
            w = s["since"]
            p = third["rain"](w["heavyRainDays"])
            factors.append({
                "key": "rain", "points": p, "title": "Heavy rain since then",
                "text": f"{w['heavyRainDays']} days of heavy rain ({WORD[p]} compared with the other streams). "
                        "Heavy rain can wash sewage and street dirt into a stream.",
            })
            p = third["heat"](w["hotDays"])
            factors.append({
                "key": "heat", "points": p, "title": "Hot days since then",
                "text": f"{w['hotDays']} days at 30 °C or more ({WORD[p]} compared with the other streams). "
                        "Warm water holds less oxygen and grows more algae.",
            })
        if s["near"]:
            p = third["sewage"](-s["near"]["sewageM"])
            where = ["far", "a medium distance", "close"][p]
            factors.append({
                "key": "sewage", "points": p, "title": "Sewage works nearby",
                "text": f"The nearest sewage works is {format_distance(s['near']['sewageM'])} away, "
                        f"which is {where} compared with the other streams.",
            })
        s["factors"] = factors
        s["points"] = sum(f["points"] for f in factors)
        s["level"] = level_for(s["points"], bool(s["lab"]))
    order = {"never": 0, "first": 1, "soon": 2, "wait": 3}
    streams.sort(key=lambda s: (order[s["level"]], -s["points"], -(s["lab"] or {}).get("overall", 0), s["code"]))
    for i, s in enumerate(streams, 1):
        s["rank"] = i
    return streams


def format_distance(metres):
    if metres >= 1000:
        return f"{metres / 1000:.1f} km"
    return f"{round(metres / 10) * 10:.0f} m"


# ---------- record checks ----------

def common_factor(values_with_range):
    """The single power of ten that brings the most out-of-range values back in range.

    One factor for the whole batch, because a lost decimal point on import
    shifts every number by the same amount.
    """
    best, best_hits = None, 0
    for power in range(1, 8):
        hits = sum(1 for v, low, high in values_with_range if low <= v / 10 ** power <= high)
        if hits > best_hits:
            best, best_hits = 10 ** power, hits
    return best


def quantities(obs):
    out = []
    if "value" in obs.get("valueQuantity", {}):
        out.append(("value", obs["valueQuantity"]["value"]))
    for comp in obs.get("component", []):
        if "value" in comp.get("valueQuantity", {}):
            label = (comp.get("code", {}).get("coding") or [{}])[0].get("code", "value")
            out.append((label, comp["valueQuantity"]["value"]))
    return out


def impossible_values(observations):
    """Observations holding a number no real stream can have."""
    found = []
    for obs in observations:
        code = (obs.get("code", {}).get("coding") or [{}])[0].get("code")
        if code not in POSSIBLE:
            continue
        low, high, name = POSSIBLE[code]
        bad = [v for _, v in quantities(obs) if not low <= v <= high]
        if not bad:
            continue
        found.append({
            "id": obs["id"], "what": name, "value": max(bad, key=abs), "low": low, "high": high,
            "place": obs.get("subject", {}).get("reference", "").replace("Location/", ""),
            "period": (obs.get("effectivePeriod", {}).get("start") or obs.get("effectiveDateTime") or "")[:4],
        })
    factor = common_factor([(f["value"], f["low"], f["high"]) for f in found])
    for f in found:
        guess = f["value"] / factor if factor else None
        # a value only just out of range is some other mistake, not a shifted decimal point
        fits = guess is not None and max(f["low"], f["high"] / 1000) <= guess <= f["high"]
        f["likely"] = round(guess, 3) if fits else None
        f["factor"] = factor if fits else None
    return found


def shared_points(locations):
    """Groups of places recorded at exactly the same map point."""
    by_point = defaultdict(list)
    for loc in locations:
        pos = loc.get("position")
        if pos and "latitude" in pos and "longitude" in pos:
            by_point[(pos["latitude"], pos["longitude"])].append(loc)
    return [group for group in by_point.values() if len(group) > 1 and not same_stream(group)]


def same_stream(group):
    """True when every record in the group carries one shared code: one stream entered twice, not two places."""
    codes = [{i.get("value") for i in loc.get("identifier", [])} for loc in group]
    return bool(set.intersection(*codes))


def without_position(locations):
    return [l for l in locations if not (l.get("position") and "latitude" in l["position"])]


def test_entries(user_sites):
    return [s for s in user_sites if TEST_NAME.search(s["name"].strip())]


def repeated_names(user_sites):
    counts = Counter(s["name"].strip().lower() for s in user_sites)
    return {name: n for name, n in counts.items() if n > 1}


def age_in_words(start, today=None):
    years = years_between(start, today or date.today())
    if years < 1:
        return "less than a year ago"
    whole = int(years)
    return f"over {whole} year{'s' if whole != 1 else ''} ago"
