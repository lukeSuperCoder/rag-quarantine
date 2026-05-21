"""Initialize the local SQLite database used by the Flask backend."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from config.settings import DATA_DIR

DB_PATH = DATA_DIR / "backend" / "app.sqlite3"


def get_db_path() -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def init_db() -> None:
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                doc_name TEXT NOT NULL,
                doc_type TEXT NOT NULL DEFAULT '',
                country TEXT NOT NULL DEFAULT '',
                source_path TEXT NOT NULL DEFAULT '',
                txt_path TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                milvus_id INTEGER,
                text TEXT NOT NULL,
                doc_name TEXT NOT NULL,
                doc_type TEXT NOT NULL DEFAULT '',
                country TEXT NOT NULL DEFAULT '',
                chunk_index INTEGER NOT NULL,
                section_title TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
            CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_doc_type ON chunks(doc_type);
            CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id);
            """
        )
