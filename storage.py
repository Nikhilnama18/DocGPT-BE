import os
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()


def get_r2_bucket_name() -> str:
    bucket_name = os.getenv("R2_BUCKET_NAME")
    if not bucket_name:
        raise RuntimeError("Missing R2_BUCKET_NAME configuration.")
    return bucket_name


def build_r2_public_url(object_key: str) -> str:
    public_base_url = os.getenv("R2_PUBLIC_BASE_URL")
    if public_base_url:
        return f"{public_base_url.rstrip('/')}/{object_key}"

    account_id = os.getenv("R2_ACCOUNT_ID")
    bucket_name = get_r2_bucket_name()
    if not account_id:
        raise RuntimeError(
            "Missing R2 public URL configuration. Set R2_PUBLIC_BASE_URL or R2_ACCOUNT_ID."
        )

    return (
        f"https://{bucket_name}.{account_id}.r2.cloudflarestorage.com/{object_key}"
    )


def get_r2_client():
    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key_id = os.getenv("R2_ACCESS_KEY_ID")
    secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not account_id or not access_key_id or not secret_access_key:
        raise RuntimeError(
            "Missing R2 configuration. Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY."
        )

    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_bytes_to_r2(object_key: str, content: bytes, mime_type: str) -> str:
    client = get_r2_client()
    bucket_name = get_r2_bucket_name()
    client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=content,
        ContentType=mime_type,
    )
    return build_r2_public_url(object_key)


def delete_from_r2(object_key: str) -> None:
    client = get_r2_client()
    client.delete_object(Bucket=get_r2_bucket_name(), Key=object_key)


def get_object_key_from_storage_url(storage_url: str) -> str:
    public_base_url = os.getenv("R2_PUBLIC_BASE_URL")
    if public_base_url:
        normalized_base_url = public_base_url.rstrip("/")
        if storage_url.startswith(f"{normalized_base_url}/"):
            object_key = storage_url.removeprefix(f"{normalized_base_url}/")
            if object_key:
                return object_key

    parsed_url = urlparse(storage_url)
    object_key = parsed_url.path.lstrip("/")
    if not object_key:
        raise ValueError(f"Unable to derive R2 object key from storage URL: {storage_url}")
    return object_key
