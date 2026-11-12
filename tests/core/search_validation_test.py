import os
import json
from base64 import b64decode, b64encode
from copy import deepcopy
from http.cookies import SimpleCookie
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qsl, urlencode

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

import httpx2
from bs4 import BeautifulSoup
from itsdangerous import TimestampSigner
from starlette.requests import Request

from maya.app import app
from maya.core import api, api_client, exception_handlers
from maya.core.dynamic_settings import settings
from maya.core.search_validation import SearchQueryError
from maya.core.search_challenge import SearchChallengeMiddleware
from maya.core.sitemap import _parse_items
from maya.endpoints import endpoints_search


class SearchValidationTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend_requests = []
        # Exercise search handling as a browser that already passed admission.
        self.enterContext(patch.object(SearchChallengeMiddleware, "clearance_rejection_reason", return_value=None))

        def upstream(request):
            self.backend_requests.append(request)
            return httpx2.Response(
                200,
                json={
                    "result": [],
                    "total": 0,
                    "start": 0,
                    "size": 20,
                    "active_facets": {},
                    "facets_resolved": {"collectors": {"107438": {"display_label": "Aarhus Teater (1900-)"}}},
                },
            )

        backend = await self.enterAsyncContext(httpx2.AsyncClient(transport=httpx2.MockTransport(upstream)))
        self.enterContext(patch.object(api_client, "_shared_client", backend))
        self.log = self.enterContext(patch.object(exception_handlers, "log"))
        self.client = await self.enterAsyncContext(
            httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="https://aarhus.local")
        )

    def forwarded_items(self):
        self.assertEqual(len(self.backend_requests), 1)
        return parse_qsl(self.backend_requests[0].url.params["params"], keep_blank_values=True)

    async def test_malformed_queries_never_reach_backend_on_any_search_route(self):
        queries = [
            "locations=51097size=20sort=date_fromview=listdirection=asc",
            "people=123%20OR%201%3D1",
            "-subjects=44%27%20ORDER%20BY%201000",
            "subjects=6%0Atype%20win.ini",
            "content_types=1.5",
            "collection=-1",
            "availability=%2B4",
            "usability=%D9%A1",  # Non-ASCII digit.
            "registration_id=abc",
            "subjects=bad&subjects=44",  # Validate every occurrence.
            "direction=asc%20UNION%20ALL%20SELECT",
            "direction=asc&direction=invalid",
            "sort=invalid",
            "size=zero",
            "size=0",
            "size=10001",
            "size=" + "9" * 5000,
            "start=" + "0" * 5000,
            "start=-1",
            "start=10000",
            "start=1.5",
            "date_from=20260230",
            "date_to=20261301",
            "date_from=2026-01-01",
            "date_to=20260101%20OR%201%3D1",
        ]
        for path in ("/search?", "/search/json?", "/search?view=ids&"):
            for query in queries:
                with self.subTest(path=path, query=query[:100]):
                    self.backend_requests.clear()
                    response = await self.client.get(path + query)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(self.backend_requests, [])
                    self.assertIn("no-store", response.headers["cache-control"])
                    if "json" in path or "ids" in path:
                        self.assertTrue(response.json()["error"])
                        self.assertIn("Invalid search query", response.json()["message"])
                    else:
                        self.assertIn("text/html", response.headers["content-type"])
                        self.assertIn('class="page-error"', response.text)
        self.log.exception.assert_not_called()
        self.log.warning.assert_called()

    async def test_styled_error_is_translated_without_api_calls_even_with_a_session(self):
        session = TimestampSigner(settings["session_secret"]).sign(b64encode(json.dumps({"access_token": "test-token"}).encode())).decode()
        self.client.cookies.set(settings["cookie"]["name"], session)
        original_menus = deepcopy((settings["main_menu_system"], settings["main_menu_top"]))
        for language, heading, message in (
            ("da", "400 Ugyldig søgning", "Linket indeholder ugyldige søgeoplysninger."),
            ("en", "400 Invalid search", "The link contains invalid search information."),
        ):
            for debug in (False, True):
                with self.subTest(language=language, debug=debug), patch.dict(settings, language=language, debug=debug):
                    response = await self.client.get("/search?content_types=45abc")
                    self.assertEqual(response.status_code, 400)
                    soup = BeautifulSoup(response.text, "html.parser")
                    self.assertEqual(soup.select_one(".main-title").get_text(strip=True), heading)
                    self.assertIn(message, soup.select_one("main").get_text())
                    self.assertIsNotNone(soup.select_one("header .logo"))
                    self.assertTrue(any(link["href"].endswith(("/search", "/search?")) for link in soup.select("header a[href]")))
                    self.assertFalse(soup.select("main button, main a, main pre"))
                    self.assertNotIn("must contain only digits", response.text)
                    self.assertEqual(self.backend_requests, [])
        self.assertEqual((settings["main_menu_system"], settings["main_menu_top"]), original_menus)
        self.assertIn("content_types", self.log.warning.call_args.kwargs["extra"]["exception"])

    async def test_invalid_view_and_regular_page_size_are_rejected(self):
        for query in ("view=unknown", "size=1001", "view=ids&view=unknown"):
            response = await self.client.get("/search?" + query)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.backend_requests, [])

    async def test_valid_filters_and_free_text_still_search(self):
        items = [
            ("subjects", "17"),
            ("subjects", "44"),
            ("-subjects", "52"),
            ("locations", "000123"),
            ("collection", "194"),
            ("series", "Aarhus Havn/Økonomi & regnskab"),
            ("collection_tags", "O'Brien + søn"),
            ("q", 'SELECT "Aarhus" OR havn*'),
            ("date_from", "19600229"),
            ("date_to", "19701231"),
            ("direction", "desc"),
            ("sort", "date_to"),
            ("size", "50"),
            ("start", "20"),
        ]
        for path in ("/search", "/search/json"):
            with self.subTest(path=path):
                self.backend_requests.clear()
                response = await self.client.get(path + "?" + urlencode(items))
                self.assertEqual(response.status_code, 200)
                forwarded = self.forwarded_items()
                for key, value in items:
                    self.assertIn((key, "123" if key == "locations" else value), forwarded)

    async def test_empty_filters_and_tracking_parameters_remain_supported(self):
        response = await self.client.get("/search/json?locations=&date_from=&q=&utm_source=newsletter&unknown=value")
        self.assertEqual(response.status_code, 200)
        forwarded = self.forwarded_items()
        self.assertFalse({"locations", "date_from", "utm_source", "unknown"} & {key for key, value in forwarded})

    async def test_single_character_query_is_removed_from_api_search(self):
        response = await self.client.get("/search/json?q=a")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([value for key, value in self.forwarded_items() if key == "q"], [""])

    async def test_ids_mode_preserves_cursor_text_and_repeated_filters(self):
        items = [
            ("view", "ids"),
            ("size", "10000"),
            ("cursor", "00Ab+C/d=="),
            ("subjects", "17"),
            ("subjects", "44"),
            ("-subjects", "52"),
            ("q", "Aarhus & direction=unexpected + havn"),
        ]
        response = await self.client.get("/search?" + urlencode(items))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.forwarded_items(), items)

    async def test_sitemap_batch_size_remains_supported(self):
        items = _parse_items("subjects=17")
        await api.proxies_view_ids_from_list(items)
        self.assertEqual(self.forwarded_items(), items)

    async def test_direct_adapters_reject_invalid_values(self):
        request = Request({"type": "http", "session": {}})
        for adapter, args in (
            (api.proxies_records, (request,)),
            (api.proxies_records_from_list, (request,)),
            (api.proxies_view_ids_from_list, ()),
        ):
            with self.subTest(adapter=adapter.__name__):
                with self.assertRaises(SearchQueryError):
                    await adapter(*args, [("people", "123 OR 1=1")])
                self.assertEqual(self.backend_requests, [])

    async def test_hook_values_are_validated_before_api_call(self):
        hooks = endpoints_search.get_hooks(Request({"type": "http"}))
        with patch.object(type(hooks), "before_get_search", new=AsyncMock(return_value=[("locations", "invalid")])):
            response = await self.client.get("/search/json?locations=123")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.backend_requests, [])

    async def test_last_result_window_is_clamped_to_remaining_records(self):
        response = await self.client.get("/search/json?start=9999&size=20")
        self.assertEqual(response.status_code, 200)
        forwarded = self.forwarded_items()
        self.assertIn(("start", "9999"), forwarded)
        self.assertIn(("size", "1"), forwarded)

    async def test_padded_collector_resolves_label_links_cookies_and_navigation(self):
        contexts = []
        for collector_id in ("107438", "000107438"):
            self.backend_requests.clear()
            response = await self.client.get(f"/search/json?collectors={collector_id}")
            self.assertEqual(response.status_code, 200)
            context = response.json()
            contexts.append(context)
            self.assertIn(("collectors", "107438"), self.forwarded_items())
            selected = next(item for item in context["facets_filters"] if item["query_name"] == "collectors")
            self.assertEqual(selected["label"], "Arkivskaber Aarhus Teater (1900-)")
            self.assertEqual(selected["entity_url"], "/collectors/107438")
            self.assertNotIn(("collectors", "107438"), parse_qsl(selected["remove_link"]))
            self.assertIn(("-collectors", "107438"), parse_qsl(selected["invert_link"]))

            cookies = SimpleCookie()
            for header in response.headers.get_list("set-cookie"):
                cookies.load(header)
            search_cookie = json.loads(cookies["search"].value)
            self.assertIn(["collectors", "107438"], search_cookie["query_params"])
            self.assertIn(("collectors", "107438"), parse_qsl(search_cookie["search_query_str"]))
            session_cookie = cookies[settings["cookie"]["name"]].value
            session = json.loads(b64decode(TimestampSigner(settings["session_secret"]).unsign(session_cookie)))
            self.assertIn(["collectors", "107438"], session["record_navigation_cache"]["query_params"])
        self.assertEqual(contexts[0], contexts[1])
        response = await self.client.get("/search?collectors=000107438")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Arkivskaber Aarhus Teater (1900-)", response.text)

    async def test_negated_padded_collector_has_resolved_label_and_working_links(self):
        response = await self.client.get("/search/json?-collectors=000107438")
        self.assertEqual(response.status_code, 200)
        selected = next(item for item in response.json()["facets_filters"] if item["query_name"] == "collectors")
        self.assertEqual(selected["label"], "Arkivskaber Aarhus Teater (1900-)")
        self.assertTrue(selected["negated"])
        self.assertIn(("-collectors", "107438"), self.forwarded_items())
        self.assertNotIn(("-collectors", "107438"), parse_qsl(selected["remove_link"]))
        self.assertIn(("collectors", "107438"), parse_qsl(selected["invert_link"]))

    async def test_text_leading_zeroes_survive_both_search_paths(self):
        items = [("q", "007"), ("collection", "000194"), ("series", "001/Økonomi & regnskab"), ("collection_tags", "001")]
        for path in ("/search/json?", "/search?view=ids&"):
            self.backend_requests.clear()
            response = await self.client.get(path + urlencode(items))
            self.assertEqual(response.status_code, 200)
            for key, value in items:
                self.assertIn((key, "194" if key == "collection" else value), self.forwarded_items())
            if "json" in path:
                self.assertEqual(response.json()["q"], "007")
                saved = parse_qsl(response.json()["search_query_str"])
                self.assertIn(("q", "007"), saved)
                self.assertIn(("collection_tags", "001"), saved)

    async def test_conflicting_singletons_are_rejected_before_hooks_or_api(self):
        queries = ("size=20&size=100", "collection=1&collection=2", "q=foo&q=bar", "direction=asc&direction=desc")
        hooks = endpoints_search.get_hooks(Request({"type": "http"}))
        with patch.object(type(hooks), "before_get_search", new=AsyncMock()) as before:
            for path in ("/search?", "/search/json?", "/search?view=ids&"):
                for query in queries:
                    with self.subTest(path=path, query=query):
                        response = await self.client.get(path + query)
                        self.assertEqual(response.status_code, 400)
            before.assert_not_awaited()
        self.assertEqual(self.backend_requests, [])

    async def test_equivalent_duplicates_collapse_but_distinct_filters_remain(self):
        response = await self.client.get(
            "/search/json?collection=000194&collection=194&subjects=017&subjects=17&subjects=44&size=020&size=20"
        )
        self.assertEqual(response.status_code, 200)
        items = self.forwarded_items()
        self.assertEqual([value for key, value in items if key == "collection"], ["194"])
        self.assertEqual([value for key, value in items if key == "subjects"], ["17", "44"])
        self.assertEqual([value for key, value in items if key == "size"], ["20"])

    async def test_hooks_receive_normalized_ids_and_output_is_normalized_again(self):
        hooks = endpoints_search.get_hooks(Request({"type": "http"}))

        async def before(query_params):
            self.assertIn(("collectors", "107438"), query_params)
            return [(key, "000107438" if key == "collectors" else value) for key, value in query_params]

        with patch.object(type(hooks), "before_get_search", new=AsyncMock(side_effect=before)):
            for path in ("/search/json?", "/search?view=ids&"):
                self.backend_requests.clear()
                response = await self.client.get(path + "collectors=000107438")
                self.assertEqual(response.status_code, 200)
                self.assertIn(("collectors", "107438"), self.forwarded_items())
                if "json" in path:
                    self.assertIn(["collectors", "107438"], response.json()["query_params_before_search"])

    async def test_after_hook_cannot_mutate_parameters_saved_for_navigation(self):
        hooks = endpoints_search.get_hooks(Request({"type": "http"}))

        async def after(query_params):
            query_params.remove(("collectors", "107438"))
            return query_params

        with patch.object(type(hooks), "after_get_search", new=AsyncMock(side_effect=after)):
            response = await self.client.get("/search/json?collectors=000107438")
        self.assertEqual(response.status_code, 200)
        self.assertIn(["collectors", "107438"], response.json()["query_params_before_search"])
        self.assertNotIn(["collectors", "107438"], response.json()["query_params"])

    async def test_html_escaped_keys_are_normalized_before_validation(self):
        response = await self.client.get("/search/json?q=teater&amp;collectors=000107438")
        self.assertEqual(response.status_code, 200)
        self.assertIn(("collectors", "107438"), self.forwarded_items())
        self.backend_requests.clear()
        response = await self.client.get("/search/json?q=teater&amp;collectors=invalid")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.backend_requests, [])

    async def test_hook_options_drive_api_and_display_using_the_same_hook_instance(self):
        hooks = endpoints_search.get_hooks(Request({"type": "http"}))

        async def before(hook, query_params):
            hook.search_prepared = True
            items = [(key, value) for key, value in query_params if key not in {"size", "start", "date_from"}]
            return items + [("size", "050"), ("start", "040"), ("date_from", "19000101")]

        async def after(hook, query_params):
            self.assertTrue(hook.search_prepared)
            return query_params

        with patch.object(type(hooks), "before_get_search", before), patch.object(type(hooks), "after_get_search", after):
            response = await self.client.get("/search/json?size=20&date_from=20000101")
        self.assertEqual(response.status_code, 200)
        context = response.json()
        self.assertEqual(context["size"], "50")
        self.assertEqual(context["pagination_data"]["size"], 50)
        self.assertEqual(context["pagination_data"]["start"], 40)
        self.assertEqual(context["dates"]["from_year"], "1900")
        self.assertIn(("size", "50"), self.forwarded_items())
        self.assertIn(("date_from", "19000101"), self.forwarded_items())

    async def test_html_escaped_ids_view_uses_ids_preparation(self):
        response = await self.client.get("/search?collectors=000107438&amp;view=ids&size=10000")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status_code"], 0)
        self.assertIn(("collectors", "107438"), self.forwarded_items())
        self.assertIn(("size", "10000"), self.forwarded_items())
