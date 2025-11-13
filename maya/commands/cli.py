"""
File containing CLI commands for the Maya CLI.
"""

import click
import subprocess
import os
import secrets
import glob
import sys
import json
import logging
from maya.core import logging_handlers
import asyncio
from maya import __version__, __program__


logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)
stream_handler = logging_handlers.get_stream_handler(logging.INFO)
logger.addHandler(stream_handler)
logger.propagate = False


class ConfigDirValidator:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.base_dir_abs = os.path.abspath(base_dir)
        self.error_message: str = ""

    def validate(self) -> bool:
        if not os.path.exists(self.base_dir_abs):
            self.error_message = f"Config directory '{self.base_dir}' does not exist."
            return False

        return True

    def get_error_message(self) -> str:
        return self.error_message


def _get_base_dir(base_dir):
    validator = ConfigDirValidator(base_dir)

    if not validator.validate():
        logger.info(validator.get_error_message())
        exit(1)

    logger.info(f"Using config dir: {validator.base_dir_abs}")

    return validator.base_dir_abs


@click.group()
@click.version_option(version=__version__, prog_name=__program__)
def cli():
    """
    maya is used for serving customized web-clients
    that uses the webservice from Aarhus City Archives as backend and datastore.

    For full documentation see https://demo.openaws.dk
    """
    pass


if os.name == "nt":
    # gunicorn is not supported on Windows, so we skip the server_prod command
    pass
else:

    @cli.command(help="Start the production gunicorn server.")
    @click.option("--port", default=5555, help="Server port.")
    @click.option("--workers", default=3, help="Number of workers.")
    @click.option("--host", default="0.0.0.0", help="Server host.")
    @click.argument("base_dir")
    def server_prod(port: int, workers: int, host: str, base_dir: str):

        base_dir = _get_base_dir(base_dir)
        os.environ["BASE_DIR"] = base_dir

        cmd = [
            # Notice that this can not just be "gunicorn" as it is a new subprocess being started
            sys.executable,
            "-m",
            "gunicorn",
            "maya.app:app",
            f"--workers={workers}",
            f"--bind={host}:{port}",
            "--worker-class=uvicorn.workers.UvicornWorker",
            "--log-level=info",
        ]

        try:
            logger.info("Started Gunicorn in the foreground")
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Gunicorn failed to start: {e}")
            exit(1)


@cli.command(help="Start the running Uvicorn dev-server.")
@click.option("--port", default=5555, help="Server port.")
@click.option("--workers", default=1, help="Number of workers.")
@click.option("--host", default="0.0.0.0", help="Server host.")
@click.argument("base_dir")
def server_dev(port: int, workers: int, host: str, base_dir: str, reload=True):

    base_dir = _get_base_dir(base_dir)
    os.environ["BASE_DIR"] = base_dir

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "maya.app:app",
        f"--host={host}",
        f"--port={port}",
        f"--workers={workers}",
        "--log-level=debug",
    ]

    if reload:
        # Default if to reload when the current directory or the base_dir directory changes
        reload_dirs = [".", base_dir]

        if not _is_source():
            # If not in source mode, only reload the base_dir directory
            reload_dirs = [base_dir]

        # reload when yml and py files change
        cmd.append("--reload")
        cmd.append("--reload-include=*.yml")
        cmd.append("--reload-include=*.json")

        for dir in reload_dirs:
            cmd.append(f"--reload-dir={dir}")

    try:
        logger.info("Started Uvicorn in the foreground")
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Uvicorn failed to start {e}")
        exit(1)


async def _run_cron_tasks() -> None:
    """
    Run nightly cron tasks:

    - Expire orders
    - Send renewal emails
    """
    from maya.database.crud_orders import cron_orders_expire, cron_renewal_emails

    # Expire orders
    try:
        await cron_orders_expire()
    except Exception:
        pass

    # Send renewal emails
    try:
        await cron_renewal_emails()
    except Exception:
        pass


@cli.command(help="Run scheduled cron tasks (orders expire, renewal emails).")
@click.argument("base_dir")
def cron(base_dir: str):
    """
    Example usage:
        maya cron sites/aarhus
    """
    base_dir = _get_base_dir(base_dir)
    os.environ["BASE_DIR"] = base_dir
    asyncio.run(_run_cron_tasks())


@cli.command(help="Execute a script within a config context.")
@click.option("-s", "--script", help="Path to the script to execute.", required=True)
@click.option("-c", "--config-dir", default="local", help="Specify a path to a config directory.", required=False)
def exec(base_dir: str, script: str):

    base_dir = _get_base_dir(base_dir)
    os.environ["BASE_DIR"] = base_dir

    python_executable = sys.executable
    cmd = [
        python_executable,
        script,
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Script failed: {e}")
        exit(1)


@cli.command(help="Generate a session secret.")
@click.option("--length", default=32, help="Length of secret.")
def server_secret(length):
    print(secrets.token_hex(length))


def run_tests(base_dir: str = "", tests_path_pattern: str = ""):
    """
    Run tests based on the provided base_dir and tests_path_pattern.
    - base_dir is the path to the BASE_DIR
    - tests_path_pattern is the path to the test files
    """

    os.environ["TEST"] = "TRUE"
    if base_dir:
        os.environ["BASE_DIR"] = base_dir
        logger.info(f"Running tests with config dir: {os.getenv('BASE_DIR')}")
    else:
        logger.info("No BASE_DIR is set. Running tests with built-in BASE_DIR and configuration")

    # Get all test files
    test_files = glob.glob(tests_path_pattern)
    if test_files:
        for test_file in test_files:
            logger.info(f"Running tests in {test_file}")

            # Run with sys.executable in order use the same python version as the current process
            subprocess.run([sys.executable, "-m", "unittest", test_file], check=True)
    else:
        logger.info(f"No tests found matching pattern {tests_path_pattern}")


def _is_source():
    """
    If running in a virtual environment and if the .is_source file exists,
    then allow dev commands
    """

    if sys.prefix != sys.base_prefix and os.path.exists("maya/.is_source"):
        return True


if _is_source() and os.name != "nt":
    # Only show dev commands if source version
    @cli.command(help="Run all tests.")
    def source_test():
        run_tests("sites/base_test", "tests/base_test/*.py")
        run_tests("sites/aarhus", "tests/aarhus/*.py")
        run_tests("sites/teater", "tests/teater/*.py")
        run_tests("", "tests/core/*.py")

    @cli.command(help="Fix code according to black, flake8, mypy.")
    def source_fix():
        os.system("black . --config pyproject.toml")
        os.system("mypy  --config-file pyproject.toml .")
        os.system("flake8 . --config .flake8")

    @cli.command(help="Generate importmap for JavaScript files.")
    def import_map():

        base_dir = "maya/static/js"
        js_files = [f for f in os.listdir(base_dir) if f.endswith(".js")]
        import_map = {"imports": {}}

        for js_file in js_files:
            key = f"/static/js/{js_file}"
            value = key + "?v={{ get_setting('version') }}"
            import_map["imports"][key] = value

        import_map = json.dumps(import_map, indent=4)
        import_map_html = f'<script type="importmap">\n{import_map}\n</script>'
        with open("maya/templates/includes/importmap.html", "w") as f:
            f.write(import_map_html)
