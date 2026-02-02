"""
Test of JSON response
"""

from maya.app import app
from maya.core.logging import get_log
from starlette.testclient import TestClient
import unittest
import json

log = get_log()


class TestJSON(unittest.TestCase):

    def test_sejrs_sedler(self):

        self.maxDiff = None
        client = TestClient(app)
        url = "/records/000109399/json/meta_data"

        response = client.get(url)
        response_json = response.json()
        json_expected = r"""
{
    "id": "000109399",
    "real_id": "109399",
    "_allowed_by_ip": false,
    "_permission_granted": false,
    "title": "",
    "meta_title": "om Badstuegade og Badstuerne under Kong Hans, i hvis...",
    "summary": "om Badstuegade og Badstuerne under Kong Hans, i hvis Regnskabsbøger staaer anført i 1487: \"28 Skilling for det tyske Øl, der var uddrukken i Badstuen i Aar., da Kongen badede der\" og lidt senere \"Eiler Brydske har udlagt 3 Mark i Badstuen til Kongens Behag\" - Badstuerne blev helt ophævede i Danmark i 16. Aarhundrede fordi Gejstligheden mente de befordrede Epidemi.",
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
    "orderable_online": false,
    "orderable_by_form": false,
    "order_message": "<p>Materialet kan bestilles hjem til læsesalen.<br> <a href='/auth/login?next=/records/000109399'>Log ind</a> eller <a href='/auth/register'>opret bruger</a> for at bestille.</p>",
    "resources": {},
    "record_type": "sejrs_sedler",
    "representations": {},
    "is_representations_online": true,
    "is_downloadable": false,
    "representation_text": "om Badstuegade og Badstuerne under Kong Hans, i hvis Regnskabsbøger staaer anført i 1487: \"28 Skilling for det tyske Øl, der var uddrukken i Badstuen i Aar., da Kongen badede der\" og lidt senere \"Eiler Brydske har udlagt 3 Mark i Badstuen til Kongens Behag\" - Badstuerne blev helt ophævede i Danmark i 16. Aarhundrede fordi Gejstligheden mente de befordrede Epidemi."
}
"""

        json_expected = json.loads(json_expected)
        self.assertEqual(response_json, json_expected)
