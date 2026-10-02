"""Can a stream's surroundings tell us its lab health risk? A leave-one-out test.

Each stream with a lab result is hidden in turn and estimated from the streams
whose surroundings are most alike. Compared with simply guessing the average.

Run:  python3 scripts/twin_test.py
"""
import json
import statistics as st
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
SKIP = ("id", "researchSiteCode", "samplingDate")
TWINS = 5


def main():
    lab = {r["researchSiteCode"]: r["healthRiskScore"] for r in json.loads((RAW / "health_risks.json").read_text())}
    urban = {r["researchSiteCode"]: r for r in json.loads((RAW / "urban_parameters.json").read_text())}
    city = {s["code"]: s["city"]["id"] for s in json.loads((RAW / "sites.json").read_text())}
    codes = [c for c in lab if c in urban]

    measures = [k for k in urban[codes[0]] if k not in SKIP]
    measures = [k for k in measures
                if all(urban[c][k] is not None for c in codes) and st.pstdev(urban[c][k] for c in codes) > 0]
    scaled = {c: [] for c in codes}
    for k in measures:
        mean, spread = st.mean(urban[c][k] for c in codes), st.pstdev(urban[c][k] for c in codes)
        for c in codes:
            scaled[c].append((urban[c][k] - mean) / spread)

    errors = {"overall average": [], "city average": [], f"{TWINS} most similar streams": []}
    for c in codes:
        others = [o for o in codes if o != c]
        errors["overall average"].append(abs(lab[c] - st.mean(lab[o] for o in others)))
        same_city = [lab[o] for o in others if city[o] == city[c]]
        errors["city average"].append(abs(lab[c] - st.mean(same_city)))
        nearest = sorted(others, key=lambda o: sum((a - b) ** 2 for a, b in zip(scaled[c], scaled[o])))[:TWINS]
        errors[f"{TWINS} most similar streams"].append(abs(lab[c] - st.mean(lab[o] for o in nearest)))

    print(f"{len(codes)} streams, {len(measures)} measures of surroundings")
    for name, errs in errors.items():
        print(f"  guess from the {name:<26} average error {st.mean(errs):.3f}")


if __name__ == "__main__":
    main()
