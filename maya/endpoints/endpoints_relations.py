from starlette.requests import Request
from starlette.responses import JSONResponse
from maya.core.logging import get_log
from maya.core.api import OpenAwsException
from maya.core import api
from maya.core.relations import format_relations, sort_data
from maya.core.auth import is_authenticated


log = get_log()


async def relations_post(request: Request):
    await is_authenticated(request, permissions=["employee"])

    try:
        await api.proxies_post_relations(request)
        return JSONResponse({"error": False, "message": "Relation er oprettet"})

    except OpenAwsException as e:
        log.exception("Error in relations_post")
        return JSONResponse({"error": True, "message": e.message})

    except Exception:
        log.exception("Error in relations_post")
        return JSONResponse({"error": True, "message": "Internal Server Error"})


async def relations_get(request: Request):
    type = request.path_params.get("type", "")
    id = request.path_params.get("id", "")
    try:
        relations = await api.proxies_get_relations(request, type, id)
        relations_formatted = format_relations(type, relations)
        if type == "people":
            relations_formatted = sort_data(relations_formatted, "display_label")
        if type == "events":
            relations_formatted = sort_data(relations_formatted, "rel_label")
        return JSONResponse(relations_formatted)

    except OpenAwsException as e:
        log.exception("Error in relations_get")
        return JSONResponse({"error": True, "message": e.message})

    except Exception:
        log.exception("Error in relations_get")
        return JSONResponse({"error": True, "message": "Internal Server Error"})


async def relations_delete(request: Request):
    await is_authenticated(request, permissions=["employee"])
    try:
        await api.proxies_delete_relations(request)
        return JSONResponse({"error": False, "message": "Relation er slettet"})

    except OpenAwsException as e:
        log.exception("Error in relations_delete")
        return JSONResponse({"error": True, "message": e.message})

    except Exception:
        log.exception("Error in relations_delete")
        return JSONResponse({"error": True, "message": "Internal Server Error"})
