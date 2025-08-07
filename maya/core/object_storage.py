from maya.core.logging import get_log
from maya.database.crud_default import database_url
from maya.database.utils import DatabaseConnection
from maya.database.cache import DatabaseCache
import os
import boto3

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
BOTO3_EXPIRE = 3600

log = get_log()


async def set_presigned_urls(record: dict) -> dict:

    # Get thumbnail URL
    thumbnail_url = record.get("thumbnail", "")
    if thumbnail_url:
        thumbnail_url = await _get_presigned_url(thumbnail_url)
        record["thumbnail"] = thumbnail_url

    # portrait
    portrait = record.get("portrait", "")
    if portrait:
        portrait = await _get_presigned_url(portrait)
        record["portrait"] = portrait

    if "representations" in record:
        representations = record["representations"]
        for key in ["full_image", "large_image", "record_image", "video", "audio"]:
            if key in representations:
                representations[key] = await _get_presigned_url(representations[key])
    return record


async def _get_presigned_url(url: str):

    # Check if URL shoud be generated
    if not url.startswith("https://nbg1.your-objectstorage.com/"):
        return url

    cache_key = f"boto3_{url}"
    database_connection = DatabaseConnection(database_url)
    async with database_connection.transaction_scope_async() as connection:

        database_cache = DatabaseCache(connection)
        cached_url = await database_cache.get(cache_key, expire_in=BOTO3_EXPIRE)  # Cache for 1 hour

        if cached_url:
            return cached_url

        # Generate a new pre-signed URL
        presigned_url = await _generate_presigned_url(url)

        # Store the generated URL in cache
        await database_cache.set(cache_key, presigned_url)
    return presigned_url


async def _generate_presigned_url(url: str) -> str:
    """
    Generate a pre-signed URL for an object in S3 storage.
    E.g. https://nbg1.your-objectstorage.com/aca-access/520/000520432_f.jpg
    """

    log.debug(f"Generating pre-signed URL for: {url}")

    # Get object key which is "520/000520432_f.jpg" part of the URL
    object_key = url.split("https://nbg1.your-objectstorage.com/aca-access/")[-1]

    # Initialize the S3 client
    s3 = boto3.client(
        "s3",
        endpoint_url="https://nbg1.your-objectstorage.com",  # custom endpoint
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    # Generate the pre-signed URL
    url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": "aca-access", "Key": object_key},
        ExpiresIn=BOTO3_EXPIRE,  # 1 hour
    )

    log.debug(f"Generated pre-signed URL: {url}")
    return url
