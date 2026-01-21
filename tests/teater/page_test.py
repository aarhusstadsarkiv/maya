"""
Test of some modified resources on "teater" client.
"""

from maya.app import app
from maya.core.logging import get_log
from starlette.testclient import TestClient
import unittest

log = get_log()


class TestPages(unittest.TestCase):
    def test_events(self):
        client = TestClient(app)
        response = client.get("/events/000112281")
        self.assertEqual(response.status_code, 200)

    def test_people(self):
        client = TestClient(app)
        response = client.get("/people/000116693")
        self.assertEqual(response.status_code, 200)

    def test_record(self):
        """This record page has no 'people' key in the record_and_types dict."""
        client = TestClient(app)
        response = client.get("/records/000497604")
        self.assertEqual(response.status_code, 200)
