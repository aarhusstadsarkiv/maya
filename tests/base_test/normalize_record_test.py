import unittest
import os

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

from maya.records.normalize_record import RecordNormalizer


class TestNormalizeRecord(unittest.TestCase):
    def test_normalize_series_encodes_only_series_value(self):
        record = {
            "collection": {"id": 1},
            "series": [
                {"label": "Emnesedler"},
                {"label": "Biblioteket"},
            ],
        }

        normalized = RecordNormalizer()._normalize_series(record)

        self.assertEqual(
            normalized["series"][0][1]["search_query"],
            "/search?collection=1&series=Emnesedler/Biblioteket",
        )


if __name__ == "__main__":
    unittest.main()
