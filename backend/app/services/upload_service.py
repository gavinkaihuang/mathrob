import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from urllib.parse import urlparse

import boto3
from botocore.client import Config
from fastapi import UploadFile

from ..config import settings

DEFAULT_UPLOAD_SUFFIX = ".jpg"
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(APP_DIR)
LEGACY_UPLOAD_ROOT = os.path.join(BACKEND_DIR, "uploads")


@dataclass(frozen=True)
class SavedUploadFile:
    object_key: str
    public_url: str
    s3_uri: str


def _normalize_suffix(filename: str | None) -> str:
    suffix = os.path.splitext(filename or "")[1].lower()
    if not suffix:
        return DEFAULT_UPLOAD_SUFFIX
    if not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
        return DEFAULT_UPLOAD_SUFFIX
    return suffix


def _require_s3_settings() -> None:
    missing = []
    if not settings.S3_ENDPOINT_URL:
        missing.append("S3_ENDPOINT_URL")
    if not settings.S3_ACCESS_KEY:
        missing.append("S3_ACCESS_KEY")
    if not settings.S3_SECRET_KEY:
        missing.append("S3_SECRET_KEY")
    if not settings.S3_BUCKET_NAME:
        missing.append("S3_BUCKET_NAME")
    if missing:
        raise RuntimeError(f"Missing S3 settings: {', '.join(missing)}")


@lru_cache(maxsize=1)
def get_s3_client():
    _require_s3_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name="us-east-1",
    )


def _build_object_key(prefix: str, current_date: datetime, filename: str) -> str:
    clean_prefix = prefix.strip("/")
    date_path = f"{current_date.year:04d}/{current_date.month:02d}/{current_date.day:02d}"
    return f"{clean_prefix}/{date_path}/{filename}" if clean_prefix else f"{date_path}/{filename}"


def _build_public_url(object_key: str) -> str:
    endpoint = settings.S3_ENDPOINT_URL.rstrip("/")
    return f"{endpoint}/{settings.S3_BUCKET_NAME}/{object_key}"


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    value = s3_uri[5:]
    if "/" not in value:
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    bucket_name, object_key = value.split("/", 1)
    return bucket_name, object_key


def read_s3_object_bytes(s3_uri: str) -> bytes:
    bucket_name, object_key = parse_s3_uri(s3_uri)
    response = get_s3_client().get_object(Bucket=bucket_name, Key=object_key)
    return response["Body"].read()


def get_accessible_image_url(image_ref: str, expires_in: int = 3600) -> str:
    if not image_ref:
        return image_ref

    try:
        if image_ref.startswith("s3://"):
            bucket_name, object_key = parse_s3_uri(image_ref)
            return get_s3_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": object_key},
                ExpiresIn=expires_in,
            )

        if image_ref.startswith("http://") or image_ref.startswith("https://"):
            object_key = _extract_object_key_from_public_url(image_ref)
            if object_key:
                return get_s3_client().generate_presigned_url(
                    "get_object",
                    Params={"Bucket": settings.S3_BUCKET_NAME, "Key": object_key},
                    ExpiresIn=expires_in,
                )
            return image_ref

        return image_ref
    except Exception:
        return image_ref


def _extract_object_key_from_public_url(public_url: str) -> str | None:
    endpoint = settings.S3_ENDPOINT_URL.rstrip("/")
    expected_prefix = f"{endpoint}/{settings.S3_BUCKET_NAME}/"
    if public_url.startswith(expected_prefix):
        return public_url[len(expected_prefix):]

    parsed = urlparse(public_url)
    path = parsed.path.lstrip("/")
    if path.startswith(f"{settings.S3_BUCKET_NAME}/"):
        return path[len(settings.S3_BUCKET_NAME) + 1 :]
    return None


def delete_uploaded_object(image_ref: str) -> bool:
    if not image_ref:
        return False

    try:
        if image_ref.startswith("s3://"):
            bucket_name, object_key = parse_s3_uri(image_ref)
            get_s3_client().delete_object(Bucket=bucket_name, Key=object_key)
            return True

        if image_ref.startswith("http://") or image_ref.startswith("https://"):
            object_key = _extract_object_key_from_public_url(image_ref)
            if object_key:
                get_s3_client().delete_object(Bucket=settings.S3_BUCKET_NAME, Key=object_key)
                return True
            return False

        candidate_paths = []
        if os.path.isabs(image_ref):
            candidate_paths.append(image_ref)
        else:
            candidate_paths.append(os.path.join(LEGACY_UPLOAD_ROOT, image_ref))
            candidate_paths.append(os.path.join(LEGACY_UPLOAD_ROOT, os.path.basename(image_ref)))

        for path in candidate_paths:
            if os.path.exists(path):
                os.remove(path)
                return True

        return False
    except Exception:
        return False


def upload_to_s3(upload_file: UploadFile, prefix: str = "exams") -> SavedUploadFile:
    _require_s3_settings()

    current_date = datetime.now()
    suffix = _normalize_suffix(upload_file.filename)
    filename = f"{uuid.uuid4().hex}{suffix}"
    object_key = _build_object_key(prefix=prefix, current_date=current_date, filename=filename)

    upload_file.file.seek(0)
    extra_args = {}
    if upload_file.content_type:
        extra_args["ContentType"] = upload_file.content_type

    if extra_args:
        get_s3_client().upload_fileobj(
            upload_file.file,
            settings.S3_BUCKET_NAME,
            object_key,
            ExtraArgs=extra_args,
        )
    else:
        get_s3_client().upload_fileobj(
            upload_file.file,
            settings.S3_BUCKET_NAME,
            object_key,
        )

    public_url = _build_public_url(object_key)
    s3_uri = f"s3://{settings.S3_BUCKET_NAME}/{object_key}"
    return SavedUploadFile(object_key=object_key, public_url=public_url, s3_uri=s3_uri)

def save_upload_file(upload_file: UploadFile, prefix: str = "exams") -> SavedUploadFile:
    return upload_to_s3(upload_file=upload_file, prefix=prefix)
