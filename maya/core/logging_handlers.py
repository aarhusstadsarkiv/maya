"""
This module defines a set of logging utilities including custom formatters and handlers
to facilitate consistent and structured logging across an application.

Features:
- A custom formatter (`UvicornLikeFormatter`) that mimics Uvicorn-style console output.
- A JSON formatter (`JsonFormatter`) that serializes log records as structured JSON,
  supporting extra context fields for enhanced error tracking.
- Functions to create and configure stream and file-based logging handlers,
  including rotating file handlers using `ConcurrentRotatingFileHandler` for safe concurrent writes.
- Automatic log directory creation based on the application's data directory.
- A default initialization logger (`get_init_logger`) for early-stage logging before
  configuration settings are loaded.

Constants:
- `MAX_LOG_SIZE`: Maximum size (in bytes) for a single log file before rotation.
- `BACKUP_COUNT`: Number of backup files to retain for rotated logs.

Dependencies:
- `concurrent_log_handler`: Used for thread-safe and process-safe rotating log files.
- `maya.core.paths.get_data_dir_path`: Used to resolve the application's data directory path.

Intended Usage:
This module is designed to be imported and used in other parts of the application
to configure logging behavior consistently and robustly.
"""

from typing import Any
import logging
import os
from pathlib import Path
from concurrent_log_handler import ConcurrentRotatingFileHandler
import warnings
from maya.core.paths import get_data_dir_path
import json
from maya.core.logging_context import get_client_ip

MAX_LOG_SIZE = 100 * 1024 * 1024
BACKUP_COUNT = 5
warnings.simplefilter(action="ignore", category=FutureWarning)


formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class UvicornLikeFormatter(logging.Formatter):
    def format(self, record):
        level = f"{record.levelname}:".ljust(9)
        msg = record.getMessage()
        if record.exc_info:
            print("Has exception info")
            msg += "\n" + self.formatException(record.exc_info)
        return f"{level} {msg}"


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }

        client_ip = getattr(record, "client_ip", None) or get_client_ip()
        if client_ip is not None:
            log_record["client_ip"] = client_ip

        # If exception information is present, add it to the log record
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Add extra fields to the log record if they exist
        extra_fields = {
            "error_code": "error_code",
            "error_type": "error_type",
            "error_url": "error_url",
            "exception": "exception",
            "message": "message",
        }

        for attr, log_key in extra_fields.items():
            value = getattr(record, attr, None)
            if value:
                log_record[log_key] = value

        return json.dumps(log_record)


def generate_log_dir():
    log_dir = get_data_dir_path("logs")
    os.makedirs(log_dir, exist_ok=True)


def get_rotating_json_file_handler(level: Any, file_name):
    Path(file_name).touch()
    handler = ConcurrentRotatingFileHandler(file_name, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT)
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    return handler


def get_stream_handler(level: Any):
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(UvicornLikeFormatter())
    return ch


def get_rotating_file_handler(level: Any, file_name):
    Path(file_name).touch()
    handler = ConcurrentRotatingFileHandler(file_name, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def get_init_logger():
    """Init logger to use before settings are loaded"""

    log = logging.getLogger("env")
    if not len(log.handlers):
        level = logging.DEBUG
        log.setLevel(level)
        ch = get_stream_handler(level)
        log.addHandler(ch)

    return log
