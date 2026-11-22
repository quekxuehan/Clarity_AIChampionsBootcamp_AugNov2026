import unittest
from datetime import date

from event_planning import (
    build_event_assessment,
    select_event_reading,
    threshold_status,
)


class EventPlanningTests(unittest.TestCase):
    def test_today_event_selects_one_hour_pm25(self):
        value, reading_kind = select_event_reading(
            date(2026, 11, 22),
            date(2026, 11, 22),
            149,
            75,
        )
        self.assertEqual((value, reading_kind), (149, "PM2.5"))

    def test_future_event_selects_24_hour_psi(self):
        value, reading_kind = select_event_reading(
            date(2026, 11, 23),
            date(2026, 11, 22),
            149,
            75,
        )
        self.assertEqual((value, reading_kind), (75, "PSI"))

    def test_future_psi_reading_uses_psi_bands(self):
        assessment = build_event_assessment(
            pm25_value=201,
            setting="Outdoor",
            intensity="Strenuous",
            attendee_mix="Vulnerable attendees",
            duration_hours=6,
            event_date=date(2026, 11, 23),
            today=date(2026, 11, 22),
            reading_kind="PSI",
        )
        self.assertEqual(assessment.level, "Urgent review")
        self.assertIn("Very unhealthy PSI", assessment.summary)

    def test_event_more_than_seven_days_uses_long_range_planning(self):
        value, reading_kind = select_event_reading(
            date(2026, 11, 30),
            date(2026, 11, 22),
            149,
            75,
        )
        self.assertEqual((value, reading_kind), (None, "Planning"))

    def test_threshold_status(self):
        self.assertTrue(
            threshold_status(151, "High (151 µg/m³)").startswith("ALERT")
        )
        self.assertTrue(
            threshold_status(150, "High (151 µg/m³)").startswith("Below")
        )
        self.assertEqual(
            threshold_status(100, "Off"),
            "Alert threshold off",
        )

    def test_normal_reading_returns_monitor_checklist(self):
        assessment = build_event_assessment(
            pm25_value=55,
            setting="Outdoor",
            intensity="Low",
            attendee_mix="Healthy adults",
            duration_hours=2,
            event_date=date(2026, 11, 23),
            today=date(2026, 11, 22),
        )
        self.assertEqual(assessment.level, "Monitor")
        self.assertIn("future-dated", " ".join(assessment.actions))

    def test_elevated_strenuous_vulnerable_event_raises_actions(self):
        assessment = build_event_assessment(
            pm25_value=150,
            setting="Mixed indoor and outdoor",
            intensity="Strenuous",
            attendee_mix="Vulnerable attendees",
            duration_hours=6,
            event_date=date(2026, 11, 22),
            today=date(2026, 11, 22),
        )
        actions = " ".join(assessment.actions)
        self.assertEqual(assessment.level, "Prepare")
        self.assertIn("Reduce session intensity", actions)
        self.assertIn("elderly", actions)
        self.assertIn("indoors", actions)
        self.assertIn("Split exposure", actions)

    def test_very_high_reading_calls_for_urgent_review(self):
        assessment = build_event_assessment(
            pm25_value=251,
            setting="Outdoor",
            intensity="Strenuous",
            attendee_mix="Healthy adults",
            duration_hours=1,
            event_date=date(2026, 11, 22),
            today=date(2026, 11, 22),
        )
        actions = " ".join(assessment.actions)
        self.assertEqual(assessment.level, "Urgent review")
        self.assertIn("Reschedule or move", actions)

    def test_indoor_event_still_warns_to_recheck_official_advisories(self):
        assessment = build_event_assessment(
            pm25_value=200,
            setting="Indoor",
            intensity="Moderate",
            attendee_mix="Mixed or unknown",
            duration_hours=3,
            event_date=date(2026, 11, 22),
            today=date(2026, 11, 22),
        )
        actions = " ".join(assessment.actions)
        self.assertEqual(assessment.level, "Act")
        self.assertIn("indoor air-quality systems", actions)
        self.assertIn("official NEA advisories", actions)

    def test_missing_reading_returns_unable_to_assess(self):
        assessment = build_event_assessment(
            pm25_value=None,
            setting="Outdoor",
            intensity="Low",
            attendee_mix="Healthy adults",
            duration_hours=2,
            event_date=date(2026, 11, 22),
            today=date(2026, 11, 22),
        )
        self.assertEqual(assessment.level, "Unable to assess")
        self.assertIn("Recheck", assessment.actions[0])


if __name__ == "__main__":
    unittest.main()
