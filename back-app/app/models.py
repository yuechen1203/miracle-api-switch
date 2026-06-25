from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AgentType(str, Enum):
    codex = "codex"
    claude_code = "claude_code"


class AgentStatus(str, Enum):
    uninitialized = "uninitialized"
    installed = "installed"
    missing = "missing"
    invalid = "invalid"


class ProxyStatus(str, Enum):
    stopped = "stopped"
    starting = "starting"
    running = "running"
    error = "error"


class TargetFormat(str, Enum):
    chat_completions = "chat/completions"
    responses = "responses"
    messages = "messages"


class ConfigPathRequest(BaseModel):
    config_path: str = ""


class ProviderCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=64)
    api_key: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    model: str = Field(min_length=1, max_length=128)
    proxy_enabled: bool = False
    proxy_port: Optional[int] = None
    target_format: Optional[Literal["chat/completions", "response", "responses", "messages"]] = None

    @field_validator("display_name", "api_key", "base_url", "model")
    @classmethod
    def strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be empty")
        return stripped

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        return value.rstrip("/")

    @field_validator("target_format")
    @classmethod
    def normalize_target_format(cls, value: Optional[str]) -> Optional[str]:
        if value == "response":
            return "responses"
        return value

    @model_validator(mode="after")
    def validate_proxy(self) -> "ProviderCreate":
        if self.proxy_enabled:
            if self.proxy_port is None:
                raise ValueError("proxy_port is required when proxy_enabled is true")
            if not 1 <= self.proxy_port <= 65535:
                raise ValueError("proxy_port must be between 1 and 65535")
            if self.target_format is None:
                raise ValueError("target_format is required when proxy_enabled is true")
        return self


class ProviderUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    api_key: Optional[str] = None
    base_url: Optional[str] = Field(default=None, min_length=1)
    model: Optional[str] = Field(default=None, min_length=1, max_length=128)
    proxy_enabled: Optional[bool] = None
    proxy_port: Optional[int] = None
    target_format: Optional[Literal["chat/completions", "response", "responses", "messages"]] = None
    expected_updated_at: Optional[str] = None

    @field_validator("display_name", "api_key", "base_url", "model")
    @classmethod
    def strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip()

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        return value.rstrip("/")

    @field_validator("target_format")
    @classmethod
    def normalize_target_format(cls, value: Optional[str]) -> Optional[str]:
        if value == "response":
            return "responses"
        return value


class ApplyProviderRequest(BaseModel):
    dry_run: bool = False
    start_proxy: bool = True


class UsageResetRequest(BaseModel):
    confirm: bool = True


class AgentPublic(BaseModel):
    model_config = ConfigDict(extra="allow")

    agent_type: AgentType
    config_path: str = ""
    resolved_config_file: Optional[str] = None
    status: AgentStatus
    status_message: str = ""
    current_provider_id: Optional[str] = None
    updated_at: Optional[str] = None


class ProviderPublic(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    agent_type: AgentType
    display_name: str
    base_url: str
    model: str
    proxy_enabled: bool = False
    proxy_port: Optional[int] = None
    target_format: Optional[TargetFormat] = None
    created_at: str
    updated_at: str
    has_api_key: bool
    api_key_masked: str
    local_proxy_url: Optional[str] = None
    proxy_status: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
