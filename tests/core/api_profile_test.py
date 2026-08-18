from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from maya.core import api
from maya.core.api_auth import V1AuthAdapter, get_auth_adapter
from maya.core.api_request import get_auth_headers
from maya.core.api_user import V1UserAdapter, V2UserAdapter, get_user_adapter
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

        headers = get_auth_headers(request, {"Accept": "application/json"})

        self.assertEqual(headers["Authorization"], "Bearer token")
        self.assertNotIn("Cookie", headers)
        self.assertIsInstance(get_auth_adapter(), V1AuthAdapter)

    def test_v2_profile_still_uses_v1_authentication(self):
        settings["api_profile"] = "v2"
        request = SimpleNamespace(session={"access_token": "token"})

        headers = get_auth_headers(request, {"Accept": "application/json"})

        self.assertEqual(headers["Authorization"], "Bearer token")
        self.assertNotIn("Cookie", headers)
        self.assertIsInstance(get_auth_adapter(), V1AuthAdapter)
        self.assertEqual(get_auth_adapter().base_url, settings["api_base_url"])
        self.assertIsInstance(get_user_adapter(), V2UserAdapter)

    def test_v1_profile_uses_v1_user_adapter(self):
        settings["api_profile"] = "v1"
        self.assertIsInstance(get_user_adapter(), V1UserAdapter)

    def test_auth_logout_clears_v1_session_with_v1_profile(self):
        settings["api_profile"] = "v1"
        request = SimpleNamespace(session={"access_token": "token", "token_type": "bearer"})

        api.auth_logout(request)

        self.assertEqual(request.session, {})

    @patch("maya.core.api.get_auth_adapter")
    def test_auth_verify_post_delegates_to_auth_adapter(self, mock_get_auth_adapter):
        request = SimpleNamespace()
        adapter = SimpleNamespace(verify=AsyncMock())
        mock_get_auth_adapter.return_value = adapter

        import asyncio

        asyncio.run(api.auth_verify_post(request))

        adapter.verify.assert_awaited_once_with(request)

    @patch("maya.core.api.get_auth_adapter")
    def test_auth_request_verify_post_delegates_to_auth_adapter(self, mock_get_auth_adapter):
        request = SimpleNamespace()
        adapter = SimpleNamespace(request_verify=AsyncMock())
        mock_get_auth_adapter.return_value = adapter

        import asyncio

        asyncio.run(api.auth_request_verify_post(request))

        adapter.request_verify.assert_awaited_once_with(request)

    @patch("maya.core.api.get_user_adapter")
    def test_users_me_get_delegates_to_user_adapter(self, mock_get_user_adapter):
        request = SimpleNamespace()
        adapter = SimpleNamespace(me=AsyncMock(return_value={"email": "user@example.com"}))
        mock_get_user_adapter.return_value = adapter

        import asyncio

        me = asyncio.run(api.users_me_get(request))

        self.assertEqual(me, {"email": "user@example.com"})
        adapter.me.assert_awaited_once_with(request)

    @patch("maya.core.api.users_me_get", new_callable=AsyncMock)
    def test_me_verified_uses_v1_is_verified_flag(self, mock_users_me_get):
        settings["api_profile"] = "v1"
        request = SimpleNamespace()
        mock_users_me_get.return_value = {"email": "user@example.com", "is_verified": True}

        import asyncio

        verified = asyncio.run(api.me_verified(request))

        self.assertTrue(verified)

    @patch("maya.core.api.users_me_get", new_callable=AsyncMock)
    def test_me_verified_returns_false_when_v1_is_not_verified(self, mock_users_me_get):
        settings["api_profile"] = "v1"
        request = SimpleNamespace()
        mock_users_me_get.return_value = {"email": "user@example.com", "is_verified": False}

        import asyncio

        verified = asyncio.run(api.me_verified(request))

        self.assertFalse(verified)

    @patch("maya.core.api.users_me_get", new_callable=AsyncMock)
    def test_me_verified_uses_is_verified_flag_with_v2_api_profile(self, mock_users_me_get):
        settings["api_profile"] = "v2"
        request = SimpleNamespace()
        mock_users_me_get.return_value = {"email": "user@example.com", "is_verified": True}

        import asyncio

        verified = asyncio.run(api.me_verified(request))

        self.assertTrue(verified)
