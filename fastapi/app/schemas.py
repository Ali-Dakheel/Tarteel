import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ExplainRequest(BaseRequest):
    question_id: int | None = None
    selected_option: int | None = Field(default=None, ge=0, le=3)
    lesson_id: int | None = None
    domain: str
    question_stem: str


class Chunk(BaseModel):
    """Internal representation of a pmp_chunks row. Never serialized to clients."""

    id: int
    lesson_id: int | None
    content: str
    metadata: dict[str, Any]
    chunk_index: int

    @field_validator("metadata", mode="before")
    @classmethod
    def parse_metadata(cls, v: Any) -> Any:
        # asyncpg returns JSONB columns as raw JSON strings
        if isinstance(v, str):
            return json.loads(v)
        return v


class ExplainResponse(BaseModel):
    """Returned by non-streaming (background job) calls."""

    explanation: str
    chunk_ids: list[int]
    cache_key: str


class HealthResponse(BaseModel):
    status: str
    ollama: bool
    postgres: bool
    redis: bool
