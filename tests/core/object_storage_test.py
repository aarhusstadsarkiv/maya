import asyncio
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from maya.core import object_storage
from maya.database.cache import DatabaseCache
from maya.database.utils import DatabaseConnection


class TestObjectStorage(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = DatabaseConnection(str(Path(self.tempdir.name) / "cache.db"))
        async with self.database.write_transaction_scope_async() as connection:
            await connection.execute("CREATE TABLE cache (key TEXT PRIMARY KEY, value TEXT, unix_timestamp INTEGER)")
        self.url = "https://nbg1.your-objectstorage.com/aca-access/520/000520432_f.jpg"
        self.connection_patch = patch.object(object_storage, "DatabaseConnection", return_value=self.database)
        self.connection_patch.start()

    async def asyncTearDown(self):
        self.connection_patch.stop()
        self.tempdir.cleanup()

    async def test_cache_hit_does_not_acquire_write_transaction(self):
        async with self.database.write_transaction_scope_async() as connection:
            await DatabaseCache(connection).set(f"boto3_{self.url}", "signed-url")
        with (
            patch.object(self.database, "write_transaction_scope_async") as write,
            patch.object(object_storage, "_generate_presigned_url", new_callable=AsyncMock) as generate,
        ):
            self.assertEqual(await object_storage._get_presigned_url(self.url), "signed-url")
        write.assert_not_called()
        generate.assert_not_awaited()

    async def test_expired_url_is_regenerated_and_cached(self):
        async with self.database.write_transaction_scope_async() as connection:
            await DatabaseCache(connection).set(f"boto3_{self.url}", "expired-url")
            await connection.execute("UPDATE cache SET unix_timestamp = 0")
        with patch.object(object_storage, "_generate_presigned_url", new_callable=AsyncMock, return_value="fresh-url") as generate:
            self.assertEqual(await object_storage._get_presigned_url(self.url), "fresh-url")
            self.assertEqual(await object_storage._get_presigned_url(self.url), "fresh-url")
            generate.assert_awaited_once_with(self.url)

    async def test_concurrent_cache_misses_generate_only_once(self):
        with patch.object(object_storage, "_generate_presigned_url", new_callable=AsyncMock, return_value="fresh-url") as generate:
            values = await asyncio.gather(*(object_storage._get_presigned_url(self.url) for _ in range(5)))
            self.assertEqual(values, ["fresh-url"] * 5)
            generate.assert_awaited_once()

    async def test_rechecks_cache_after_initial_read(self):
        original_write = self.database.write_transaction_scope_async

        @asynccontextmanager
        async def filled_by_another_worker():
            async with original_write() as connection:
                await DatabaseCache(connection).set(f"boto3_{self.url}", "other-worker-url")
            async with original_write() as connection:
                yield connection

        with (
            patch.object(self.database, "write_transaction_scope_async", side_effect=filled_by_another_worker),
            patch.object(object_storage, "_generate_presigned_url", new_callable=AsyncMock) as generate,
        ):
            self.assertEqual(await object_storage._get_presigned_url(self.url), "other-worker-url")
            generate.assert_not_awaited()

    async def test_signing_failure_returns_original_url_without_caching(self):
        with (
            patch.object(object_storage, "_generate_presigned_url", new_callable=AsyncMock, side_effect=RuntimeError("failed")),
            patch.object(object_storage, "log"),
        ):
            self.assertEqual(await object_storage._get_presigned_url(self.url), self.url)
        async with self.database.transaction_scope_async() as connection:
            self.assertIsNone(await DatabaseCache(connection).get(f"boto3_{self.url}"))

    async def test_unrelated_storage_url_bypasses_cache(self):
        with patch.object(object_storage, "DatabaseConnection") as connect:
            url = "https://storage.googleapis.com/example/image.jpg"
            self.assertEqual(await object_storage._get_presigned_url(url), url)
            connect.assert_not_called()

    async def test_s3_client_is_reused_and_closed(self):
        s3 = Mock()
        s3.generate_presigned_url.return_value = "signed-url"
        with (
            patch.object(object_storage, "_s3_client", None),
            patch.object(object_storage.boto3, "client", return_value=s3) as create_client,
        ):
            for _ in range(2):
                self.assertEqual(await object_storage._generate_presigned_url(self.url), "signed-url")
            create_client.assert_called_once()
            s3.generate_presigned_url.assert_called_with(
                ClientMethod="get_object", Params={"Bucket": "aca-access", "Key": "520/000520432_f.jpg"}, ExpiresIn=3600
            )
            object_storage.close_s3_client()
            object_storage.close_s3_client()
            s3.close.assert_called_once()
            self.assertIsNone(object_storage._s3_client)
