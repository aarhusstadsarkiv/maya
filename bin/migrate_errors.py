#!/usr/bin/env python
"""
sqlite3 migrations for adding logged errors into a sqlite3 database.
"""

import sys

sys.path.append(".")

from maya.core.dynamic_settings import settings
from maya.core.migration import Migration
from maya.migrations.errors import migrations_error_log
from maya.core.logging import get_log
import os

# Check if the environment variable BASE_DIR is set
if "BASE_DIR" not in os.environ:
    print("Environment variable BASE_DIR is not set. E.g. set it like this:")
    print("export BASE_DIR=sites/aarhus")
    exit(1)


log = get_log()


try:
    db_path = settings["sqlite3"]["errors"]
    log.info(f"Using database path: {db_path}")
except KeyError:
    log.error("No database URL found in settings")
    exit(1)

migration_manager = Migration(db_path, migrations_error_log)
migration_manager.run_migrations()
migration_manager.close()
