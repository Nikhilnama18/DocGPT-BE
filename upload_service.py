from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from fastapi import HTTPException, UploadFile

from db import get_db_connection
from storage import delete_from_r2, upload_bytes_to_r2
1048576
MAX_UPLOAD_SIZE_BYTES = int(1024 * 1024)
DOCUMENT_TTL_HOURS = 12

ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def validate_upload(file_name: str | None, mime_type: str | None, file_size_bytes: int) -> str:
    if not file_name:
        raise HTTPException(status_code=400, detail="File name is required")

    extension = Path(file_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and Word documents (.doc, .docx) are allowed",
        )

    if file_size_bytes <= 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if file_size_bytes > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="File size must be less than 1.2 MB",
        )

    expected_mime_type = ALLOWED_EXTENSIONS[extension]
    if mime_type and mime_type not in {expected_mime_type, "application/octet-stream"}:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid MIME type for {extension} file",
        )

    return extension


async def create_uploaded_document(file: UploadFile) -> dict:
    file_bytes = await file.read()
    file_size_bytes = len(file_bytes)
    extension = validate_upload(file.filename, file.content_type, file_size_bytes)

    document_id = uuid.uuid4()
    object_key = f"documents/{document_id}{extension}"
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(hours=DOCUMENT_TTL_HOURS)
    mime_type = ALLOWED_EXTENSIONS[extension]

    try:
        storage_url = upload_bytes_to_r2(object_key, file_bytes, mime_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to upload file to R2") from exc

    try:
        with get_db_connection() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO documents (
                            id,
                            original_file_name,
                            storage_url,
                            status,
                            file_size_bytes,
                            mime_type,
                            created_at,
                            updated_at,
                            expires_at,
                            error_message
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING
                            id,
                            original_file_name,
                            storage_url,
                            status,
                            file_size_bytes,
                            mime_type,
                            chunk_count,
                            created_at,
                            updated_at,
                            expires_at,
                            error_message
                        """,
                        (
                            document_id,
                            file.filename,
                            storage_url,
                            "UPLOADED",
                            file_size_bytes,
                            mime_type,
                            created_at,
                            created_at,
                            expires_at,
                            None,
                        ),
                    )
                    document_record = cursor.fetchone()
    except RuntimeError as exc:
        try:
            delete_from_r2(object_key)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        try:
            delete_from_r2(object_key)
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail="Failed to save upload metadata",
        ) from exc

    return {
        "message": "File uploaded successfully and marked for processing",
        "document": document_record,
    }
