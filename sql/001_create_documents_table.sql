CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type
        WHERE typname = 'document_status'
    ) THEN
        CREATE TYPE document_status AS ENUM (
            'UPLOADED',
            'PARSING',
            'CHUNKING',
            'EMBEDDING',
            'INDEXING',
            'READY',
            'FAILED',
            'EXPIRED'
        );
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_file_name TEXT NOT NULL,
    storage_url TEXT NOT NULL,
    status document_status NOT NULL DEFAULT 'UPLOADED',
    file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes > 0 AND file_size_bytes <= 1048576),
    mime_type TEXT NOT NULL,
    chunk_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    error_message TEXT DEFAULT NULL,
    CONSTRAINT documents_chunk_count_non_negative CHECK (
        chunk_count IS NULL OR chunk_count >= 0
    ),
    CONSTRAINT documents_error_message_required_for_failed CHECK (
        status <> 'FAILED' OR error_message IS NOT NULL
    ),
    CONSTRAINT documents_expiry_after_creation CHECK (
        expires_at > created_at
    )
);

CREATE INDEX IF NOT EXISTS idx_documents_status
    ON documents (status);

CREATE INDEX IF NOT EXISTS idx_documents_expires_at
    ON documents (expires_at);

CREATE INDEX IF NOT EXISTS idx_documents_created_at
    ON documents (created_at);
