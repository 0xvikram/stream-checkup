import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fhir

STREAM = {"code": "C5", "name": "Mina Hospital", "city": "Coimbra", "lat": 40.2186, "lon": -8.42733}
FOUND = {"id": "Obs-Almyros-Ph-2020", "what": "pH (acidity)", "value": 83800, "low": 0, "high": 14,
         "likely": 8.38, "factor": 10000}


class Location(unittest.TestCase):
    def test_carries_the_map_code_and_position(self):
        loc = fhir.location(STREAM)
        self.assertEqual(loc["identifier"], [{"system": fhir.SITE_CODES, "value": "C5"}])
        self.assertEqual(loc["position"], {"longitude": -8.42733, "latitude": 40.2186})
        self.assertEqual(loc["meta"]["profile"], [fhir.LOCATION_PROFILE])
        self.assertEqual(loc["address"]["city"], "Coimbra")


class RecordProblem(unittest.TestCase):
    def test_points_at_the_original_and_never_replaces_it(self):
        issue = fhir.record_problem(FOUND, "2026-10-03")
        self.assertEqual(issue["implicated"], [{"reference": "Observation/Obs-Almyros-Ph-2020"}])
        self.assertEqual(issue["status"], "preliminary")
        self.assertIn("83,800", issue["detail"])
        self.assertIn("0 to 14", issue["detail"])

    def test_states_the_likely_value_and_asks_for_confirmation(self):
        text = fhir.record_problem(FOUND, "2026-10-03")["mitigation"][0]["action"]["text"]
        self.assertIn("8.38", text)
        self.assertIn("10,000", text)
        self.assertIn("Confirm", text)

    def test_no_guess_when_none_fits(self):
        issue = fhir.record_problem({**FOUND, "likely": None, "factor": None}, "2026-10-03")
        self.assertIn("No simple correction", issue["mitigation"][0]["action"]["text"])


class Bundle(unittest.TestCase):
    def test_each_record_is_created_only_if_absent(self):
        bundle = fhir.create_if_absent([fhir.location(STREAM), fhir.record_problem(FOUND, "2026-10-03")])
        self.assertEqual(bundle["type"], "transaction")
        self.assertEqual([e["request"]["ifNoneExist"] for e in bundle["entry"]], [
            f"identifier={fhir.SITE_CODES}|C5",
            f"identifier={fhir.ISSUE_IDS}|Obs-Almyros-Ph-2020",
        ])
        self.assertTrue(all(e["request"]["method"] == "POST" for e in bundle["entry"]))


if __name__ == "__main__":
    unittest.main()
