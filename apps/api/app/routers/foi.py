"""API social de EcoNexoFoI: investigación abierta y colaboración profesional."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status

from .. import db
from ..deps import CurrentUser, current_user
from ..foi_schemas import (
    FoiAuthorOut,
    FoiCommentCreateIn,
    FoiCommentOut,
    FoiCommunityOut,
    FoiPostCreateIn,
    FoiPostOut,
    FoiPostUpdateIn,
    FoiProfileOut,
    FoiProfileUpdateIn,
    FoiToggleOut,
    FoiUploadOut,
)
from ..storage import put_research_file

router = APIRouter(prefix="/foi", tags=["EcoNexoFoI"])

_POST_SELECT = """
SELECT p.id,p.kind,p.title,p.abstract,p.tags,p.attachment_url,p.attachment_name,
       p.attachment_mime,p.status,p.created_at,p.updated_at,
       u.id AS author_id,u.name AS author_name,u.avatar_url AS author_avatar_url,
       COALESCE(pr.headline,'Investigador/a independiente') AS author_headline,
       pr.institution AS author_institution,pr.discipline AS author_discipline,
       EXISTS(SELECT 1 FROM foi_follows f WHERE f.follower_id=$1 AND f.followed_id=u.id) AS author_followed,
       c.id AS community_id,c.slug AS community_slug,c.name AS community_name,
       c.description AS community_description,c.icon AS community_icon,c.color AS community_color,
       CASE WHEN c.id IS NULL THEN 0 ELSE (SELECT count(*)::int FROM foi_community_members cm WHERE cm.community_id=c.id) END AS community_members_count,
       CASE WHEN c.id IS NULL THEN 0 ELSE (SELECT count(*)::int FROM foi_posts cp WHERE cp.community_id=c.id AND cp.status='published') END AS community_posts_count,
       CASE WHEN c.id IS NULL THEN false ELSE EXISTS(SELECT 1 FROM foi_community_members cm WHERE cm.community_id=c.id AND cm.user_id=$1) END AS community_joined,
       (SELECT count(*)::int FROM foi_post_reactions r WHERE r.post_id=p.id AND r.kind='like') AS likes_count,
       (SELECT count(*)::int FROM foi_comments co WHERE co.post_id=p.id) AS comments_count,
       EXISTS(SELECT 1 FROM foi_post_reactions r WHERE r.post_id=p.id AND r.user_id=$1 AND r.kind='like') AS liked,
       EXISTS(SELECT 1 FROM foi_saved_posts s WHERE s.post_id=p.id AND s.user_id=$1) AS saved
