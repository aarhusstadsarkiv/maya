import json
import logging
from unittest import TestCase

from maya.core.logging_context import reset_client_ip, set_client_ip
from maya.core.logging_handlers import JsonFormatter


class JsonFormatterTest(TestCase):
    def test_includes_request_client_ip(self):
        token = set_client_ip("203.0.113.4")
        try:
            output = JsonFormatter().format(logging.LogRecord("main", logging.INFO, "", 0, "Test", (), None))
        finally:
            reset_client_ip(token)

        self.assertEqual(json.loads(output)["client_ip"], "203.0.113.4")

    def test_omits_client_ip_outside_request(self):
        output = JsonFormatter().format(logging.LogRecord("main", logging.INFO, "", 0, "Test", (), None))

        self.assertNotIn("client_ip", json.loads(output))

    def test_explicit_client_ip_works_outside_request_context(self):
        record = logging.LogRecord("main", logging.ERROR, "", 0, "Test", (), None)
        record.client_ip = "203.0.113.5"

        output = JsonFormatter().format(record)

        self.assertEqual(json.loads(output)["client_ip"], "203.0.113.5")
