from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelConfigCreateDTO(BaseModel):
    config_type: Literal["extract"] = "extract"
    name: str = Field(min_length=1, max_length=100)
    base_url: str
    api_key: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    provider_options: dict[str, Any] | None = None


class ModelConfigUpdateDTO(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    base_url: str | None = None
    api_key: str | None = Field(default=None, min_length=1)
    model_name: str | None = Field(default=None, min_length=1)
    timeout_seconds: int | None = Field(default=None, ge=1, le=600)
    provider_options: dict[str, Any] | None = None
    is_enabled: bool | None = None


class ModelConfigReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    config_type: str
    name: str
    base_url: str
    api_key_masked: str
    model_name: str
    timeout_seconds: int
    provider_options: dict[str, Any] | None = None
    is_enabled: bool
    created_at: str
    updated_at: str
