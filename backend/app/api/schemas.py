"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.config import SEARCH_MIN_SCORE


class HealthResponse(BaseModel):
    status: str
    env: str
    database: bool
    redis: bool
    pgvector: bool
    storage: str


class VideoUploadResponse(BaseModel):
    video_id: int
    filename: str
    status: str


class VideoStatusResponse(BaseModel):
    video_id: int
    filename: str
    status: str
    duration: float | None = None
    error_message: str | None = None
    created_at: datetime
    indexed_at: datetime | None = None
    progress: float = 0.0
    object_count: int = 0


class VideoListResponse(BaseModel):
    videos: list[VideoStatusResponse]


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=50)
    offset: int = Field(0, ge=0)
    video_id: int | None = None
    padding_sec: float | None = Field(None, ge=0)
    class_names: list[str] | None = None
    min_score: float = Field(SEARCH_MIN_SCORE, ge=0.0, le=1.0)
    appearance_gap_sec: float = Field(10.0, ge=0.0)


class SearchResult(BaseModel):
    video_id: int
    track_id: int
    class_name: str
    score: float
    confidence: float
    match_time: float
    start: float
    end: float
    start_label: str
    end_label: str
    object_id: int
    bounding_box: list[float]
    clip_url: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    email: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    user_id: int
    email: str
