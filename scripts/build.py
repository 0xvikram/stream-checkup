"""Turn the raw snapshot into the one file the website reads: web/public/data.json.

Run:  python3 scripts/build.py
"""
import json
from collections import Counter
from datetime import date
from pathlib import Path

import checkup
import fhir

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "web" / "public" / "data.json"
HISTORY = ROOT / "data" / "history"
FHIR = "https://sandbox.hl7europe.eu/oneaquahealth/fhir"
TEMP_SYSTEM = "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"


def load(name):
    return json.loads((RAW / name).read_text())


def build_streams(snapshot_day):
    labs = {r["researchSiteCode"]: r for r in load("health_risks.json")}
    urban = {r["researchSiteCode"]: r for r in load("urban_parameters.json")}
    streams = []
    for site in load("sites.json"):
        code = site["code"]
        weather = load(f"weather/{code}.json")
        weather = weather if isinstance(weather, list) else []
        lab, near = labs.get(code), urban.get(code)
        lab_day = lab["samplingDate"][:10] if lab else None
        # with no lab check on record, count weather over the whole period we hold
        since_day = lab_day or (weather[0]["d"] if weather else None)
        streams.append({
            "code": code,
            "name": site["name"],
            "city": site["city"]["name"],
            "lat": site["latitude"],
            "lon": site["longitude"],
            "lab": lab and {
                "date": lab_day,
                "age": checkup.age_in_words(date.fromisoformat(lab_day), snapshot_day),
                "overall": lab["healthRiskScore"],
                "germs": lab["scaledPathogenRisk"],
                "sewage": lab["scaledFecalRisk"],
                "resistant": lab["scaledArgRisk"],
            },
            "since": checkup.weather_since(weather, since_day) if since_day else None,
            "monthly": checkup.monthly(weather, since_day) if since_day else [],
            "near": near and {
                "sewageM": near["distanceToSewageStations"],
                "hospitalM": near["distanceToHospitals"],
                "pavedPct": near["imperviousPct250m"],
                "greenPct": near["vegCoverFrac250m"],
            },
        })
    checkup.score_streams(streams)
    seen = Counter()
    for s in streams:  # already in priority order
        seen[s["city"]] += 1
        s["cityRank"] = seen[s["city"]]
    return streams


def build_citizen_sites():
    sites = load("user_sites.json")
    tests = {s["userSiteCode"] for s in checkup.test_entries(sites)}
    return [{
        "code": s["userSiteCode"], "name": s["name"].strip(),
        "lat": s["latitude"], "lon": s["longitude"],
        "looksLikeTest": s["userSiteCode"] in tests,
    } for s in sites]


def linked_codes(locations):
    """Map codes that some place in the health-data system carries as an identifier."""
    return {i.get("value") for l in locations for i in l.get("identifier", []) if i.get("value")}


def location_ids(locations):
    """Map code -> id of the place that carries it under the shared naming system."""
    return {i["value"]: l["id"] for l in locations for i in l.get("identifier", [])
            if i.get("system") == fhir.SITE_CODES}


def pinned_notes():
    """Observation id -> link to the note Stream Check-up pinned to it."""
    path = RAW / "fhir" / "DetectedIssue.json"
    issues = json.loads(path.read_text()) if path.exists() else []
    notes = {}
    for issue in issues:
        ours = any(i.get("system") == fhir.ISSUE_IDS for i in issue.get("identifier", []))
        for ref in issue.get("implicated", []) if ours else []:
            notes[ref["reference"].split("/")[-1]] = f"{FHIR}/DetectedIssue/{issue['id']}"
    return notes


def summary(data):
    """The few facts worth comparing from one day to the next."""
    return {
        "date": data["snapshot"],
        "levels": {s["code"]: s["level"] for s in data["streams"]},
        "labDates": {s["code"]: s["lab"]["date"] for s in data["streams"] if s["lab"]},
        "problems": {p["key"]: p["count"] for p in data["problems"]},
        "titles": {p["key"]: p["title"] for p in data["problems"]},
        "citizenSites": sorted(s["code"] for s in data["citizenSites"]),
    }


