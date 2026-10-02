"""Send Stream Check-up's records to the OneAquaHealth FHIR sandbox.

Without --send it only prints what would be sent.

Run:  python3 scripts/publish.py            (dry run)
      python3 scripts/publish.py --send
"""
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

import checkup
import fhir

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SANDBOX = "https://sandbox.hl7europe.eu/oneaquahealth/fhir"


def post_bundle(bundle):
    req = urllib.request.Request(
        SANDBOX, data=json.dumps(bundle).encode(), method="POST",
        headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main(send):
    sites = json.loads((RAW / "sites.json").read_text())
    streams = [{"code": s["code"], "name": s["name"], "city": s["city"]["name"],
                "lat": s["latitude"], "lon": s["longitude"]} for s in sites]
    observations = json.loads((RAW / "fhir" / "Observation.json").read_text())
    today = date.today().isoformat()
    batches = {
        "locations": [fhir.location(s) for s in streams],
        "record_problems": [fhir.record_problem(f, today) for f in checkup.impossible_values(observations)],
    }
    published = {"sentOn": today, "sandbox": SANDBOX}
    for name, resources in batches.items():
        bundle = fhir.create_if_absent(resources)
        (ROOT / "data" / "fhir-out").mkdir(parents=True, exist_ok=True)
        (ROOT / "data" / "fhir-out" / f"{name}.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False))
        if not send:
            print(f"{name}: would send {len(resources)} (dry run)")
            continue
        reply = post_bundle(bundle)
        results = [e["response"] for e in reply.get("entry", [])]
        created = [r for r in results if r.get("status", "").startswith("201")]
        published[name] = [{"identifier": res["identifier"][0]["value"], "location": r.get("location"),
                            "status": r.get("status")} for res, r in zip(resources, results)]
        print(f"{name}: sent {len(resources)}, created {len(created)}, already there {len(results) - len(created)}")
    if send:
        (ROOT / "data" / "published.json").write_text(json.dumps(published, indent=1))


if __name__ == "__main__":
    main("--send" in sys.argv)
