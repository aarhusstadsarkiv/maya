"""
This module defines the `HooksSpec` class, which provides default lifecycle hooks
for various operations in a web application using the Starlette framework.

These hooks are designed to be optionally overridden in custom implementations to
intercept and modify application behavior at key points such as route initialization,
response generation, login handling, autocomplete queries, context building,
record retrieval, search operations, and resource fetching.

Each method provides a structured point of extension to alter or augment the
underlying process and its data without modifying core logic, enabling flexible
customization.

Key features include:
- Modifying routes after initialization (`after_routes_init`)
- Customizing responses before they are returned (`before_response`)
- Adjusting login success/failure data (`after_login_success`, `after_login_failure`)
- Enhancing autocomplete and search behavior
(`before_get_auto_complete`, `after_get_auto_complete`, `before_get_search`, `after_get_search`)
- Modifying context data (`before_context`)
- Intercepting record retrieval logic (`after_get_record`, `after_get_record_and_types`)
- Transforming resource output from external APIs (`after_get_resource`)
"""

from starlette.requests import Request
from starlette.responses import Response
from maya.core.logging import get_log

log = get_log()


class HooksSpec:
    def __init__(self, request: Request):
        self.request = request

    def after_routes_init(self, routes: list) -> list:
        """
        Alter the routes after the base routes have been initialized.
        You may add or remove routes here.
        """
        return routes

    async def before_response(self, response: Response) -> Response:
        """
        Alter the response before it is returned.
        """
        return response

    async def after_login_success(self, response: dict) -> dict:
        """
        Alter the response after a successful login.
        """
        return response

    async def after_login_failure(self, response: dict) -> dict:
        """
        Alter the response after a login failure
        """
        return response

    async def before_get_auto_complete(self, query_params: list) -> list:
        """
        Alter the query params before the autocomplete is executed.
        """
        query_params.append(("limit", "25"))  # default limit
        return query_params

    async def after_get_auto_complete(self, query_params: list) -> list:
        """
        Alter the query params after the autocomplete is executed.
        """
        return query_params

    async def before_context(self, context: dict) -> dict:
        """
        Alter the context dictionary. Before the context is returned, e.g. to the template.
        """
        return context

    async def after_get_record(self, record: dict, meta_data: dict) -> tuple:
        """
        Alter the record and meta_data dictionaries after the api call
        """
        return record, meta_data

    async def after_get_record_and_types(self, record: dict, record_and_types: dict) -> tuple:
        """
        Alter the record and meta_data dictionaries after the api call
        """
        return record, record_and_types

    async def before_get_search(self, query_params: list) -> list:
        """
        Alter prepared search parameters before HTML, JSON, or ids searches.
        Numeric IDs are unpadded. Output is validated and normalized again.
        To override a single-value parameter, remove it before adding its new
        value; conflicting duplicates are rejected. Repeated filters are kept.
        """
        return query_params

    async def after_get_search(self, query_params: list) -> list:
        """
        Alter the search query params. After the search is executed.
        """
        return query_params

    async def after_get_resource(self, type: str, resource: dict) -> dict:
        """
        Alter the json returned from the proxies api.
        """
        return resource
