import logging
import os
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

os.environ.setdefault("BASE_DIR", "sites/aarhus")

from maya.endpoints import endpoints_error


class FakeRequest:
    url = SimpleNamespace(path="/error/log")

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
                "error_code": 500,
                "error_type": "Unknown Error",
                "error_url": "/error/log",
                "exception": "",
            },
        )
