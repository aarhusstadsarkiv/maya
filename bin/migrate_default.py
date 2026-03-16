#!/usr/bin/env python
"""

migrations if the system needs to contain:
- Bookmarks
- Searches

"""

import sys

sys.path.append(".")

from maya.core.dynamic_settings import settings
from maya.core.migration import Migration
from maya.migrations.default import migrations_default
from maya.core.logging import get_log
import os

# Check if the environment variable BASE_DIR is set
if "BASE_DIR" not in os.environ:
    print("Environment variable BASE_DIR is not set. E.g. set it like this:")
    print("export BASE_DIR=sites/aarhus")
    exit(1)


log = get_log()


try:
    db_path = settings["sqlite3"]["default"]
    log.info(f"Using database path: {db_path}")
except KeyError:
    log.error("No database URL found in settings")
    exit(1)

migration_manager = Migration(db_path, migrations_default)
migration_manager.run_migrations()
migration_manager.close()
