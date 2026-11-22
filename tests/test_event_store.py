import tempfile
import unittest
from pathlib import Path

from event_store import (
    EventPlan,
    EventPlanStore,
    plan_checklist_progress,
    plan_followup_status,
)


class EventPlanStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "plans.sqlite3"
        self.store = EventPlanStore(self.database_path)

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_save_list_load_and_update_plan(self):
        plan_id = self.store.save(
            "Concert",
            {"region": "Central", "handover_note": "Monitor at 5 PM"},
        )
        plans = self.store.list_plans()
        self.assertEqual([plan.name for plan in plans], ["Concert"])

        plan = self.store.get(plan_id)
        self.assertEqual(plan.data["region"], "Central")

        updated_id = self.store.save(
            "Concert",
            {"region": "West", "handover_note": "Moved venue"},
        )
        self.assertEqual(updated_id, plan_id)
        self.assertEqual(self.store.get(plan_id).data["region"], "West")
        self.assertEqual(len(self.store.list_plans()), 1)

    def test_rejects_empty_name(self):
        with self.assertRaisesRegex(ValueError, "event name"):
            self.store.save("  ", {"region": "East"})

    def test_delete_plan(self):
        plan_id = self.store.save("Race", {"region": "North"})
        self.store.delete(plan_id)
        self.assertEqual(self.store.list_plans(), ())

    def test_plans_are_isolated_by_owner(self):
        first_id = self.store.save(
            "Concert",
            {"region": "Central"},
            owner_id="browser-a",
        )
        self.store.save("Race", {"region": "North"}, owner_id="browser-b")

        first_plans = self.store.list_plans(owner_id="browser-a")
        second_plans = self.store.list_plans(owner_id="browser-b")

        self.assertEqual([plan.name for plan in first_plans], ["Concert"])
        self.assertEqual([plan.name for plan in second_plans], ["Race"])

        self.store.delete(first_id, owner_id="browser-b")
        self.assertTrue(self.store.get(first_id).owner_id == "browser-a")

    def test_plan_card_status_helpers(self):
        plan = EventPlan(
            id=1,
            name="Race",
            data={
                "checklist": {"0": True, "1": False, "2": True},
                "safety_owner": "Alex",
                "next_check": "5 PM",
                "handover_note": "Monitor the venue",
            },
            updated_at="2026-11-22 11:00:00",
        )
        self.assertEqual(plan_checklist_progress(plan), (2, 3))
        self.assertEqual(plan_followup_status(plan), "Follow-up ready")

    def test_plan_card_followup_needs_details(self):
        plan = EventPlan(
            id=2,
            name="Concert",
            data={"checklist": {}, "safety_owner": "Sam"},
            updated_at="2026-11-22 11:00:00",
        )
        self.assertEqual(plan_followup_status(plan), "Needs follow-up details")

    def test_editable_checklist_progress(self):
        plan = EventPlan(
            id=3,
            name="Festival",
            data={
                "checklist_items": [
                    {"text": "Prepare shade", "completed": True},
                    {"text": "Prepare indoor fallback", "completed": False},
                ],
            },
            updated_at="2026-11-22 11:00:00",
        )
        self.assertEqual(plan_checklist_progress(plan), (1, 2))


if __name__ == "__main__":
    unittest.main()
