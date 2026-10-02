"""Pull a dated snapshot of OneAquaHealth's public data into data/raw/.

Sources (all public, no login):
  - api.enora-oah.eu/api        the API behind the Resilience Map
  - sandbox.hl7europe.eu        the OneAquaHealth FHIR sandbox

Run:  python3 scripts/fetch.py               everything (about 5 minutes)
      python3 scripts/fetch.py --records     only the health-data records (seconds)
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

API = "https://api.enora-oah.eu/api"
FHIR = "https://sandbox.hl7europe.eu/oneaquahealth/fhir"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
WEATHER_FROM = "2023-01-01T00:00:00Z"
FHIR_TYPES = ["Location", "Observation", "Organization", "Device", "Group", "QuestionnaireResponse",
              "DetectedIssue", "ServiceRequest"]


def get(url, accept="application/json", tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "stream-checkup/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403, 404):
                return {"_error": e.code}
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return {"_error": "unreachable"}


def save(name, obj):
    path = RAW / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False))


def fetch_api():
    for name, path in [
        ("cities", "cities/all"),
        ("sites", "sites/all"),
        ("user_sites", "sites/user-generated"),
        ("health_risks", "resilience-map/health-risks"),
        ("urban_parameters", "resilience-map/urban-parameters"),
    ]:
        data = get(f"{API}/{path}")
        if isinstance(data, dict) and "_error" in data:
            sys.exit(f"could not read {path}: {data['_error']}")
        save(f"{name}.json", data)
        print(f"{name}: {len(data)} rows")


def fetch_weather():
    sites = json.loads((RAW / "sites.json").read_text())
    end = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
    query = urllib.parse.urlencode({"start": WEATHER_FROM, "end": end})
    for i, site in enumerate(sites, 1):
        code = site["code"]
        rows = get(f"{API}/resilience-map/weather?siteCode={urllib.parse.quote(code)}&{query}")
        # keep only the fields the check-up uses
        if isinstance(rows, list):
            rows = [{"d": r["date"], "tmax": r.get("t2mMaxC"), "rain": r.get("precipTotalMm")} for r in rows]
        save(f"weather/{code}.json", rows)
        print(f"weather {i}/{len(sites)} {code}: {len(rows) if isinstance(rows, list) else rows}")
        time.sleep(0.3)


def fetch_fhir():
    for rtype in FHIR_TYPES:
        resources, url = [], f"{FHIR}/{rtype}?_count=200"
        while url:
            bundle = get(url, accept="application/fhir+json")
            if "_error" in bundle:
                break
            for entry in bundle.get("entry", []):
                res = entry["resource"]
                res.pop("text", None)  # generated narrative, not needed
                resources.append(res)
            url = next((l["url"] for l in bundle.get("link", []) if l["relation"] == "next"), None)
        save(f"fhir/{rtype}.json", resources)
        print(f"fhir {rtype}: {len(resources)}")


def fetch_browser_headers():
    """How the sandbox answers a web page from another address (it decides if browsers may read it)."""
    req = urllib.request.Request(f"{FHIR}/Location?_count=1", headers={
        "Accept": "application/fhir+json", "Origin": "https://stream-checkup.example"})
    with urllib.request.urlopen(req, timeout=60) as r:
        values = r.headers.get_all("Access-Control-Allow-Origin") or []
    save("browser_headers.json", {"allowOrigin": values})
    print("allow-origin headers:", values)


if __name__ == "__main__":
    if "--records" not in sys.argv:
        fetch_api()
        fetch_weather()
    fetch_fhir()
    fetch_browser_headers()
    save("snapshot.json", {"fetchedOn": date.today().isoformat(), "api": API, "fhir": FHIR})
    print("done")