def changes_since(before, now, names):
    """Plain sentences for what differs between two summaries."""
    out = []
    for key, count in now["problems"].items():
        was = before["problems"].get(key)
        if was is not None and was != count and key not in ("lag", "old"):
            out.append(f"{now['titles'][key]}: {was} before, {count} now.")
    for code, day in now["labDates"].items():
        if before["labDates"].get(code) != day:
            out.append(f"New lab result for {names[code]} ({day}).")
    moved = [c for c, level in now["levels"].items() if before["levels"].get(c, level) != level]
    if moved:
        shown = ", ".join(names[c] for c in moved[:4]) + (" and others" if len(moved) > 4 else "")
        out.append(f"{len(moved)} stream{'s' if len(moved) != 1 else ''} changed level: {shown}.")
    added = set(now["citizenSites"]) - set(before["citizenSites"])
    if added:
        out.append(f"{len(added)} new stream{'s' if len(added) != 1 else ''} added by citizens.")
    return out


def record_history(data):
    """Keep one summary per day, plus the very first one as the baseline."""
    HISTORY.mkdir(parents=True, exist_ok=True)
    now = summary(data)
    baseline_path = HISTORY / "baseline.json"
    if not baseline_path.exists():
        baseline_path.write_text(json.dumps(now))
    baseline = json.loads(baseline_path.read_text())
    earlier = sorted(p for p in HISTORY.glob("20*.json") if p.stem < now["date"])
    previous = json.loads(earlier[-1].read_text()) if earlier else baseline
    (HISTORY / f"{now['date']}.json").write_text(json.dumps(now))
    names = {s["code"]: s["name"] for s in data["streams"]}
    return {
        "since": previous["date"],
        "sinceIsFirst": not earlier,
        "items": changes_since(previous, now, names),
        "baseline": baseline["problems"],
    }


def one_per_measurement(bad, limit=8):
    """The worst record of each kind, easiest to grasp first (pH, then temperature)."""
    worst = {}
    for b in bad:
        if b["what"] not in worst or b["value"] > worst[b["what"]]["value"]:
            worst[b["what"]] = b
    easy_first = sorted(worst.values(), key=lambda b: (not b["what"].startswith("pH"),
                                                         "temperature" not in b["what"], b["what"]))
    return easy_first[:limit]


