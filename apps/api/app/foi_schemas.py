"""Contratos públicos de EcoNexoFoI."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


FoiPostKind = Literal["research", "question", "proposal"]


class CommunityRegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    discipline: str | None = Field(default=None, max_length=120)
    institution: str | None = Field(default=None, max_length=160)
    terms_accepted: bool
    legal_version: str = Field(default="2026-07-27", max_length=40)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("La contraseña debe incluir al menos una letra y un número")
        return value


class FoiProfileUpdateIn(BaseModel):
    headline: str = Field(min_length=2, max_length=160)
    institution: str | None = Field(default=None, max_length=160)
    discipline: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=120)
    website: str | None = Field(default=None, max_length=300)
    orcid: str | None = Field(default=None, pattern=r"^([0-9]{4}-){3}[0-9X]{4}$")
    interests: list[str] = Field(default_factory=list, max_length=12)


class FoiAuthorOut(BaseModel):
    id: UUID
    name: str
    headline: str
    institution: str | None = None
    discipline: str | None = None
    avatar_url: str | None = None
    followed: bool = False


class FoiProfileOut(FoiAuthorOut):
    email: str | None = None
    bio: str | None = None
    location: str | None = None
    website: str | None = None
    orcid: str | None = None
    interests: list[str] = Field(default_factory=list)
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0


class FoiCommunityOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    icon: str
    color: str
    members_count: int
    posts_count: int
    joined: bool


class FoiPostCreateIn(BaseModel):
    kind: FoiPostKind
    title: str = Field(min_length=8, max_length=220)
    abstract: str = Field(min_length=20, max_length=10000)
    tags: list[str] = Field(default_factory=list, max_length=10)
    community_id: UUID | None = None
    attachment_url: str | None = Field(default=None, max_length=1000)
    attachment_name: str | None = Field(default=None, max_length=240)
    attachment_mime: str | None = Field(default=None, max_length=120)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        output: list[str] = []
        for raw in values:
            value = raw.strip().lstrip("#")[:40]
            if value and value.casefold() not in {item.casefold() for item in output}:
                output.append(value)
        return output


class FoiPostUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=8, max_length=220)
    abstract: str | None = Field(default=None, min_length=20, max_length=10000)
    tags: list[str] | None = Field(default=None, max_length=10)
    community_id: UUID | None = None
    status: Literal["published", "archived"] | None = None


class FoiPostOut(BaseModel):
    id: UUID
    kind: FoiPostKind
    title: str
    abstract: str
    tags: list[str]
    attachment_url: str | None = None
    attachment_name: str | None = None
    attachment_mime: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    author: FoiAuthorOut
    community: FoiCommunityOut | None = None
    likes_count: int
    comments_count: int
    liked: bool
    saved: bool


class FoiCommentCreateIn(BaseModel):
    body: str = Field(min_length=2, max_length=4000)


class FoiCommentOut(BaseModel):
    id: UUID
    body: str
    created_at: datetime
    updated_at: datetime
    author: FoiAuthorOut


class FoiToggleOut(BaseModel):
    active: bool
    count: int


class FoiUploadOut(BaseModel):
    url: str
    name: str
    mime: str
    size: int