"""
Test of JSON response
"""

from stadsarkiv_client.app import app
from stadsarkiv_client.core.logging import get_log
from starlette.testclient import TestClient
import unittest
import json
import os

log = get_log()


class TestJSON(unittest.TestCase):

    def test_sejrs_sedler(self):

        os.environ["CONFIG_DIR"] = "example-config-aarhus"

        self.maxDiff = None
        client = TestClient(app)
        url = "/records/000109399/json/meta_data"

        response = client.get(url)
        response_json = response.json()
        json_expected = r"""
{
    "id": "000109399",
    "real_id": "109399",
    "allowed_by_ip": false,
    "permission_granted": false,
    "title": "",
    "meta_title": "om Badstuegade og Badstuerne under Kong Hans, i hvis...",
    "meta_description": "om Badstuegade og Badstuerne under Kong Hans, i hvis Regnskabsbøger staaer anført i 1487: \"28 Skilling for det tyske...",
    "icon": {
        "icon": "description",
        "label": "Manuskripter"
    },
    "copyright_id": 1,
    "legal_id": 1,
    "contractual_id": 5,
    "availability_id": 4,
    "usability_id": 1,
    "collection_id": 1,
    "content_types_label": "",
    "orderable": false,
    "resources": {},
    "is_representations_online": true,
    "record_type": "sejrs_sedler",
    "is_downloadable": false,
    "representation_text": "om Badstuegade og Badstuerne under Kong Hans, i hvis Regnskabsbøger staaer anført i 1487: \"28 Skilling for det tyske Øl, der var uddrukken i Badstuen i Aar., da Kongen badede der\" og lidt senere \"Eiler Brydske har udlagt 3 Mark i Badstuen til Kongens Behag\" - Badstuerne blev helt ophævede i Danmark i 16. Aarhundrede fordi Gejstligheden mente de befordrede Epidemi.",
    "has_active_order": false
}
"""

        json_expected = json.loads(json_expected)
        self.assertEqual(response_json, json_expected)
