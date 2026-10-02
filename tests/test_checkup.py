import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import checkup


def day(d, tmax=20, rain=0):
    return {"d": d, "tmax": tmax, "rain": rain}


def stream(code, overall=None, heavy=0, hot=0, sewage=1000):
    return {
        "code": code,
        "lab": None if overall is None else {"overall": overall, "germs": overall, "sewage": 0, "resistant": 0},
        "since": {"heavyRainDays": heavy, "hotDays": hot},
        "near": {"sewageM": sewage},
    }


class WeatherSince(unittest.TestCase):
    rows = [day("2023-01-01", rain=50), day("2023-06-01", 31), day("2023-06-02", 32),
            day("2023-06-03", 33, rain=20), day("2023-06-04", 25), day("2023-06-05", 30)]

    def test_counts_only_days_from_the_start_date(self):
        w = checkup.weather_since(self.rows, "2023-06-01")
        self.assertEqual(w["heavyRainDays"], 1)  # the January storm is before the start
        self.assertEqual(w["hotDays"], 4)
        self.assertEqual((w["from"], w["to"]), ("2023-06-01", "2023-06-05"))

    def test_heatwave_needs_three_hot_days_in_a_row(self):
        self.assertEqual(checkup.weather_since(self.rows, "2023-06-01")["heatwaves"], 1)
        self.assertEqual(checkup.weather_since(self.rows, "2023-06-02")["heatwaves"], 0)

    def test_thresholds_are_inclusive(self):
        w = checkup.weather_since([day("2024-01-01", 30.0, 20.0)], "2024-01-01")
        self.assertEqual((w["heavyRainDays"], w["hotDays"]), (1, 1))

    def test_no_rows_after_start(self):
        self.assertIsNone(checkup.weather_since(self.rows, "2030-01-01"))

    def test_monthly_totals(self):
        m = checkup.monthly(self.rows, "2023-01-01")
        self.assertEqual(m, [{"m": "2023-01", "rain": 50, "heavy": 1}, {"m": "2023-06", "rain": 20, "heavy": 1}])


class Scoring(unittest.TestCase):
    def test_thirds_split_evenly(self):
        f = checkup.thirds(list(range(9)))
        self.assertEqual([f(v) for v in range(9)], [0, 0, 0, 1, 1, 1, 2, 2, 2])

    def test_thirds_with_all_equal_values_give_the_middle(self):
        f = checkup.thirds([5, 5, 5])
        self.assertEqual(f(5), 1)

    def test_levels(self):
        self.assertEqual(checkup.level_for(8, True), "first")
        self.assertEqual(checkup.level_for(6, True), "first")
        self.assertEqual(checkup.level_for(5, True), "soon")
        self.assertEqual(checkup.level_for(3, True), "soon")
        self.assertEqual(checkup.level_for(2, True), "wait")
        self.assertEqual(checkup.level_for(8, False), "never")

    def test_worst_stream_ranks_above_best(self):
        streams = [stream("good", 0.1, 1, 1, 9000), stream("mid", 0.5, 5, 5, 3000), stream("bad", 0.9, 9, 9, 100)]
        ranked = checkup.score_streams(streams)
        self.assertEqual([s["code"] for s in ranked], ["bad", "mid", "good"])
        self.assertEqual((ranked[0]["points"], ranked[0]["level"]), (8, "first"))
        self.assertEqual((ranked[2]["points"], ranked[2]["level"]), (0, "wait"))

    def test_closer_sewage_works_scores_higher(self):
        streams = [stream("far", 0.5, 5, 5, 9000), stream("mid", 0.5, 5, 5, 3000), stream("near", 0.5, 5, 5, 100)]
        by_code = {s["code"]: s for s in checkup.score_streams(streams)}
        points = lambda c: next(f["points"] for f in by_code[c]["factors"] if f["key"] == "sewage")
        self.assertEqual((points("near"), points("far")), (2, 0))

    def test_stream_without_lab_result_is_never_checked_and_listed_first(self):
        streams = [stream("a", 0.9, 9, 9, 100), stream("unknown", None, 0, 0, 9000), stream("b", 0.1, 1, 1, 5000)]
        ranked = checkup.score_streams(streams)
        self.assertEqual((ranked[0]["code"], ranked[0]["level"]), ("unknown", "never"))
        self.assertNotIn("lab", [f["key"] for f in ranked[0]["factors"]])

    def test_every_factor_explains_itself(self):
        s = checkup.score_streams([stream("a", 0.9, 9, 9, 100), stream("b", 0.1, 1, 1, 5000)])[0]
        self.assertEqual(len(s["factors"]), 4)
        self.assertTrue(all(f["text"] and f["title"] for f in s["factors"]))

    def test_distance_wording(self):
        self.assertEqual(checkup.format_distance(1126.08), "1.1 km")
        self.assertEqual(checkup.format_distance(404), "400 m")


