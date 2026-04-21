from types import SimpleNamespace
import unittest

from maya.core import api
from maya.core.api_auth import V1AuthAdapter, V2AuthAdapter, get_auth_adapter
from maya.core.dynamic_settings import settings


class TestApiProfile(unittest.TestCase):
    def setUp(self):
        self.original_api_profile = settings.get("api_profile")

    def tearDown(self):
        if self.original_api_profile is None:
            settings.pop("api_profile", None)
        else:
            settings["api_profile"] = self.original_api_profile

    def test_v1_profile_uses_jwt_authorization_header(self):
        settings["api_profile"] = "v1"
        request = SimpleNamespace(session={"access_token": "token"})

        headers = api._get_jwt_headers(request, {"Accept": "application/json"})

        self.assertEqual(headers["Authorization"], "Bearer token")
        self.assertNotIn("Cookie", headers)
        self.assertIsInstance(get_auth_adapter(), V1AuthAdapter)

    def test_v2_profile_uses_session_cookie_header(self):
        settings["api_profile"] = "v2"
        request = SimpleNamespace(session={"session": "s1", "client": "c1", "domain": "d1"})

        headers = api._get_jwt_headers(request, {"Accept": "application/json"})

        self.assertEqual(headers["Cookie"], "session=s1; client=c1; domain=d1")
        self.assertNotIn("Authorization", headers)
        self.assertIsInstance(get_auth_adapter(), V2AuthAdapter)
