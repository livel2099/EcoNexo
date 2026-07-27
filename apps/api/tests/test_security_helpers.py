from __future__ import annotations

import pytest

pytest.importorskip("jose")

from app.security import create_citizen_token, decode_citizen_token, slugify, token_digest


def test_slugify_handles_accents_and_symbols() -> None:
    assert slugify("Municipalidad de El Soberbio – Misiones") == "municipalidad-de-el-soberbio-misiones"


def test_citizen_token_round_trip() -> None:
    subject = decode_citizen_token(create_citizen_token())
    assert subject is not None
    assert len(subject) >= 20


def test_token_digest_does_not_store_raw_token() -> None:
    assert token_digest("secret-token") != "secret-token"
    assert token_digest("secret-token") == token_digest("secret-token")
