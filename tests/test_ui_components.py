from __future__ import annotations

import unittest

from src.ui_components import floating_action_markup, floating_action_target


class FloatingActionTests(unittest.TestCase):
    def test_citizen_actions_are_visible_and_staff_actions_are_not(self) -> None:
        markup = floating_action_markup("citizen", unread_count=9)
        self.assertIn("Report an issue", markup)
        self.assertIn("Track request", markup)
        self.assertIn("Help", markup)
        self.assertNotIn("Agency quick actions", markup)
        self.assertNotIn("Inbox", markup)
        self.assertNotIn("Notifications", markup)

    def test_agency_actions_show_unread_badge(self) -> None:
        markup = floating_action_markup("officer", unread_count=123)
        self.assertIn("Inbox", markup)
        self.assertIn("Map", markup)
        self.assertIn("Notifications", markup)
        self.assertIn("aria-label=\"123 unread notifications\"", markup)
        self.assertIn(">99+</span>", markup)
        self.assertNotIn("Report an issue", markup)

    def test_query_routes_are_enforced_by_role(self) -> None:
        self.assertEqual(floating_action_target("report", "citizen"), "Report Complaint")
        self.assertEqual(floating_action_target("inbox", "officer"), "Agency Portal")
        self.assertIsNone(floating_action_target("inbox", "citizen"))
        self.assertIsNone(floating_action_target("notifications", "citizen"))
        self.assertIsNone(floating_action_target("unknown", "administrator"))


if __name__ == "__main__":
    unittest.main()
