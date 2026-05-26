from __future__ import annotations

import logging
from pathlib import Path

from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

_AVATAR_DIR = Path("~/.codex-pool/avatars").expanduser()
_MAX_AVATAR_BYTES = 2 * 1024 * 1024
_EXT_BY_TYPE = {"jpeg": ".jpg", "png": ".png", "gif": ".gif", "webp": ".webp"}


def _detect_image_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def avatar_dir() -> Path:
    path = _AVATAR_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def avatar_file_path(user_id: int) -> Path | None:
    directory = avatar_dir()
    for ext in _EXT_BY_TYPE.values():
        candidate = directory / f"{user_id}{ext}"
        if candidate.is_file():
            return candidate
    return None


def avatar_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".jpg":
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".gif":
        return "image/gif"
    if suffix == ".webp":
        return "image/webp"
    return "application/octet-stream"


def save_avatar(user_id: int, upload: UploadFile) -> str:
    data = upload.file.read(_MAX_AVATAR_BYTES + 1)
    if not data:
        raise HTTPException(400, "avatar file is empty")
    if len(data) > _MAX_AVATAR_BYTES:
        raise HTTPException(400, "avatar file exceeds 2MB")

    image_type = _detect_image_type(data)
    if image_type not in _EXT_BY_TYPE:
        raise HTTPException(400, "avatar must be JPG, PNG, GIF, or WebP")

    ext = _EXT_BY_TYPE[image_type]
    remove_avatar(user_id)
    path = avatar_dir() / f"{user_id}{ext}"
    path.write_bytes(data)
    return path.name


def remove_avatar(user_id: int) -> None:
    existing = avatar_file_path(user_id)
    if existing and existing.is_file():
        existing.unlink(missing_ok=True)
