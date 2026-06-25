from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "miracle-api-switch"
APP_VERSION = "0.1.0"
CACHE_DIR_NAME = ".hyc_cache"


def get_back_app_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def get_workspace_root() -> Path:
    configured = os.getenv("MIRACLE_WORKSPACE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return get_back_app_dir().parent.resolve()


def get_cache_dir(workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    return root / CACHE_DIR_NAME

