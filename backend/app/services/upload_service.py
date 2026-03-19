import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime

from fastapi import UploadFile


APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(APP_DIR)
UPLOAD_ROOT_DIR = os.path.join(BACKEND_DIR, "uploads")
PUBLIC_UPLOAD_PREFIX = "/uploads"
DEFAULT_UPLOAD_SUFFIX = ".jpg"


@dataclass(frozen=True)
class SavedUploadFile:
    file_system_path: str
    public_path: str
    relative_path: str


def _normalize_suffix(filename: str | None) -> str:
    suffix = os.path.splitext(filename or "")[1].lower()
    if not suffix:
        return DEFAULT_UPLOAD_SUFFIX
    if not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
        return DEFAULT_UPLOAD_SUFFIX
    return suffix


def save_upload_file(upload_file: UploadFile) -> SavedUploadFile:
    current_date = datetime.now()
    date_path = os.path.join(
        f"{current_date.year:04d}",
        f"{current_date.month:02d}",
        f"{current_date.day:02d}",
    )
    target_directory = os.path.join(UPLOAD_ROOT_DIR, date_path)
    os.makedirs(target_directory, exist_ok=True)

    suffix = _normalize_suffix(upload_file.filename)
    filename = f"{uuid.uuid4().hex}{suffix}"
    file_system_path = os.path.join(target_directory, filename)

    upload_file.file.seek(0)
    with open(file_system_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    relative_path = os.path.join(date_path, filename).replace("\\", "/")
    public_path = f"{PUBLIC_UPLOAD_PREFIX}/{relative_path}"
    return SavedUploadFile(
        file_system_path=file_system_path,
        public_path=public_path,
        relative_path=relative_path,
    )
