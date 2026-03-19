import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET_NAME: str


settings = Settings(
    S3_ENDPOINT_URL=os.getenv("S3_ENDPOINT_URL", "").strip(),
    S3_ACCESS_KEY=os.getenv("S3_ACCESS_KEY", "").strip(),
    S3_SECRET_KEY=os.getenv("S3_SECRET_KEY", "").strip(),
    S3_BUCKET_NAME=os.getenv("S3_BUCKET_NAME", "").strip(),
)
