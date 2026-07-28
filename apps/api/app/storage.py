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


class StorageUnavailableError(RuntimeError):
    """El despliegue no tiene almacenamiento de objetos habilitado."""


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
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name=settings.s3_region,
    )


def put_photo(data: bytes, content_type: str, extension: str) -> str:
    """Sube evidencia a un bucket privado y devuelve una referencia interna."""
    settings = get_settings()
    if not settings.s3_enabled:
        raise StorageUnavailableError(
            "El almacenamiento de evidencias no esta habilitado en este entorno"
        )

    key = f"reports/{uuid.uuid4().hex}{extension}"
    options = {
        "Bucket": settings.s3_bucket,
        "Key": key,
        "Body": data,
        "ContentType": content_type,
    }
    if settings.s3_server_side_encryption:
        options["ServerSideEncryption"] = settings.s3_server_side_encryption
    try:
        _client(settings.s3_endpoint).put_object(**options)
    except Exception as exc:
        log.exception("upload de foto fallo")
        raise StorageUnavailableError(
            "No se pudo guardar la evidencia fotografica"
        ) from exc
    return f"s3://{settings.s3_bucket}/{key}"


def resolve_photo_url(reference: str | None, expires_seconds: int = 900) -> str | None:
    if not reference or not reference.startswith("s3://"):
        return reference
    settings = get_settings()
    if not settings.s3_enabled:
        return None
    without_scheme = reference[5:]
    bucket, _, key = without_scheme.partition("/")
    if not bucket or not key:
        return None
    try:
        endpoint = settings.s3_public_endpoint or settings.s3_endpoint
        return _client(endpoint).generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
    except Exception as exc:
        log.warning("firma de URL de foto fallo: %s", exc)
        return None
