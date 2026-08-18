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
        region_name=s.s3_region,
    )


def _encryption_options() -> dict[str, str]:
    encryption = get_settings().s3_server_side_encryption.strip()
    return {"ServerSideEncryption": encryption} if encryption else {}


def validate_image(data: bytes, content_type: str) -> str:
    """Valida MIME y firma binaria; devuelve una extensión segura."""
    signatures = {
        "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
        "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
        "image/webp": (b"RIFF", ".webp"),
    }
    expected = signatures.get(content_type.lower())
    if expected is None:
        raise ValueError("Formato de imagen no admitido")
    signature, extension = expected
    if not data.startswith(signature) or (content_type.lower() == "image/webp" and data[8:12] != b"WEBP"):
        raise ValueError("El contenido del archivo no coincide con su tipo MIME")
    return extension


def put_photo(data: bytes, content_type: str) -> str | None:
    """Sube la foto y devuelve una URL publica (endpoint publico del bucket)."""
    s = get_settings()
    if not s.s3_enabled:
        return None
    key = f"reports/{uuid.uuid4().hex}"
    try:
        _client().put_object(
            Bucket=s.s3_bucket, Key=key, Body=data, ContentType=content_type,
            **_encryption_options(),
        )
        return f"{s.s3_public_endpoint}/{s.s3_bucket}/{key}"
    except Exception as exc:
        log.warning("upload de foto fallo: %s", exc)
        return None


def put_research_file(data: bytes, content_type: str, filename: str) -> str | None:
    """Sube un adjunto de EcoNexoFoI conservando un nombre seguro."""
    import re

    s = get_settings()
    if not s.s3_enabled:
        return None
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-.")[:120] or "investigacion"
    key = f"foi/{uuid.uuid4().hex}-{safe_name}"
    try:
        _client().put_object(
            Bucket=s.s3_bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            Metadata={"original-name": safe_name},
            **_encryption_options(),
        )
        return f"{s.s3_public_endpoint}/{s.s3_bucket}/{key}"
    except Exception as exc:
        log.warning("upload de investigación falló: %s", exc)
        return None