def build_problems(streams, citizen_sites, snapshot_day):
    observations = load("fhir/Observation.json")
    locations = load("fhir/Location.json")
    user_sites = load("user_sites.json")
    api_codes = {s["code"] for s in streams}
    problems = []

    def add(key, title, count, saw, matters, fix, owner, examples):
        problems.append({"key": key, "title": title, "count": count, "saw": saw,
                         "matters": matters, "fix": fix, "owner": owner, "examples": examples})

    notes = pinned_notes()
    place_names = {l["id"]: l.get("name", l["id"]) for l in locations}
    bad = checkup.impossible_values(observations)
    for item in bad:
        item["place"] = place_names.get(item["place"], item["place"])
    places = Counter(b["place"] for b in bad)
    fixable = [b for b in bad if b["likely"] is not None]
    add("impossible", "Measurements that cannot be real", len(bad),
        f"{len(bad)} lab records hold numbers no stream can have, such as a pH of "
        f"{max((b['value'] for b in bad if b['what'].startswith('pH')), default=0):,.0f} "
        f"(the scale stops at 14). All of them belong to: {', '.join(sorted(places))}.",
        "Anyone who averages or charts these records gets nonsense, and may not notice.",
        f"The numbers look like a decimal point was lost when the data was loaded. "
        f"Dividing by {bad[0]['factor'] or 0:,} gives a believable value for {len(fixable)} of the {len(bad)}, shown below. "
        "A person who knows the original lab sheet must confirm before anything is changed.",
        "them",
        [{"label": f"{b['what']}, {b['place']}, {b['period']}",
          "recorded": f"{b['value']:,.0f}", "likely": None if b["likely"] is None else f"{b['likely']:g}",
          "detail": f"recorded {b['value']:,.0f}" + (f", likely {b['likely']:g}" if b["likely"] is not None else ""),
          "url": f"{FHIR}/Observation/{b['id']}", "note": notes.get(b["id"])} for b in one_per_measurement(bad)])
    problems[-1]["flagged"] = sum(1 for b in bad if b["id"] in notes)

    groups = checkup.shared_points(locations)
    stacked = sum(len(g) for g in groups)
    add("stacked", "Different places on the same map point", stacked,
        f"{stacked} monitoring places are recorded at exactly the same spot as another place.",
        "On a map they sit on top of each other, so results cannot be told apart by location.",
        "Give each place its own position. We cannot guess the true positions.",
        "them",
        [{"label": f"{len(g)} places at {g[0]['position']['latitude']}, {g[0]['position']['longitude']}",
          "detail": ", ".join(l.get("name", l["id"]) for l in g[:4]) + (" …" if len(g) > 4 else ""),
          "url": f"{FHIR}/Location/{g[0]['id']}"} for g in groups])

    nowhere = checkup.without_position(locations)
    add("nowhere", "Places with no position at all", len(nowhere),
        f"{len(nowhere)} places in the health-data system have a name but no position.",
        "A record that cannot be placed on a map cannot be linked to a stream.",
        "Add a position, or remove the place if it is a duplicate.",
        "them",
        [{"label": l.get("name", l["id"]), "detail": f"id {l['id']}", "url": f"{FHIR}/Location/{l['id']}"}
         for l in nowhere])

    linked = linked_codes(locations) & api_codes
    add("unlinked", "Two systems that name the same streams differently", len(streams) - len(linked),
        f"The map data knows {len(streams)} streams by codes like C1. In the health-data system, "
        f"{len(linked)} of them can be found by that code.",
        "Without a shared name, a lab result in one system cannot be matched to a stream in the other.",
        f"Stream Check-up adds each missing stream to the health-data system, carrying its map code.",
        "us", [])

    tests = [s for s in citizen_sites if s["looksLikeTest"]]
    add("tests", "Try-out entries on the public list of citizen streams", len(tests),
        f"{len(tests)} of the {len(citizen_sites)} streams added by citizens have names like "
        f"{', '.join(repr(s['name']) for s in tests[:3])}.",
        "They appear next to real streams, so counts of citizen activity are too high.",
        "Stream Check-up hides them from its own lists and names them here so they can be removed.",
        "us",
        [{"label": s["name"], "detail": f"{s['lat']:.3f}, {s['lon']:.3f}", "url": None} for s in tests])

    repeats = checkup.repeated_names(user_sites)
    add("repeats", "Citizen streams that share a name", sum(repeats.values()),
        f"{len(repeats)} names are used by more than one citizen stream, "
        f"for example 'Site 3' ({repeats.get('site 3', 0)} times).",
        "A coordinator reading the list cannot tell which is which.",
        "Ask for a place name when a citizen adds a stream, and warn if the name is taken nearby.",
        "them",
        [{"label": name, "detail": f"used {n} times", "url": None}
         for name, n in sorted(repeats.items(), key=lambda kv: -kv[1])[:6]])

    never = [s for s in streams if not s["lab"]]
    add("never", "Research streams with no lab result", len(never),
        f"{len(never)} of the {len(streams)} research streams have no health-risk result in the public data.",
        "These streams look the same as checked ones on the map, but nothing is known about them.",
        "Stream Check-up marks them 'Never checked' and puts them at the top of the list.",
        "us",
        [{"label": f"{s['name']} ({s['code']})", "detail": s["city"], "url": None} for s in never])

    lab_years = Counter(s["lab"]["date"][:4] for s in streams if s["lab"])
    oldest_year, oldest_count = lab_years.most_common(1)[0]
    add("old", "A lab picture that has not been refreshed", oldest_count,
        f"{oldest_count} of the {sum(lab_years.values())} lab results are from {oldest_year}. "
        "Each stream has been sampled once.",
        "Decisions made today rest on what the water was like years ago.",
        "Stream Check-up shows the age on every stream and ranks where to look first.",
        "us", [])

    last_day = max(s["since"]["to"] for s in streams if s["since"])
    lag = (snapshot_day - date.fromisoformat(last_day)).days
    add("lag", "Weather data that stops a few days back", lag,
        f"The newest weather day on record is {last_day}, {lag} days before this snapshot.",
        "A storm in the last week would not show up yet.",
        "State the last weather day wherever weather is shown. Stream Check-up does this on every card.",
        "us", [])

    headers_path = RAW / "browser_headers.json"
    allow = json.loads(headers_path.read_text())["allowOrigin"] if headers_path.exists() else []
    add("browser", "A health-data system that web pages cannot read", 1 if len(allow) > 1 else 0,
        f"The test system answers a web page with {len(allow)} 'allow' headers "
        f"({' and '.join(repr(v) for v in allow)}). Browsers accept exactly one, so they refuse the answer.",
        "No website can read or write records there directly, so every team has to build a workaround.",
        "Send a single 'allow' header. Until then Stream Check-up passes its requests through a small relay.",
        "them", [])

    temp = [o for o in observations
            if any(c.get("system") == TEMP_SYSTEM for c in o.get("code", {}).get("coding", []))]
    typo = [o for o in observations if "morophology" in json.dumps(o)]
    add("words", "A word list still marked 'temporary'", len(temp),
        f"{len(temp)} records use a list of terms that is still named 'temporary', and "
        f"{len(typo)} records carry the misspelling 'morophology'.",
        "Other systems match records by these exact words, so a spelling fixed later breaks the match.",
        "Publish a final list and correct the spelling before more records depend on it.",
        "them",
        [{"label": "morophology", "detail": f"in {len(typo)} records", "url": f"{FHIR}/Observation/{typo[0]['id']}"}]
        if typo else [])

    return problems


