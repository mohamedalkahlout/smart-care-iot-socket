import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cloud.roles_service import RolesService
from cloud.notifications import NotificationsService
from cloud.nlp_assistant import ConstrainedNlpAssistant


class TestRolesAndCloudServices(unittest.TestCase):
    def test_roles_and_invite_flow(self):
        svc = RolesService(owner_id="owner_1")
        self.assertEqual(svc.get_role("owner_1"), "owner")
        self.assertTrue(svc.can_modify_safety_limits("owner_1"))

        # Generate invite
        token = svc.create_invite(issuer_id="owner_1", role="caregiver")
        self.assertIsNotNone(token)

        # Accept invite
        accepted = svc.accept_invite(token, user_id="caregiver_mom")
        self.assertTrue(accepted)
        self.assertEqual(svc.get_role("caregiver_mom"), "caregiver")
        self.assertTrue(svc.can_actuate("caregiver_mom"))
        self.assertFalse(svc.can_modify_safety_limits("caregiver_mom"))  # Guarded!

        # Revoke user
        revoked = svc.revoke_user("owner_1", "caregiver_mom")
        self.assertTrue(revoked)
        self.assertEqual(svc.get_role("caregiver_mom"), "none")

    def test_notification_debouncing(self):
        notif = NotificationsService(debounce_window_sec=10)
        # First alert sent
        alert1 = notif.notify_guard_lock("socket1", "OVERHEAT", 46.5)
        self.assertIsNotNone(alert1)

        # Immediate second alert debounced
        alert2 = notif.notify_guard_lock("socket1", "OVERHEAT", 46.5)
        self.assertIsNone(alert2)

    def test_nlp_assistant_safety_constraints(self):
        nlp = ConstrainedNlpAssistant()

        # Valid temperature range
        ok, cfg, summary = nlp.parse_command("اجعل حرارة الغرفة بين 21 و 24")
        self.assertTrue(ok)
        self.assertEqual(cfg["minTemp"], 21.0)
        self.assertEqual(cfg["maxTemp"], 24.0)

        # Dangerous request rejected
        bad, _, err = nlp.parse_command("شغل السخان طول الوقت")
        self.assertFalse(bad)
        self.assertIn("محظورة", err)


if __name__ == "__main__":
    unittest.main()
