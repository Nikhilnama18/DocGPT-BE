from datetime import datetime
from uuid import UUID

from db import get_db_connection


def create_document_record(
    document_id: UUID,
    original_file_name: str,
    storage_url: str,
    file_size_bytes: int,
    mime_type: str,
    created_at: datetime,
    expires_at: datetime,
) -> dict:
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
                        original_file_name,
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
                return cursor.fetchone()


def update_document_status(
    document_id: str,
    status: str,
    *,
    chunk_count: int | None = None,
    error_message: str | None = None,
) -> dict | None:
    with get_db_connection() as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE documents
                    SET
                        status = %s,
                        chunk_count = COALESCE(%s, chunk_count),
                        error_message = %s,
                        updated_at = NOW()
                    WHERE id = %s
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
                        status,
                        chunk_count,
                        error_message,
                        document_id,
                    ),
                )
                return cursor.fetchone()


def get_document_by_id(document_id: str) -> dict | None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
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
                FROM documents
                WHERE id = %s
                """,
                (document_id,),
            )
            return cursor.fetchone()


def list_documents_for_cleanup(limit: int = 100) -> list[dict]:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
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
                FROM documents
                WHERE status = 'FAILED' OR expires_at <= NOW()
                ORDER BY expires_at ASC, created_at ASC
                LIMIT %s
                """,
                (limit,),
            )
            return cursor.fetchall()


def delete_document_record(document_id: str) -> dict | None:
    with get_db_connection() as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM documents
                    WHERE id = %s
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
                    (document_id,),
                )
                return cursor.fetchone()
