"""
Main application file for the maya application.
"""

from maya.core.dynamic_settings import settings
from maya.core.logging import get_log
from starlette.applications import Starlette
from maya.routes import get_app_routes
from maya.core.middleware import middleware
from maya.core.exception_handlers import exception_handlers
from maya.core.hooks import get_hooks
from maya.core.paths import get_data_dir_path
import contextlib
import os
import sys


hooks = get_hooks()
routes = get_app_routes()
routes = hooks.after_routes_init(routes)


@contextlib.asynccontextmanager
async def lifespan(app):

    try:

        sys.path.append(".")
        log = get_log()
        data_dir = get_data_dir_path()

        if not os.path.exists(data_dir):
            log.info(f"Creating data directory: {data_dir}")
            os.makedirs(data_dir)

        log.info(f"Environment: {settings.get('environment')}")
        log.info(f"App loaded from the file {os.path.abspath(__file__)}")
        log.info("App lifecycle started")

        api_key = settings.get("api_key")
        if api_key == "api_key":
            log.error("API_KEY is missing. Please set the API_KEY environment variable before running the app.")
            raise RuntimeError("Missing required environment variable: API_KEY")
        yield
    finally:
        log.info("App lifecycle ended")


app = Starlette(
    debug=settings["debug"],  # type: ignore
    middleware=middleware,
    routes=routes,
    exception_handlers=exception_handlers,  # type: ignore
    lifespan=lifespan,
)
