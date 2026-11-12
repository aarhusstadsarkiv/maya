import os
from unittest import IsolatedAsyncioTestCase, TestCase
from urllib.parse import parse_qsl

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

from starlette.requests import Request

from maya.core.hooks_spec import HooksSpec
from maya.core.query import get_str_from_list
from maya.core.search_query import get_api_search_query, prepare_search_query, prepare_search_request
from maya.core.search_validation import SearchQueryError
from sites.simple.hooks import Hooks as SimpleHooks


class SearchQueryTest(TestCase):
    def test_encoder_preserves_values_and_escapes_both_names_and_values(self):
        pairs = [("q", "007 & A+B=1"), ("series", "001/Økonomi"), ("collectors", "000107438"), ("a&b", "x"), ("q", "")]
        self.assertEqual(parse_qsl(get_str_from_list(pairs), keep_blank_values=True), pairs)
        self.assertTrue(get_str_from_list(pairs).endswith("&"))
        self.assertEqual(get_str_from_list([]), "")

    def test_encoder_filtering_does_not_change_values_or_inputs(self):
        pairs = [("q", "007"), ("start", "00020"), ("subjects", "0017"), ("subjects", "0044")]
        original = pairs.copy()
        encoded = get_str_from_list(pairs, accept_keys=["q", "subjects", "start"], remove_keys=["start"])
        self.assertEqual(parse_qsl(encoded), [pairs[0], pairs[2], pairs[3]])
        self.assertEqual(pairs, original)

    def test_preparation_is_idempotent_and_preserves_zero_text_and_dates(self):
        pairs = [("collectors", "000"), ("collectors", "0"), ("-collectors", "000107438"), ("date_from", "00010101"), ("q", "007")]
        original = pairs.copy()
        prepared = prepare_search_query(pairs)
        self.assertEqual(prepared, [("collectors", "0"), ("-collectors", "107438"), ("date_from", "00010101"), ("q", "007")])
        self.assertEqual(prepare_search_query(prepared), prepared)
        self.assertEqual(pairs, original)

    def test_api_adjustments_leave_user_search_state_unchanged(self):
        pairs = [("collectors", "107438"), ("size", "20"), ("start", "9999"), ("q", "a")]
        original = pairs.copy()
        api_items = get_api_search_query(pairs)
        self.assertIn(("size", "1"), api_items)
        self.assertIn(("q", ""), api_items)
        self.assertEqual(pairs, original)

    def test_ids_mode_supports_large_batches_and_preserves_cursor(self):
        pairs = [("size", "10000"), ("view", "ids"), ("cursor", "000A+/=="), ("collectors", "000107438")]
        self.assertEqual(get_api_search_query(pairs, ids_view=True), pairs[:3] + [("collectors", "107438")])
        with self.assertRaises(SearchQueryError):
            get_api_search_query(pairs)

    def test_unsupported_and_empty_filters_are_omitted_consistently(self):
        pairs = [("unknown", "value"), ("utm_source", "mail"), ("-q", "007"), ("people", ""), ("q", "007")]
        for ids_view in (False, True):
            self.assertEqual(prepare_search_query(pairs, ids_view=ids_view), [("q", "007")])


class SearchPreparationHooksTest(IsolatedAsyncioTestCase):
    def make_request(self, query: bytes = b""):
        return Request({"type": "http", "method": "GET", "path": "/search", "query_string": query, "headers": []})

    async def test_simple_site_replaces_availability_instead_of_creating_conflict(self):
        request = self.make_request(b"availability=3&-availability=2&content_types=000061")
        prepared = await prepare_search_request(request, hooks=SimpleHooks(request))
        self.assertEqual([pair for pair in prepared if "availability" in pair[0]], [("availability", "4")])
        self.assertEqual([pair for pair in prepared if pair[0] == "content_types"], [("content_types", "61")])

    async def test_series_is_kept_when_extra_parameters_supply_its_collection(self):
        request = self.make_request(b"series=001%2FAccounts")
        prepared = await prepare_search_request(request, [("collection", "000194")], hooks=HooksSpec(request))
        self.assertIn(("series", "001/Accounts"), prepared)
        self.assertIn(("collection", "194"), prepared)
        without_collection = await prepare_search_request(request, hooks=HooksSpec(request))
        self.assertNotIn(("series", "001/Accounts"), without_collection)

    async def test_hook_conflicting_singletons_are_rejected(self):
        class ConflictingHooks(HooksSpec):
            async def before_get_search(self, query_params):
                return query_params + [("size", "50")]

        request = self.make_request(b"size=20")
        with self.assertRaises(SearchQueryError):
            await prepare_search_request(request, hooks=ConflictingHooks(request))

    async def test_site_parameters_override_singletons_before_preferences_are_applied(self):
        for query in (b"", b"size=50&sort=date_from"):
            request = self.make_request(query)
            extras = [("events", "000111818"), ("size", "10"), ("sort", "created_at")]
            prepared = await prepare_search_request(request, extras, hooks=HooksSpec(request))
            self.assertEqual([pair for pair in prepared if pair[0] == "size"], [("size", "10")])
            self.assertIn(("events", "111818"), prepared)
            self.assertIn(("sort", "created_at"), prepared)
            self.assertIn(("direction", "desc"), prepared)

    async def test_site_overrides_do_not_hide_invalid_or_conflicting_url_parameters(self):
        for query in (b"size=invalid", b"size=20&size=50"):
            request = self.make_request(query)
            with self.assertRaises(SearchQueryError):
                await prepare_search_request(request, [("size", "10")], hooks=HooksSpec(request))