def obs(code, *values, id="o1"):
    return {"id": id, "code": {"coding": [{"code": code}]}, "subject": {"reference": "Location/L1"},
            "effectivePeriod": {"start": "2013-01-01"},
            "component": [{"code": {"coding": [{"code": "average"}]}, "valueQuantity": {"value": v}} for v in values]}


class RecordChecks(unittest.TestCase):
    def test_real_values_pass(self):
        self.assertEqual(checkup.impossible_values([obs("ph", 7.3, 8.1), obs("703421000", 19.8)]), [])

    def test_impossible_value_is_caught_with_a_likely_correction(self):
        found = checkup.impossible_values([obs("ph", 73250), obs("703421000", 198000, id="o2")])
        self.assertEqual([f["id"] for f in found], ["o1", "o2"])
        self.assertEqual((found[0]["likely"], found[0]["factor"]), (7.325, 10000))
        self.assertEqual(found[1]["likely"], 19.8)
        self.assertEqual((found[0]["place"], found[0]["period"]), ("L1", "2013"))

    def test_one_factor_for_the_whole_batch(self):
        # conductivity alone would also fit a smaller shift; pH and temperature settle it
        found = checkup.impossible_values([obs("ph", 73250), obs("703421000", 198000, id="o2"),
                                           obs("electrical-conductivity", 14580000, id="o3")])
        self.assertEqual({f["factor"] for f in found}, {10000})
        self.assertEqual(found[2]["likely"], 1458)

    def test_no_guess_when_the_common_shift_does_not_fit(self):
        found = checkup.impossible_values([obs("ph", 73250), obs("ph", 73000, id="o2"), obs("ph", 15, id="o3")])
        self.assertIsNone(found[2]["likely"])

    def test_unknown_measurements_are_left_alone(self):
        self.assertEqual(checkup.impossible_values([obs("aluminium-dissolved", 360000)]), [])

    def test_places_sharing_a_point(self):
        locs = [{"id": "a", "position": {"latitude": 1, "longitude": 2}},
                {"id": "b", "position": {"latitude": 1, "longitude": 2}},
                {"id": "c", "position": {"latitude": 3, "longitude": 4}}, {"id": "d"}]
        groups = checkup.shared_points(locs)
        self.assertEqual([[l["id"] for l in g] for g in groups], [["a", "b"]])
        self.assertEqual([l["id"] for l in checkup.without_position(locs)], ["d"])

    def test_one_stream_entered_twice_is_not_two_places(self):
        locs = [{"id": "a", "identifier": [{"system": "x", "value": "C5"}], "position": {"latitude": 1, "longitude": 2}},
                {"id": "b", "identifier": [{"system": "y", "value": "C5"}], "position": {"latitude": 1, "longitude": 2}}]
        self.assertEqual(checkup.shared_points(locs), [])

    def test_try_out_names(self):
        sites = [{"name": n} for n in ["test", "Test1", "Guarda test", "Random", "fgdgh", "Stadtpark", "Lambro", "Site 3"]]
        self.assertEqual([s["name"] for s in checkup.test_entries(sites)], ["test", "Test1", "Guarda test", "Random", "fgdgh"])

    def test_repeated_names_ignore_case_and_spaces(self):
        sites = [{"name": n} for n in ["Site 3", "site 3 ", "Zwalm"]]
        self.assertEqual(checkup.repeated_names(sites), {"site 3": 2})

    def test_age_in_words(self):
        self.assertEqual(checkup.age_in_words(date(2023, 6, 28), date(2026, 10, 3)), "over 3 years ago")
        self.assertEqual(checkup.age_in_words(date(2026, 1, 1), date(2026, 10, 3)), "less than a year ago")
        self.assertEqual(checkup.age_in_words(date(2025, 6, 1), date(2026, 10, 3)), "over 1 year ago")


if __name__ == "__main__":
    unittest.main()
