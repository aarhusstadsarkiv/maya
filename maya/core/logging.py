"""
Simple logging setup for Maya application.

Exposes the following functions:
    - get_log(): returns the main application logger
    - get_access_log(): returns the access logger
    - get_custom_log(name): returns a custom named logger
"""

from typing import Any
import logging
from maya.core.dynamic_settings import settings
from maya.core import logging_handlers
import warnings
from maya.core.paths import get_data_dir_path


logging_handlers.generate_log_dir()
warnings.simplefilter(action="ignore", category=FutureWarning)
logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)


def get_custom_log(name: str) -> logging.Logger:
    """
    Create or return a logger configured like the main application logger.

    The `name` is used as:
      - the logger name (logging.getLogger(name))
      - the base name of the log file: <name>.log
    """
    # This is safe as logger is a singleton
    logger = logging.getLogger(name)
    level: Any = settings["log_level"]
    logger.setLevel(level)

    # Only configure handlers once per logger
    if not logger.handlers:

        if "rotating_file" in settings["log_handlers"]:
            file_name = get_data_dir_path("logs", f"{name}.log")
            fh = logging_handlers.get_rotating_json_file_handler(level, file_name=file_name)
            logger.addHandler(fh)

        if "stream" in settings["log_handlers"]:
            ch = logging_handlers.get_stream_handler(level)
            logger.addHandler(ch)

    return logger


def get_log() -> logging.Logger:
    """
    Return the main application logger, configured via get_custom_log('main').
    """
    return get_custom_log("main")


def get_access_log() -> logging.Logger:
    """
    Return the access logger, configuring it lazily on first use.
    """
    logger = logging.getLogger("access")
    level: Any = settings["log_level"]
    logger.setLevel(level)

    if not logger.handlers:
        access_file_name = get_data_dir_path("logs", "access.log")
        fh = logging_handlers.get_rotating_file_handler(level, file_name=access_file_name)
        logger.addHandler(fh)

    return logger
