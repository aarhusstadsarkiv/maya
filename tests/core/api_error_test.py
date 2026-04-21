import unittest

from maya.core.api_error import OpenAwsException, raise_openaws_exception


class TestApiError(unittest.TestCase):
    def test_v2_error_details_are_used_as_message(self):
        error = {"data": None, "error": "AuthenticationError", "error_details": "Invalid credentials"}

        with self.assertRaises(OpenAwsException) as context:
            raise_openaws_exception(401, error)

        self.assertEqual(str(context.exception), "Invalid credentials")
        self.assertEqual(context.exception.status_code, 401)
