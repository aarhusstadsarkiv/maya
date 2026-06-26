import os
import unittest
from unittest.mock import ANY, patch

os.environ.setdefault("BASE_DIR", os.getcwd())

from maya.core.relations import MISSING_ENTITY, format_relations, sort_data


class TestRelations(unittest.TestCase):
    @patch("maya.core.relations.log")
    def test_format_relations_replaces_missing_rel_label(self, mock_log):
        relations = [{"id": "100", "rel_id": "200", "rel_label": None}]

        formatted = format_relations("events", relations, "https://example.test/events/1")

        self.assertEqual(formatted[1]["data"][0]["rel_label"], MISSING_ENTITY)
        mock_log.error.assert_called_once_with(
            ANY,
            extra={
                "error_code": 499,
                "error_type": "MissingRelationValue",
                "error_url": "https://example.test/events/1",
            },
        )

    @patch("maya.core.relations.log")
    def test_sort_data_replaces_missing_display_label(self, mock_log):
        data = [
            {
                "label": "Produktion",
                "data": [
                    {"display_label": "Hamlet 1999", "id": "1999"},
                    {"display_label": None, "id": "100", "rel_id": "200"},
                ],
            }
        ]

        sorted_data = sort_data(data, "display_label", "https://example.test/people/1")

        self.assertEqual([item["display_label"] for item in sorted_data[0]["data"]], ["Hamlet 1999", MISSING_ENTITY])
        mock_log.error.assert_called_once_with(
            ANY,
            extra={
                "error_code": 499,
                "error_type": "MissingRelationValue",
                "error_url": "https://example.test/people/1",
            },
        )


if __name__ == "__main__":
    unittest.main()
