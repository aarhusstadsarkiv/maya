"""
Proxy for resources endpoints
- locations
- people
- collections
(etc)

All that is not records
"""

from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.exceptions import HTTPException
from maya.core.templates import templates
from maya.core.context import get_context
from maya.core.logging import get_log
from maya.core import api
from maya.resources import resource_alter
from maya.core.hooks import get_hooks
from maya.core.object_storage import set_presigned_urls_resource
from maya.core.proxy_validation import validate_resource_path
import json

log = get_log()


async def _get_resource(request: Request):
    """
    Get resource from api and alter it with hooks
    """
    hooks = get_hooks(request)
    id = request.path_params["id"]
    resource_type = request.path_params["resource_type"]

    resource = await api.proxies_get_resource(request, resource_type, id=id)
    resource = await set_presigned_urls_resource(resource)
    resource = await hooks.after_get_resource(resource_type, resource)

    # remove leading zeros from id string
    # these ruins the search results
    id = id.lstrip("0")
    resource["id_real"] = id
    return resource


async def _get_resource_context(request):
    resource = await _get_resource(request)
    title = resource["display_label"]
    resource = resource_alter.resource_alter(resource)
    resource["meta"]["title"] = title
    resource_type = request.path_params["resource_type"]

    context_variables = {"title": title, "resource": resource, "meta": resource["meta"]}
    context = await get_context(request, context_variables, resource_type)
    return context


async def get_resource(request: Request):
    resource_type = request.path_params["resource_type"]
    id = request.path_params["id"]
    validate_resource_path(resource_type, id)

    context = await _get_resource_context(request)
    template_path = f"resources/{resource_type}.html"
    response = templates.TemplateResponse(request, template_path, context)
    return response


async def get_resource_json(request: Request):
    id = request.path_params["id"]
    json_type = request.path_params["type"]
    resource_type = request.path_params["resource_type"]
    validate_resource_path(resource_type, id)

    if json_type == "api":
        resource_api = await api.proxies_get_resource(request, resource_type, id)
        resource_json = json.dumps(resource_api, indent=4, ensure_ascii=False)
        return PlainTextResponse(resource_json)
    elif json_type == "resource_and_types":
        context = await _get_resource_context(request)
        resource_json = json.dumps(context["resource"], indent=4, ensure_ascii=False)
        return PlainTextResponse(resource_json)

    else:
        raise HTTPException(status_code=404, detail="Type not found")