def main():
    snapshot_day = date.fromisoformat(load("snapshot.json")["fetchedOn"])
    streams = build_streams(snapshot_day)
    citizen_sites = build_citizen_sites()
    problems = build_problems(streams, citizen_sites, snapshot_day)
    ids = location_ids(load("fhir/Location.json"))
    for s in streams:
        s["fhirId"] = ids.get(s["code"])
    levels = Counter(s["level"] for s in streams)
    labs = [s["lab"]["date"] for s in streams if s["lab"]]
    data = {
        "snapshot": snapshot_day.isoformat(),
        "lastWeatherDay": max(s["since"]["to"] for s in streams if s["since"]),
        "levels": checkup.LEVELS,
        "counts": {
            "streams": len(streams),
            "cities": len({s["city"] for s in streams}),
            "withLab": len(labs),
            "labFrom2023": sum(1 for d in labs if d.startswith("2023")),
            "citizenSites": sum(1 for s in citizen_sites if not s["looksLikeTest"]),
            "recordProblems": sum(p["count"] for p in problems if p["key"] in ("impossible", "stacked", "nowhere")),
            **{k: levels.get(k, 0) for k in checkup.LEVELS},
        },
        "streams": streams,
        "citizenSites": citizen_sites,
        "problems": problems,
    }
    history = record_history(data)
    for p in problems:
        p["was"] = history["baseline"].get(p["key"], p["count"])
    data["problems"] = [p for p in problems if p["count"] or p["was"]]
    data["changes"] = {k: history[k] for k in ("since", "sinceIsFirst", "items")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False))
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
    print("levels:", dict(levels))
    for p in data["problems"]:
        print(f"  {p['count']:>4}  (was {p['was']})  {p['title']}")
    print("changes:", data["changes"]["items"] or "none")


if __name__ == "__main__":
    main()
