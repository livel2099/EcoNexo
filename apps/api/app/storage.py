"""Almacenamiento privado de evidencias fotograficas en S3-compatible."""
from __future__ import annotations

import logging
import uuid

import boto3
from botocore.config import Config

from .config import get_settings

log = logging.getLogger("econexo.storage")

_ALLOWED_IMAGE_TYPES = {
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
    "image/webp": (b"RIFF", ".webp"),
}


def validate_image(data: bytes, declared_type: str) -> str:
    media_type = declared_type.lower().split(";", 1)[0].strip()
    if media_type not in _ALLOWED_IMAGE_TYPES:
        raise ValueError("Formato de imagen no permitido")
    signature, extension = _ALLOWED_IMAGE_TYPES[media_type]
    if not data.startswith(signature):
        raise ValueError("La firma del archivo no coincide con su tipo")
    if media_type == "image/webp" and (len(data) < 12 or data[8:12] != b"WEBP"):
        raise ValueError("Archivo WebP invalido")
    return extension


def _client(endpoint: str):
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def put_photo(data: bytes, content_type: str, extension: str) -> str | None:
    """Sube evidencia a un bucket privado y devuelve una referencia interna."""
    s = get_settings()
    key = f"reports/{uuid.uuid4().hex}{extension}"
    try:
        options = {
            "Bucket": s.s3_bucket,
            "Key": key,
            "Body": data,
            "ContentType": content_type,
        }
        if s.s3_server_side_encryption:
            options["ServerSideEncryption"] = s.s3_server_side_encryption
        _client(s.s3_endpoint).put_object(**options)
        return f"s3://{s.s3_bucket}/{key}"
    except Exception as exc:
        log.warning("upload de foto fallo: %s", exc)
        return None


def resolve_photo_url(reference: str | None, expires_seconds: int = 900) -> str | None:
    if not reference or not reference.startswith("s3://"):
        return reference
    s = get_settings()
    without_scheme = reference[5:]
    bucket, _, key = without_scheme.partition("/")
    if not bucket or not key:
        return None
    try:
        return _client(s.s3_public_endpoint).generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
    except Exception as exc:
        log.warning("firma de URL de foto fallo: %s", exc)
        return None
