import unittest

from maya.core import user


class TestUserPermissions(unittest.TestCase):
    def test_permissions_from_v1_me_preserves_v1_names(self):
        me = {
            "permissions": [
                {"grant_id": 20, "name": "employee"},
                {"grant_id": 10, "name": "user"},
                {"grant_id": 30, "name": "admin"},
            ]
        }

        self.assertEqual(user.permissions_from_me(me), ["user", "employee", "admin"])

    def test_permissions_from_v2_viewer_role_maps_to_user(self):
        self.assertEqual(user.permissions_from_me({"role": 0}), ["user"])

    def test_permissions_from_v2_verified_user_without_role_maps_to_user(self):
        self.assertEqual(user.permissions_from_me({"role": None}), ["user"])

    def test_permissions_from_v2_editor_role_maps_to_employee_and_user(self):
        self.assertEqual(user.permissions_from_me({"role": 10}), ["employee", "user"])

    def test_permissions_from_v2_manager_role_maps_to_employee_and_user(self):
        self.assertEqual(user.permissions_from_me({"role": 20}), ["employee", "user"])

    def test_permissions_from_v2_admin_role_maps_hierarchically(self):
        self.assertEqual(user.permissions_from_me({"role": 30}), ["admin", "employee", "user"])

    def test_has_permission_uses_normalized_v2_permissions(self):
        me = {"role": 30}

        self.assertTrue(user.has_permission(me, "admin"))
        self.assertTrue(user.has_permission(me, "employee"))
        self.assertTrue(user.has_permission(me, "user"))
