from maya.core.dynamic_settings import init_settings
from maya.app import app
from maya.core.logging import get_log
from starlette.testclient import TestClient
import unittest

init_settings()
log = get_log()

valid_user = "dennis.iversen+h@gmail.com"
valid_password = "testtest"

invalid_user = "bad.mail@test.com"
invalid_password = "bad_password"

correct_login = {
    "username": valid_user,
    "password": valid_password,
}
incorrect_login = {"username": invalid_user, "password": invalid_password}
headers = {"origin": "http://testserver"}
"""
User already exists. At some point we should test with a user that does not exist.
Before that is possible we should be allowed to delete a user from the database.
So some of these tests are a bit shallow.
"""


class TestAuth(unittest.TestCase):
    def test_login_get(self):
        client = TestClient(app)
        response = client.get("/auth/login")
        self.assertEqual(response.status_code, 200)

    def test_login_post_correct(self):
        client = TestClient(app, headers=headers)

        # Sometimes login credential uses "email" and sometimes "username" ... this is a bit confusing
        login = {"email": valid_user, "password": valid_password}
        response = client.post("/auth/login", data=login, follow_redirects=True)  # type: ignore
        expect_json = {"error": False, "redirect": "/search"}
        log.debug(f"Response JSON: {response.json()}")
        self.assertEqual(response.json(), expect_json)

    def test_login_post_incorrect(self):

        client = TestClient(app, headers=headers)
        response = client.post("/auth/login", data=incorrect_login, follow_redirects=True)  # type: ignore
        expect_json = {"message": "Email eller password er ikke korrekt.", "error": True}
        self.assertEqual(response.json(), expect_json)

    def test_logout_get(self):
        client = TestClient(app)
        response = client.get("/auth/logout", follow_redirects=True)
        self.assertEqual(response.url, "http://testserver/")

    def test_register_get(self):
        client = TestClient(app)
        response = client.get("/auth/register")
        self.assertEqual(response.status_code, 200)

    def test_register_post(self):
        client = TestClient(app, headers=headers)
        data = {
            "display_name": "test",
            "email": correct_login["username"],
            "password": correct_login["password"],
            "password_2": correct_login["password"],
        }
        response = client.post("/auth/register", data=data, follow_redirects=True)  # type: ignore

        reponse_urls = ["http://testserver/auth/login", "http://testserver/auth/register"]
        self.assertIn(response.url, reponse_urls)

    def test_forgot_password_get(self):
        client = TestClient(app)
        response = client.get("/auth/forgot-password")
        self.assertEqual(response.status_code, 200)

    # def test_forgot_password_post(self):
    #     client = TestClient(app)
    #     response = client.post("/auth/forgot-password", data={"email": valid_user}, follow_redirects=True)  # type: ignore
    #     self.assertEqual(response.url, "http://testserver/auth/forgot-password") # type: ignore

    def test_reset_password_get(self):
        client = TestClient(app)
        response = client.get("/auth/reset-password/fake-token")
        self.assertEqual(response.status_code, 200)

    def test_reset_password_post(self):
        client = TestClient(app, headers=headers)
        response = client.post(
            "/auth/reset-password/fake-token", data={"password": valid_password, "password_2": valid_password}, follow_redirects=True
        )
        self.assertEqual(response.url, "http://testserver/auth/reset-password/fake-token")

    def test_verify_get(self):
        client = TestClient(app)
        response = client.get("/auth/verify/fake-token")
        self.assertEqual(response.url, "http://testserver/auth/login")

    def test_me_loggedin_get(self):
        client = TestClient(app, headers=headers)
        response = client.post(
            "/auth/login",
            data=correct_login,
        )  # type: ignore
        response = client.get("/auth/me")
        self.assertEqual(response.status_code, 200)

    def test_me_not_logged_in_get(self):
        client = TestClient(app)
        response = client.get("/auth/me", follow_redirects=True)
        self.assertEqual(response.url, "http://testserver/auth/login?next=/auth/me")
