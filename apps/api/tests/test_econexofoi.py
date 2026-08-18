from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.foi_schemas import CommunityRegisterIn, FoiPostCreateIn


def test_free_community_registration_requires_a_strong_password() -> None:
    with pytest.raises(ValidationError):
        CommunityRegisterIn(
            name="Investigadora",
            email="investigadora@example.com",
            password="sololetras",
            terms_accepted=True,
        )


def test_research_post_cleans_duplicate_tags() -> None:
    post = FoiPostCreateIn(
        kind="research",
        title="Monitoreo comunitario de agua",
        abstract="Resultados abiertos del monitoreo participativo realizado durante seis meses.",
        tags=[" Agua ", "#agua", "Biodiversidad"],
    )
    assert post.tags == ["Agua", "Biodiversidad"]


def test_foi_routes_are_registered() -> None:
    pytest.importorskip("asyncpg")
    pytest.importorskip("aiomqtt")
    pytest.importorskip("jose")
    from app.main import app

    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/auth/community/register" in paths
    assert "/foi/posts" in paths
    assert "/foi/communities" in paths
    assert "/foi/uploads/{attachment_id}" in paths


def test_migration_16_is_synced_and_contains_the_social_model() -> None:
    root = Path(__file__).resolve().parents[3]
    api_file = root / "apps/api/migrations/16_econexofoi_research_network.sql"
    infra_file = root / "infra/db/migrations/16_econexofoi_research_network.sql"
    assert api_file.read_bytes() == infra_file.read_bytes()
    sql = api_file.read_text(encoding="utf-8")
    for table in ("foi_profiles", "foi_posts", "foi_comments", "foi_communities", "foi_attachments"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql