import os
import uuid
import aiofiles
from pathlib import Path
from app.core.config import settings


async def upload_file(content: bytes, filename: str, folder: str = "uploads") -> str:
    """
    Upload file to configured backend (local or S3).
    Returns the public URL / path to the stored file.
    """
    if settings.STORAGE_BACKEND == "s3":
        return await _upload_s3(content, filename, folder)
    return await _upload_local(content, filename, folder)


async def _upload_local(content: bytes, filename: str, folder: str) -> str:
    ext = Path(filename).suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_dir = Path(settings.LOCAL_UPLOAD_DIR) / folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / unique_name

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(content)

    # Return a relative URL that Nginx/Next will serve
    return f"/uploads/{folder}/{unique_name}"


async def _upload_s3(content: bytes, filename: str, folder: str) -> str:
    import boto3
    from botocore.exceptions import ClientError

    ext = Path(filename).suffix
    key = f"{folder}/{uuid.uuid4().hex}{ext}"

    s3 = boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    s3.put_object(
        Bucket=settings.AWS_BUCKET,
        Key=key,
        Body=content,
        ContentType=_guess_content_type(filename),
    )

    return f"https://{settings.AWS_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


def _guess_content_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    mapping = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    return mapping.get(ext, "application/octet-stream")