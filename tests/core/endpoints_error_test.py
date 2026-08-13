import logging
import os
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

os.environ.setdefault("BASE_DIR", "sites/aarhus")

from maya.endpoints import endpoints_error


class FakeRequest:
    url = SimpleNamespace(path="/error/log")
    client = SimpleNamespace(host="203.0.113.4", port=0)

    def __init__(self, data):
        self.data = data

    async def json(self):
        return self.data


class EndpointsErrorTest(IsolatedAsyncioTestCase):
    async def test_error_log_post_uses_posted_level(self):
        request = FakeRequest(
            {
                "message": "Missing Image Error: /missing.jpg",
                "level": "WARNING",
                "error_code": 404,
                "error_type": "Missing Image Error",
                "error_url": "/records/1",
                "exception": "",
            }
        )

        with patch.object(endpoints_error, "log") as log:
            response = await endpoints_error.error_log_post(request)

        self.assertEqual(response.status_code, 200)
        log.log.assert_called_once_with(
            logging.WARNING,
            "Missing Image Error: /missing.jpg",
            extra={
                "client_ip": "203.0.113.4",
                "error_code": 404,
                "error_type": "Missing Image Error",
                "error_url": "/records/1",
                "exception": "",
            },
        )

    async def test_error_log_post_defaults_invalid_level_to_error(self):
        request = FakeRequest({"message": "Client message", "level": "INVALID"})

        with patch.object(endpoints_error, "log") as log:
            response = await endpoints_error.error_log_post(request)

        self.assertEqual(response.status_code, 200)
        log.log.assert_called_once_with(
            logging.ERROR,
            "Client message",
            extra={
                "client_ip": "203.0.113.4",
                "error_code": 500,
                "error_type": "Unknown Error",
                "error_url": "/error/log",
                "exception": "",
            },
        )

    async def test_error_log_post_includes_client_ip_when_payload_cannot_be_parsed(self):
        request = FakeRequest(None)

        async def invalid_json():
            raise ValueError("Invalid JSON")

        request.json = invalid_json

        with patch.object(endpoints_error, "log") as log:
            response = await endpoints_error.error_log_post(request)

        self.assertEqual(response.status_code, 200)
        log.error.assert_called_once_with(
            "Failed to parse error log",
            extra={
                "client_ip": "203.0.113.4",
                "error_code": 500,
                "error_type": "UnknownError",
                "error_url": "/error/log",
                "exception": "Invalid JSON",
            },
        )
