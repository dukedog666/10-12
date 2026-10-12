import sys
import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard import daily_counts, filter_period, headline_metrics, load_data, weekly_check


class DashboardChecks(unittest.TestCase):
    def test_source_totals_and_card_exclusion(self):
        all_data = load_data()
        self.assertEqual(len(all_data), 3898)
        data = all_data.loc[all_data.source.eq("index_1")]
        self.assertNotIn("card", data.columns)
        self.assertEqual(len(data), 3636)
        self.assertAlmostEqual(headline_metrics(data)["sales"], 115431.58, places=2)
        self.assertEqual(int(data.cash_type.eq("cash").sum()), 89)

    def test_unknown_day_is_not_zero(self):
        data = load_data()
        counts = daily_counts(filter_period(data, "2024-05-01", "2024-05-06"), "2024-05-01", "2024-05-06")
        self.assertTrue(pd.isna(counts.loc[0, "transactions"]))
        self.assertEqual(int(counts.transactions.isna().sum()), 3)
        self.assertNotEqual(counts.loc[1, "segment"], counts.loc[5, "segment"])
        result = weekly_check(data, "2024-04-20", "2024-05-06", data.date.max())
        self.assertEqual(result["status"], "unavailable")

    def test_illustrative_threshold_and_short_period(self):
        dates = pd.date_range("2025-01-01", periods=14)
        records = [{"date": day} for i, day in enumerate(dates) for _ in range(10 if i < 7 else 7)]
        sample = pd.DataFrame(records)
        result = weekly_check(sample, dates[0], dates[-1], "2025-01-15")
        self.assertEqual(result["status"], "review")
        self.assertAlmostEqual(result["change"], -0.30)
        self.assertEqual(weekly_check(sample, dates[-2], dates[-1], "2025-01-15")["status"], "unavailable")

    def test_app_default_filter_and_full_period(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 3)
        self.assertEqual(len(app.get("vega_lite_chart")), 2)
        all_data = load_data()
        data = all_data.loc[all_data.source.eq("index_1")]
        chosen = app.date_input[0].value
        expected = headline_metrics(filter_period(data, *chosen))
        self.assertEqual(app.metric[1].value, f"{expected['transactions']:,}")
        app.date_input[0].set_value((data.date.min().date(), data.date.max().date())).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "115,431.58")
        self.assertEqual(app.metric[1].value, "3,636")
        self.assertEqual(app.metric[2].value, "31.75")

    def test_empty_and_single_endpoint_filters(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        no_records = pd.Timestamp("2024-05-01").date()
        app.date_input[0].set_value((no_records, no_records)).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[1].value, "0")
        self.assertEqual(app.metric[2].value, "—")
        self.assertEqual(len(app.get("vega_lite_chart")), 0)
        app.date_input[0].set_value((no_records,)).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 0)

    def test_source_switch_preserves_secondary_rows_and_duplicates(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        app.selectbox[0].set_value("index_2").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 3)
        self.assertEqual(len(app.get("vega_lite_chart")), 2)
        data = load_data()
        secondary = data.loc[data.source.eq("index_2")]
        app.date_input[0].set_value((secondary.date.min().date(), secondary.date.max().date())).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[1].value, "262")
        self.assertEqual(app.metric[0].value, "6,890.00")
        self.assertTrue(any("2 identical extra" in warning.value for warning in app.warning))
        app.selectbox[0].set_value("index_1").run()
        self.assertFalse(app.exception)
        self.assertNotEqual(app.metric[1].value, "262")


if __name__ == "__main__":
    unittest.main()
