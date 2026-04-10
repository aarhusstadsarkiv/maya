import asyncio
import os
import unittest

from unittest.mock import AsyncMock, patch

os.environ.setdefault("BASE_DIR", "sites/aarhus")
os.environ.setdefault("TEST", "TRUE")

from maya.core.dynamic_settings import init_settings
from maya.commands import cli

init_settings()


class TestOrdersCli(unittest.TestCase):

    def test_run_cron_tasks_calls_both_order_crons(self):
        asyncio.run(self._test_run_cron_tasks_calls_both_order_crons())

    async def _test_run_cron_tasks_calls_both_order_crons(self):
        from maya.orders import service as orders_service

        with (
            patch.object(orders_service, "cron_orders_expire", new=AsyncMock(return_value=1)) as expire_mock,
            patch.object(orders_service, "cron_renewal_emails", new=AsyncMock(return_value=1)) as renew_mock,
        ):
            await cli._run_cron_tasks()

        expire_mock.assert_awaited_once()
        renew_mock.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
