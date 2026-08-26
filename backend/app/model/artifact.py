import hashlib
from pathlib import Path
from urllib.parse import quote

import httpx

from ..config import settings


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _download_private_object(bucket: str, object_path: str, destination: Path) -> Path:
    base_url = settings.supabase_url.strip().rstrip("/")
    service_key = settings.supabase_service_role_key.strip()
    if not base_url or not service_key:
        raise RuntimeError("Supabase model storage is not configured")

    safe_path = quote(object_path.lstrip("/"), safe="/")
    url = f"{base_url}/storage/v1/object/{bucket}/{safe_path}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    with httpx.stream(
        "GET",
        url,
        headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
        timeout=300,
        follow_redirects=True,
    ) as response:
        response.raise_for_status()
        with temporary.open("wb") as target:
            for chunk in response.iter_bytes(1024 * 1024):
                target.write(chunk)
    temporary.replace(destination)
    return destination


def ensure_model_artifact() -> Path:
    destination = Path(settings.model_path)
    expected_hash = settings.model_sha256.strip().upper()
    if destination.is_file() and (not expected_hash or sha256_file(destination) == expected_hash):
        return destination

    object_parts = [part.strip() for part in settings.model_object_parts.split(",") if part.strip()]
    if object_parts:
        destination.parent.mkdir(parents=True, exist_ok=True)
        assembled = destination.with_suffix(destination.suffix + ".assembling")
        with assembled.open("wb") as output:
            for index, object_path in enumerate(object_parts):
                part_path = destination.with_suffix(destination.suffix + f".part{index:03d}")
                _download_private_object(settings.model_bucket, object_path, part_path)
                with part_path.open("rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        output.write(chunk)
                part_path.unlink(missing_ok=True)
        assembled.replace(destination)
    else:
        if not settings.model_object_path:
            raise RuntimeError(f"Model file was not found at {destination}")
        _download_private_object(settings.model_bucket, settings.model_object_path, destination)

    if settings.model_size_bytes and destination.stat().st_size != settings.model_size_bytes:
        destination.unlink(missing_ok=True)
        raise RuntimeError("Downloaded model size does not match MODEL_SIZE_BYTES")
    if expected_hash and sha256_file(destination) != expected_hash:
        destination.unlink(missing_ok=True)
        raise RuntimeError("Downloaded model hash does not match MODEL_SHA256")
    return destination


def download_race_video(object_path: str, destination: Path) -> Path:
    return _download_private_object(settings.video_bucket, object_path, destination)