FROM foi_posts p
JOIN users u ON u.id=p.author_id AND u.is_active
LEFT JOIN foi_profiles pr ON pr.user_id=u.id
LEFT JOIN foi_communities c ON c.id=p.community_id
"""


def _author(row: dict, prefix: str = "author_") -> FoiAuthorOut:
    return FoiAuthorOut(
        id=row[f"{prefix}id"],
        name=row[f"{prefix}name"],
        headline=row.get(f"{prefix}headline") or "Investigador/a independiente",
        institution=row.get(f"{prefix}institution"),
        discipline=row.get(f"{prefix}discipline"),
        avatar_url=row.get(f"{prefix}avatar_url"),
        followed=bool(row.get(f"{prefix}followed", False)),
    )


def _community(row: dict) -> FoiCommunityOut | None:
    if row.get("community_id") is None:
        return None
    return FoiCommunityOut(
        id=row["community_id"], slug=row["community_slug"], name=row["community_name"],
        description=row["community_description"], icon=row["community_icon"], color=row["community_color"],
        members_count=int(row["community_members_count"] or 0), posts_count=int(row["community_posts_count"] or 0),
        joined=bool(row["community_joined"]),
    )


def _post(row) -> FoiPostOut:
    data = dict(row)
    return FoiPostOut(
        id=data["id"], kind=data["kind"], title=data["title"], abstract=data["abstract"],
        tags=list(data["tags"] or []), attachment_url=data["attachment_url"],
        attachment_name=data["attachment_name"], attachment_mime=data["attachment_mime"],
        status=data["status"], created_at=data["created_at"], updated_at=data["updated_at"],
        author=_author(data), community=_community(data), likes_count=int(data["likes_count"] or 0),
        comments_count=int(data["comments_count"] or 0), liked=bool(data["liked"]), saved=bool(data["saved"]),
    )


async def _ensure_profile(user_id: UUID) -> None:
    await db.pool().execute(
        """
        INSERT INTO foi_profiles (user_id,headline)
        VALUES ($1,'Investigador/a independiente')
        ON CONFLICT (user_id) DO NOTHING
        """,
        user_id,
    )


@router.get("/posts", response_model=list[FoiPostOut])
async def list_posts(
    kind: Literal["research", "question", "proposal"] | None = None,
    community_id: UUID | None = None,
    q: str = Query(default="", max_length=120),
    scope: Literal["all", "following", "saved"] = "all",
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(current_user),
) -> list[FoiPostOut]:
    rows = await db.pool().fetch(
        _POST_SELECT + """
        WHERE p.status='published'
          AND ($2::text IS NULL OR p.kind=$2)
          AND ($3::uuid IS NULL OR p.community_id=$3)
          AND ($4='' OR p.title ILIKE '%' || $4 || '%' OR p.abstract ILIKE '%' || $4 || '%'
               OR EXISTS(SELECT 1 FROM unnest(p.tags) tag WHERE tag ILIKE '%' || $4 || '%'))
          AND ($5='all'
               OR ($5='following' AND EXISTS(SELECT 1 FROM foi_follows f WHERE f.follower_id=$1 AND f.followed_id=p.author_id))
               OR ($5='saved' AND EXISTS(SELECT 1 FROM foi_saved_posts s WHERE s.user_id=$1 AND s.post_id=p.id)))
        ORDER BY p.created_at DESC
        LIMIT $6 OFFSET $7
        """,
        user.id, kind, community_id, q.strip(), scope, limit, offset,
    )
    return [_post(row) for row in rows]


@router.get("/posts/{post_id}", response_model=FoiPostOut)
async def get_post(post_id: UUID, user: CurrentUser = Depends(current_user)) -> FoiPostOut:
    row = await db.pool().fetchrow(_POST_SELECT + " WHERE p.id=$2 AND p.status='published'", user.id, post_id)
    if row is None:
        raise HTTPException(404, "Publicación no encontrada")
    return _post(row)


@router.post("/posts", response_model=FoiPostOut, status_code=status.HTTP_201_CREATED)
async def create_post(body: FoiPostCreateIn, user: CurrentUser = Depends(current_user)) -> FoiPostOut:
    await _ensure_profile(user.id)
    if body.community_id is not None and not await db.pool().fetchval("SELECT EXISTS(SELECT 1 FROM foi_communities WHERE id=$1)", body.community_id):
        raise HTTPException(404, "Comunidad no encontrada")
    post_id = await db.pool().fetchval(
        """
        INSERT INTO foi_posts (
            author_id,community_id,kind,title,abstract,tags,
            attachment_url,attachment_name,attachment_mime
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        RETURNING id
        """,
        user.id, body.community_id, body.kind, body.title.strip(), body.abstract.strip(),
        body.tags, body.attachment_url, body.attachment_name, body.attachment_mime,
    )
    return await get_post(post_id, user)


@router.patch("/posts/{post_id}", response_model=FoiPostOut)
async def update_post(post_id: UUID, body: FoiPostUpdateIn, user: CurrentUser = Depends(current_user)) -> FoiPostOut:
    current = await db.pool().fetchrow("SELECT author_id FROM foi_posts WHERE id=$1", post_id)
    if current is None:
        raise HTTPException(404, "Publicación no encontrada")
    if current["author_id"] != user.id:
        raise HTTPException(403, "Sólo el autor puede editar esta publicación")
    await db.pool().execute(
        """
        UPDATE foi_posts SET
          title=COALESCE($2,title),abstract=COALESCE($3,abstract),tags=COALESCE($4,tags),
          community_id=COALESCE($5,community_id),status=COALESCE($6,status)
        WHERE id=$1
        """,
        post_id, body.title.strip() if body.title else None, body.abstract.strip() if body.abstract else None,
        body.tags, body.community_id, body.status,
    )
    if body.status == "archived":
        row = await db.pool().fetchrow(_POST_SELECT + " WHERE p.id=$2", user.id, post_id)
        return _post(row)
    return await get_post(post_id, user)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_post(post_id: UUID, user: CurrentUser = Depends(current_user)) -> Response:
    result = await db.pool().execute("DELETE FROM foi_posts WHERE id=$1 AND author_id=$2", post_id, user.id)
    if result == "DELETE 0":
        raise HTTPException(404, "Publicación no encontrada o sin permisos")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/posts/{post_id}/like", response_model=FoiToggleOut)
async def toggle_like(post_id: UUID, user: CurrentUser = Depends(current_user)) -> FoiToggleOut:
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            removed = await conn.fetchval(
                "DELETE FROM foi_post_reactions WHERE post_id=$1 AND user_id=$2 AND kind='like' RETURNING true",
                post_id, user.id,
            )
            active = not bool(removed)
            if active:
                try:
                    await conn.execute(
                        "INSERT INTO foi_post_reactions(post_id,user_id,kind) VALUES ($1,$2,'like')",
                        post_id, user.id,
                    )
                except Exception as exc:
                    if not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM foi_posts WHERE id=$1 AND status='published')", post_id):
                        raise HTTPException(404, "Publicación no encontrada") from exc
                    raise
            count = await conn.fetchval("SELECT count(*)::int FROM foi_post_reactions WHERE post_id=$1 AND kind='like'", post_id)
    return FoiToggleOut(active=active, count=int(count or 0))


@router.post("/posts/{post_id}/save", response_model=FoiToggleOut)
async def toggle_save(post_id: UUID, user: CurrentUser = Depends(current_user)) -> FoiToggleOut:
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            removed = await conn.fetchval("DELETE FROM foi_saved_posts WHERE post_id=$1 AND user_id=$2 RETURNING true", post_id, user.id)
            active = not bool(removed)
            if active:
                try:
                    await conn.execute("INSERT INTO foi_saved_posts(post_id,user_id) VALUES ($1,$2)", post_id, user.id)
                except Exception as exc:
                    if not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM foi_posts WHERE id=$1 AND status='published')", post_id):
                        raise HTTPException(404, "Publicación no encontrada") from exc
                    raise
            count = await conn.fetchval("SELECT count(*)::int FROM foi_saved_posts WHERE post_id=$1", post_id)
    return FoiToggleOut(active=active, count=int(count or 0))


@router.get("/posts/{post_id}/comments", response_model=list[FoiCommentOut])
async def list_comments(post_id: UUID, user: CurrentUser = Depends(current_user)) -> list[FoiCommentOut]:
    rows = await db.pool().fetch(
        """
        SELECT co.id,co.body,co.created_at,co.updated_at,u.id AS author_id,u.name AS author_name,
               u.avatar_url AS author_avatar_url,COALESCE(pr.headline,'Investigador/a independiente') AS author_headline,
               pr.institution AS author_institution,pr.discipline AS author_discipline,
               EXISTS(SELECT 1 FROM foi_follows f WHERE f.follower_id=$2 AND f.followed_id=u.id) AS author_followed
        FROM foi_comments co JOIN users u ON u.id=co.author_id
        LEFT JOIN foi_profiles pr ON pr.user_id=u.id
        WHERE co.post_id=$1 ORDER BY co.created_at ASC
        """,
        post_id, user.id,
    )
    return [FoiCommentOut(id=row["id"], body=row["body"], created_at=row["created_at"], updated_at=row["updated_at"], author=_author(dict(row))) for row in rows]


@router.post("/posts/{post_id}/comments", response_model=FoiCommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(post_id: UUID, body: FoiCommentCreateIn, user: CurrentUser = Depends(current_user)) -> FoiCommentOut:
    if not await db.pool().fetchval("SELECT EXISTS(SELECT 1 FROM foi_posts WHERE id=$1 AND status='published')", post_id):
        raise HTTPException(404, "Publicación no encontrada")
    comment_id = await db.pool().fetchval(
        "INSERT INTO foi_comments(post_id,author_id,body) VALUES ($1,$2,$3) RETURNING id",
        post_id, user.id, body.body.strip(),
    )
    rows = await list_comments(post_id, user)
    return next(comment for comment in rows if comment.id == comment_id)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_comment(comment_id: UUID, user: CurrentUser = Depends(current_user)) -> Response:
    result = await db.pool().execute("DELETE FROM foi_comments WHERE id=$1 AND author_id=$2", comment_id, user.id)
    if result == "DELETE 0":
        raise HTTPException(404, "Comentario no encontrado o sin permisos")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/communities", response_model=list[FoiCommunityOut])
async def list_communities(user: CurrentUser = Depends(current_user)) -> list[FoiCommunityOut]:
    rows = await db.pool().fetch(
        """
        SELECT c.id,c.slug,c.name,c.description,c.icon,c.color,
               (SELECT count(*)::int FROM foi_community_members m WHERE m.community_id=c.id) AS members_count,
               (SELECT count(*)::int FROM foi_posts p WHERE p.community_id=c.id AND p.status='published') AS posts_count,
               EXISTS(SELECT 1 FROM foi_community_members m WHERE m.community_id=c.id AND m.user_id=$1) AS joined
        FROM foi_communities c ORDER BY members_count DESC,c.name
        """,
        user.id,
    )
    return [FoiCommunityOut(**dict(row)) for row in rows]


@router.post("/communities/{community_id}/join", response_model=FoiToggleOut)
async def toggle_community(community_id: UUID, user: CurrentUser = Depends(current_user)) -> FoiToggleOut:
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            removed = await conn.fetchval("DELETE FROM foi_community_members WHERE community_id=$1 AND user_id=$2 RETURNING true", community_id, user.id)
            active = not bool(removed)
            if active:
                try:
                    await conn.execute("INSERT INTO foi_community_members(community_id,user_id) VALUES ($1,$2)", community_id, user.id)
                except Exception as exc:
                    if not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM foi_communities WHERE id=$1)", community_id):
                        raise HTTPException(404, "Comunidad no encontrada") from exc
                    raise
            count = await conn.fetchval("SELECT count(*)::int FROM foi_community_members WHERE community_id=$1", community_id)
    return FoiToggleOut(active=active, count=int(count or 0))


@router.get("/profile/me", response_model=FoiProfileOut)
async def my_profile(user: CurrentUser = Depends(current_user)) -> FoiProfileOut:
    await _ensure_profile(user.id)
    row = await db.pool().fetchrow(
        """
        SELECT u.id,u.name,u.email,u.avatar_url,pr.headline,pr.institution,pr.discipline,
               pr.bio,pr.location,pr.website,pr.orcid,pr.interests,false AS followed,
               (SELECT count(*)::int FROM foi_follows f WHERE f.followed_id=u.id) AS followers_count,
               (SELECT count(*)::int FROM foi_follows f WHERE f.follower_id=u.id) AS following_count,
               (SELECT count(*)::int FROM foi_posts p WHERE p.author_id=u.id AND p.status='published') AS posts_count
        FROM users u JOIN foi_profiles pr ON pr.user_id=u.id WHERE u.id=$1
        """,
        user.id,
    )
    return FoiProfileOut(**dict(row))


@router.patch("/profile/me", response_model=FoiProfileOut)
async def update_profile(body: FoiProfileUpdateIn, user: CurrentUser = Depends(current_user)) -> FoiProfileOut:
    await _ensure_profile(user.id)
    await db.pool().execute(
        """
        UPDATE foi_profiles SET headline=$2,institution=$3,discipline=$4,bio=$5,
            location=$6,website=$7,orcid=$8,interests=$9 WHERE user_id=$1
        """,
        user.id, body.headline.strip(), body.institution, body.discipline, body.bio,
        body.location, body.website, body.orcid, body.interests,
    )
    return await my_profile(user)


@router.get("/profiles/suggested", response_model=list[FoiAuthorOut])
async def suggested_profiles(
    limit: int = Query(default=5, ge=1, le=20),
    user: CurrentUser = Depends(current_user),
) -> list[FoiAuthorOut]:
    rows = await db.pool().fetch(
        """
        SELECT u.id AS author_id,u.name AS author_name,u.avatar_url AS author_avatar_url,
               COALESCE(pr.headline,'Investigador/a independiente') AS author_headline,
               pr.institution AS author_institution,pr.discipline AS author_discipline,false AS author_followed
        FROM users u LEFT JOIN foi_profiles pr ON pr.user_id=u.id
        WHERE u.id<>$1 AND u.is_active
          AND NOT EXISTS(SELECT 1 FROM foi_follows f WHERE f.follower_id=$1 AND f.followed_id=u.id)
          AND EXISTS(SELECT 1 FROM foi_posts p WHERE p.author_id=u.id AND p.status='published')
        ORDER BY (SELECT count(*) FROM foi_posts p WHERE p.author_id=u.id AND p.status='published') DESC,u.created_at DESC
        LIMIT $2
        """,
        user.id, limit,
    )
    return [_author(dict(row)) for row in rows]


@router.post("/profiles/{profile_id}/follow", response_model=FoiToggleOut)
async def toggle_follow(profile_id: UUID, user: CurrentUser = Depends(current_user)) -> FoiToggleOut:
    if profile_id == user.id:
        raise HTTPException(409, "No podés seguirte a vos mismo")
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            removed = await conn.fetchval("DELETE FROM foi_follows WHERE follower_id=$1 AND followed_id=$2 RETURNING true", user.id, profile_id)
            active = not bool(removed)
            if active:
                try:
                    await conn.execute("INSERT INTO foi_follows(follower_id,followed_id) VALUES ($1,$2)", user.id, profile_id)
                except Exception as exc:
                    if not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE id=$1 AND is_active)", profile_id):
                        raise HTTPException(404, "Perfil no encontrado") from exc
                    raise
            count = await conn.fetchval("SELECT count(*)::int FROM foi_follows WHERE followed_id=$1", profile_id)
    return FoiToggleOut(active=active, count=int(count or 0))


_ALLOWED_UPLOADS = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/csv",
    "image/png",
    "image/jpeg",
    "image/webp",
}
_MAX_UPLOAD_BYTES = 15 * 1024 * 1024


@router.get("/uploads/{attachment_id}", name="download_research_attachment")
async def download_research_attachment(
    attachment_id: UUID,
    user: CurrentUser = Depends(current_user),
) -> Response:
    del user
    row = await db.pool().fetchrow(
        "SELECT filename,content_type,data FROM foi_attachments WHERE id=$1",
        attachment_id,
    )
    if row is None:
        raise HTTPException(404, "Archivo no encontrado")
    safe_name = "".join(char for char in row["filename"] if char.isalnum() or char in " ._-")[:120]
    return Response(
        content=bytes(row["data"]),
        media_type=row["content_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name or "investigacion"}"',
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/uploads", response_model=FoiUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_research(
    request: Request,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(current_user),
) -> FoiUploadOut:
    mime = file.content_type or "application/octet-stream"
    if mime not in _ALLOWED_UPLOADS:
        raise HTTPException(415, "Formato no admitido. Usá PDF, DOCX, CSV, PNG, JPG o WebP")
    data = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(413, "El archivo supera el máximo de 15 MB")
    if not data:
        raise HTTPException(422, "El archivo está vacío")
    name = file.filename or "investigacion"
    url = put_research_file(data, mime, name)
    if not url:
        attachment_id = await db.pool().fetchval(
            """
            INSERT INTO foi_attachments(owner_id,filename,content_type,size_bytes,data)
            VALUES ($1,$2,$3,$4,$5) RETURNING id
            """,
            user.id, name[:240], mime, len(data), data,
        )
        url = str(request.url_for("download_research_attachment", attachment_id=str(attachment_id)))
    return FoiUploadOut(url=url, name=name[:240], mime=mime, size=len(data))