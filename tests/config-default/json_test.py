"""
Test of JSON response
"""

from stadsarkiv_client.app import app
from stadsarkiv_client.core.logging import get_log
from starlette.testclient import TestClient
import unittest
import json

log = get_log()


class TestJSON(unittest.TestCase):
    def test_readingroom(self):
        client = TestClient(app)
        url = "/records/000309478/json/meta_data"
        response = client.get(url)
        json_response = response.json()
        json_expected = r"""
{
    "id": "000309478",
    "real_id": "309478",
    "allowed_by_ip": false,
    "permission_granted": false,
    "title": "Aarhus Vejviser 1997",
    "meta_title": "Aarhus Vejviser 1997",
    "meta_description": "Aarhus Vejviser 1997",
    "icon": {
        "icon": "article",
        "label": "Publikationer"
    },
    "copyright_id": 7,
    "legal_id": 1,
    "contractual_id": 5,
    "availability_id": 3,
    "usability_id": 4,
    "collection_id": 204,
    "content_types_label": "",
    "orderable": false,
    "resources": {
        "digital_size": "8469.218 MB",
        "mimetype": "application/zip",
        "checksum_algorithm": "MD5",
        "filename": "000309478.zip",
        "original_filename": "Aarhus Vejviser 1997.zip",
        "checksum": "3479d47c09595cb5854233681bc39ce7",
        "last_checksum_date": "2019-02-25 07:41:27",
        "type": "digital"
    },
    "is_representations_online": false,
    "is_downloadable": false,
    "has_active_order": false
}
    """
        # parse json
        json_expected = json.loads(json_expected)
        self.assertEqual(json_response, json_expected)

    def test_pdf(self):
        client = TestClient(app)
        url = "/records/000182391/json/meta_data"
        response = client.get(url)
        json_response = response.json()

        json_expected = r"""
{
    "id": "000182391",
    "real_id": "182391",
    "allowed_by_ip": false,
    "permission_granted": false,
    "title": "Salgsbrochure for kampagne Byg og bo i Aarhus.",
    "meta_title": "Salgsbrochure for kampagne Byg og bo i Aarhus.",
    "meta_description": "Salgsbrochure for kampagne Byg og bo i Aarhus.",
    "icon": {
        "icon": "description",
        "label": "Andet materiale"
    },
    "copyright_id": 4,
    "legal_id": 1,
    "contractual_id": 4,
    "availability_id": 4,
    "usability_id": 2,
    "collection_id": 194,
    "content_types_label": "",
    "orderable": false,
    "resources": {
        "Fysisk omfang": "1",
        "type": "analog",
        "storage_id": [
            "91+00239-1"
        ]
    },
    "is_representations_online": true,
    "record_type": "web_document",
    "representations": {
        "record_type": "web_document",
        "web_document_url": "https://acastorage.blob.core.windows.net/sam-access/000182391/000182391_c.pdf",
        "record_image": "https://acastorage.blob.core.windows.net/sam-access/000182391/000182391_m.jpg",
        "large_image": "https://acastorage.blob.core.windows.net/sam-access/000182391/000182391_m.jpg"
    },
    "portrait": "https://acastorage.blob.core.windows.net/sam-access/000182391/000182391_m.jpg",
    "is_downloadable": true,
    "has_active_order": false
}
"""

        # parse json
        json_expected = json.loads(json_expected)
        self.assertEqual(json_response, json_expected)

    def test_video(self):
        client = TestClient(app)
        url = "/records/000313141/json/meta_data"
        response = client.get(url)
        response_json = response.json()

        # Define expected JSON using a raw string to avoid issues with escape characters
        json_expected = r"""
{
    "id": "000313141",
    "real_id": "313141",
    "allowed_by_ip": false,
    "permission_granted": false,
    "title": "En køretur med sporvogn",
    "meta_title": "En køretur med sporvogn",
    "meta_description": "Filmens første 38 sekunder er fra Clemens Bro i 1902 \n\nDen 7. juli 1904 blev den første sporvognsrute indviet i Aarhus....",
    "icon": {
        "icon": "movie",
        "label": "Medieproduktioner"
    },
    "copyright_id": 2,
    "legal_id": 1,
    "contractual_id": 5,
    "availability_id": 4,
    "usability_id": 1,
    "collection_id": null,
    "content_types_label": "",
    "orderable": false,
    "resources": {
        "digital_size": "45.107 MB",
        "checksum_algorithm": "MD5",
        "filename": "000313141.mp4",
        "original_filename": "Århus med sporvogn 1904 I.mp4",
        "checksum": "15ac7fb0aed0dff914221ff71c988303",
        "last_checksum_date": "2019-01-30 10:17:10",
        "type": "digital"
    },
    "is_representations_online": true,
    "record_type": "video",
    "representations": {
        "record_type": "video",
        "record_file": "https://acastorage.blob.core.windows.net/sam-access/000313141/000313141.mp4",
        "vimeo_id": "49234056",
        "record_image": "https://acastorage.blob.core.windows.net/sam-access/000313141/000313141_m.jpg",
        "large_image": "https://acastorage.blob.core.windows.net/sam-access/000313141/000313141_m.jpg"
    },
    "portrait": "https://acastorage.blob.core.windows.net/sam-access/000313141/000313141_m.jpg",
    "is_downloadable": false,
    "has_active_order": false
}
        """

        json_expected = json.loads(json_expected)
        self.assertEqual(response_json, json_expected)
