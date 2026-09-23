import asyncio
import os
import unittest

from unittest.mock import AsyncMock, patch
from click.testing import CliRunner

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

from maya.core.dynamic_settings import init_settings
from maya.commands import cli

init_settings()


class TestOrdersCli(unittest.TestCase):

    def test_run_cron_tasks_calls_only_order_crons(self):
        asyncio.run(self._test_run_cron_tasks_calls_only_order_crons())

    async def _test_run_cron_tasks_calls_only_order_crons(self):
        from maya.orders import service as orders_service
        from maya.orders import refresh

        with (
            patch.object(refresh, "cron_refresh_records", new=AsyncMock(return_value={"updated": 2, "failed": 0})) as refresh_mock,
            patch.object(orders_service, "cron_orders_expire", new=AsyncMock(return_value=1)) as expire_mock,
            patch.object(orders_service, "cron_renewal_emails", new=AsyncMock(return_value=1)) as renew_mock,
        ):
            await cli._run_cron_tasks()

        refresh_mock.assert_not_awaited()
        expire_mock.assert_awaited_once()
        renew_mock.assert_awaited_once()

    def test_refresh_command_runs_independently(self):
        with (
            patch("maya.orders.refresh.cron_refresh_records", new=AsyncMock(return_value={"updated": 2, "failed": 0})) as refresh,
            patch("maya.orders.service.cron_orders_expire", new=AsyncMock()) as expire,
            patch("maya.orders.service.cron_renewal_emails", new=AsyncMock()) as renew,
            patch.dict(os.environ),
        ):
            result = CliRunner().invoke(cli.cli, ["refresh-order-records", "sites/aarhus"])
            self.assertEqual(os.environ["BASE_DIR"], os.path.abspath("sites/aarhus"))
        self.assertEqual(result.exit_code, 0, result.output)
        refresh.assert_awaited_once()
        expire.assert_not_awaited()
        renew.assert_not_awaited()

    def test_refresh_task_failure_is_logged(self):
        with (
            patch("maya.orders.refresh.cron_refresh_records", new=AsyncMock(side_effect=RuntimeError("Database unavailable"))),
            patch.object(cli.logger, "exception") as log_exception,
            patch.dict(os.environ),
        ):
            result = CliRunner().invoke(cli.cli, ["refresh-order-records", "sites/aarhus"])
        self.assertEqual(result.exit_code, 0, result.output)
        log_exception.assert_called_once_with("Material refresh task failed")


if __name__ == "__main__":
    unittest.main()
