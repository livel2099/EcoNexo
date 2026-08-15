"""Almacenamiento de fotos (interfaz S3-compatible: MinIO local / S3 en prod)."""
from __future__ import annotations

import logging
import uuid

import boto3
from botocore.config import Config

from .config import get_settings

log = logging.getLogger("econexo.storage")


def _client():
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def put_photo(data: bytes, content_type: str) -> str | None:
    """Sube la foto y devuelve una URL publica (endpoint publico del bucket)."""
    s = get_settings()
    key = f"reports/{uuid.uuid4().hex}"
    try:
        _client().put_object(
            Bucket=s.s3_bucket, Key=key, Body=data, ContentType=content_type
        )
        return f"{s.s3_public_endpoint}/{s.s3_bucket}/{key}"
    except Exception as exc:
        log.warning("upload de foto fallo: %s", exc)
        return None
