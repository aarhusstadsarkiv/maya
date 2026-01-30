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
    def test_readingroom(self):
        client = TestClient(app)
        url = "/records/000309478/json/meta_data"
        response = client.get(url)
        json_response = response.json()
        json_expected = r"""
{
    "id": "000309478",
    "real_id": "309478",
    "_allowed_by_ip": false,
    "_permission_granted": false,
    "title": "Aarhus Vejviser 1997",
    "meta_title": "Aarhus Vejviser 1997",
    "summary": "",
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
    "orderable": true,
    "orderable_online": true,
    "orderable_by_form": false,
    "order_message": "",
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
    "record_type": "icon",
    "is_downloadable": false
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
    "_allowed_by_ip": false,
    "_permission_granted": false,
    "title": "Salgsbrochure for kampagne Byg og bo i Aarhus.",
    "meta_title": "Salgsbrochure for kampagne Byg og bo i Aarhus.",
    "summary": "",
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
    "orderable_online": false,
    "orderable_by_form": false,
    "order_message": "",
    "resources": {
        "Fysisk omfang": "1",
        "type": "analog",
        "storage_id": [
            "91+00239-1"
        ]
    },
    "record_type": "web_document",
    "representations": {
        "record_type": "web_document",
        "web_document_url": "https://acastorage.blob.core.windows.net/sam-access/000182391/000182391_c.pdf",
        "record_image": "https://acastorage.blob.core.windows.net/sam-access/000182391/000182391_m.jpg",
        "large_image": "https://acastorage.blob.core.windows.net/sam-access/000182391/000182391_m.jpg"
    },
    "portrait": "https://acastorage.blob.core.windows.net/sam-access/000182391/000182391_m.jpg",
    "is_representations_online": true,
    "is_downloadable": false
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
    "_allowed_by_ip": false,
    "_permission_granted": false,
    "title": "En køretur med sporvogn",
    "meta_title": "En køretur med sporvogn",
    "summary": "Filmens første 38 sekunder er fra Clemens Bro i 1902 \n\nDen 7. juli 1904 blev den første sporvognsrute indviet i Aarhus. Ruten gik fra Dalgas Avenue gennem Hans Broges Gade, Skt. Pauls Kirkeplads, M.P. Bruuns Gade forbi hovedbanegården, videre ad den velkendte omnibusrute til Østbanetorvet og derfra til Skovvejen og til sidst Trøjborgvej. Længe var dette den eneste rute, men da kommunen overtog driften blev den eksisterende rute i 1930 udvidet og en ny blev tilføjet. Sporvognskørslen i Aarhus fortsatte op til 1971.\n\nFilmene viser sporvognene køre gennem Aarhus i 1905.",
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
    "orderable_online": false,
    "orderable_by_form": false,
    "order_message": "",
    "resources": {
        "digital_size": "45.107 MB",
        "checksum_algorithm": "MD5",
        "filename": "000313141.mp4",
        "original_filename": "Århus med sporvogn 1904 I.mp4",
        "checksum": "15ac7fb0aed0dff914221ff71c988303",
        "last_checksum_date": "2019-01-30 10:17:10",
        "type": "digital"
    },
    "record_type": "video",
    "representations": {
        "record_type": "video",
        "record_file": "https://acastorage.blob.core.windows.net/sam-access/000313141/000313141.mp4",
        "vimeo_id": "49234056",
        "record_image": "https://acastorage.blob.core.windows.net/sam-access/000313141/000313141_m.jpg",
        "large_image": "https://acastorage.blob.core.windows.net/sam-access/000313141/000313141_m.jpg"
    },
    "portrait": "https://acastorage.blob.core.windows.net/sam-access/000313141/000313141_m.jpg",
    "is_representations_online": true,
    "is_downloadable": false
}
        """

        json_expected = json.loads(json_expected)
        self.assertEqual(response_json, json_expected)

    def test_orderable_by_form(self):
        client = TestClient(app)
        url = "/records/000472462/json/meta_data"
        response = client.get(url)
        response_json = response.json()

        # Define expected JSON using a raw string to avoid issues with escape characters
        json_expected = r"""
{
    "id": "000472462",
    "real_id": "472462",
    "_allowed_by_ip": false,
    "_permission_granted": false,
    "title": "Børneværnsudvalget. Dagsordener, udvalgsmøder",
    "meta_title": "Børneværnsudvalget. Dagsordener, udvalgsmøder",
    "summary": "",
    "meta_description": "Børneværnsudvalget. Dagsordener, udvalgsmøder",
    "icon": {
        "icon": "folder_open",
        "label": "Kommunale sager og planer"
    },
    "copyright_id": 1,
    "legal_id": 2,
    "contractual_id": 2,
    "availability_id": 2,
    "usability_id": 4,
    "collection_id": 194,
    "content_types_label": "",
    "orderable": true,
    "orderable_online": false,
    "orderable_by_form": true,
    "order_message": "",
    "resources": {
        "barcode": "8037309941",
        "type": "analog",
        "location": "Reol 43/fag 2/hylde 1",
        "storage_id": [
            "91+01295-98"
        ]
    },
    "record_type": "icon",
    "is_downloadable": false
}
        """

        json_expected = json.loads(json_expected)
        self.assertEqual(response_json, json_expected)
