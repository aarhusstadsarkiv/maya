"""
Load the default maya .env file of the site running
"""

from dotenv import load_dotenv
import os
from maya.core.logging_handlers import get_init_logger
from maya.core.paths import get_base_dir_path


log = get_init_logger()


def load():
    """
    Load the .env-dist included with the source code of maya
    Override with "local" .env file if it exists
    """
    local_dot_env = get_base_dir_path(".env")

    if os.path.exists(local_dot_env):
        load_dotenv(local_dot_env, override=True)
        log.info(f"{local_dot_env} file loaded. Will override .env.dist settings")
    else:
        log.info(f"Local {local_dot_env} file NOT loaded")
