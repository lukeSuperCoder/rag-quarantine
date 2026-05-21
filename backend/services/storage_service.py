"""SQLite persistence service."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from backend.db.init_db import get_db_path, init_db
from backend.services.common import new_id, now_iso
from config.settings import CHUNKS_FILE, DOCS_DIR


class StorageService:
    def __init__(self):
        init_db()
        self.db_path = get_db_path()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row is not None else None

    def healthcheck(self) -> bool:
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False

    def bootstrap_from_chunks_file(self) -> None:
        """Seed SQLite metadata from the existing script-generated chunks.json once."""
        if not CHUNKS_FILE.exists():
            return
        with self._connect() as conn:
            existing = conn.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()["count"]
        if existing:
            return

        chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
        grouped: dict[str, list[dict]] = {}
        for chunk in chunks:
            doc_name = chunk.get("doc_name", "")
            if not doc_name:
                continue
            grouped.setdefault(doc_name, []).append(chunk)

        for doc_chunks in grouped.values():
            document = self._create_bootstrap_document(doc_chunks[0])
            self.replace_chunks(document["id"], doc_chunks)
            self.update_document(document["id"], status="ready", chunk_count=len(doc_chunks))

    def _create_bootstrap_document(self, chunk: dict) -> dict:
        doc_name = chunk.get("doc_name", "")
        source_path = ""
        for path in DOCS_DIR.glob(f"{doc_name}.*"):
            source_path = str(path)
            break
        return self.create_document(
            filename=Path(source_path).name if source_path else doc_name,
            doc_name=doc_name,
            doc_type=chunk.get("doc_type", ""),
            country=chunk.get("country", ""),
            source_path=source_path,
            status="ready",
        )

    def create_document(self, filename: str, doc_name: str, doc_type: str = "", country: str = "", source_path: str = "", status: str = "uploaded") -> dict:
        document_id = new_id("doc")
        ts = now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (id, filename, doc_name, doc_type, country, source_path, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, filename, doc_name, doc_type, country, source_path, status, ts, ts),
            )
        return self.get_document(document_id)

    def update_document(self, document_id: str, **fields) -> dict | None:
        allowed = {"filename", "doc_name", "doc_type", "country", "source_path", "txt_path", "status", "chunk_count", "error_message"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        updates["updated_at"] = now_iso()
        assignments = ", ".join(f"{k} = ?" for k in updates)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE documents SET {assignments} WHERE id = ?",
                [*updates.values(), document_id],
            )
        return self.get_document(document_id)

    def get_document(self, document_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return self._row_to_dict(row)

    def list_documents(self, status: str | None = None, keyword: str | None = None) -> list[dict]:
        clauses = []
        params = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if keyword:
            clauses.append("(filename LIKE ? OR doc_name LIKE ?)")
            like = f"%{keyword}%"
            params.extend([like, like])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(f"SELECT * FROM documents{where} ORDER BY updated_at DESC", params).fetchall()
        return [dict(row) for row in rows]

    def delete_document(self, document_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            return cur.rowcount > 0

    def replace_chunks(self, document_id: str, chunks: Iterable[dict]) -> list[dict]:
        ts = now_iso()
        stored = []
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            for chunk in chunks:
                chunk_id = chunk.get("id") or new_id("chunk")
                row = {
                    "id": chunk_id,
                    "document_id": document_id,
                    "milvus_id": chunk.get("milvus_id"),
                    "text": chunk["text"],
                    "doc_name": chunk.get("doc_name", ""),
                    "doc_type": chunk.get("doc_type", ""),
                    "country": chunk.get("country", ""),
                    "chunk_index": int(chunk.get("chunk_index", 0)),
                    "section_title": chunk.get("section_title") or "",
                    "created_at": ts,
                    "updated_at": ts,
                }
                conn.execute(
                    """
                    INSERT INTO chunks (id, document_id, milvus_id, text, doc_name, doc_type, country, chunk_index, section_title, created_at, updated_at)
                    VALUES (:id, :document_id, :milvus_id, :text, :doc_name, :doc_type, :country, :chunk_index, :section_title, :created_at, :updated_at)
                    """,
                    row,
                )
                stored.append(row)
        self.update_document(document_id, chunk_count=len(stored))
        return stored

    def search_chunks(self, keyword: str, doc_type: str | None = None, country: str | None = None, limit: int = 20) -> list[dict]:
        clauses = ["text LIKE ?"]
        params = [f"%{keyword}%"]
        if doc_type:
            clauses.append("doc_type = ?")
            params.append(doc_type)
        if country:
            clauses.append("country = ?")
            params.append(country)
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id AS chunk_id, document_id, text, doc_name, doc_type, country, chunk_index, section_title
                FROM chunks
                WHERE {' AND '.join(clauses)}
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def get_chunk(self, chunk_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id AS chunk_id, document_id, milvus_id, text, doc_name, doc_type, country, chunk_index, section_title, created_at, updated_at
                FROM chunks WHERE id = ?
                """,
                (chunk_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def find_chunk_by_source(self, doc_name: str, chunk_index: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id AS chunk_id, document_id, milvus_id, text, doc_name, doc_type, country, chunk_index, section_title, created_at, updated_at
                FROM chunks
                WHERE doc_name = ? AND chunk_index = ?
                LIMIT 1
                """,
                (doc_name, int(chunk_index)),
            ).fetchone()
        return self._row_to_dict(row)

    def update_chunk(self, chunk_id: str, **fields) -> dict | None:
        allowed = {"milvus_id", "text", "doc_name", "doc_type", "country", "chunk_index", "section_title"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        updates["updated_at"] = now_iso()
        assignments = ", ".join(f"{k} = ?" for k in updates)
        with self._connect() as conn:
            conn.execute(f"UPDATE chunks SET {assignments} WHERE id = ?", [*updates.values(), chunk_id])
        return self.get_chunk(chunk_id)

    def update_session(self, session_id: str, title: str) -> dict | None:
        ts = now_iso()
        with self._connect() as conn:
            conn.execute("UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?", (title, ts, session_id))
        return self.get_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        with self._connect() as conn:
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            cur = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            return cur.rowcount > 0

    def create_session(self, title: str) -> dict:
        session_id = new_id("sess")
        ts = now_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO chat_sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, title, ts, ts),
            )
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
        return self._row_to_dict(row)

    def list_sessions(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM chat_sessions ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]

    def add_message(self, session_id: str, role: str, content: str, sources: list[dict] | None = None) -> dict:
        message_id = new_id("msg")
        ts = now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (id, session_id, role, content, sources_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (message_id, session_id, role, content, json.dumps(sources or [], ensure_ascii=False), ts),
            )
            conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (ts, session_id))
        return self.get_message(message_id)

    def get_message(self, message_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM chat_messages WHERE id = ?", (message_id,)).fetchone()
        return self._message_row(row)

    def list_messages(self, session_id: str, limit: int | None = None) -> list[dict]:
        sql = "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC"
        params: list = [session_id]
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._message_row(row) for row in rows]

    def recent_messages_for_model(self, session_id: str, max_history: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, max_history),
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    @staticmethod
    def _message_row(row) -> dict | None:
        if row is None:
            return None
        item = dict(row)
        item["sources"] = json.loads(item.pop("sources_json") or "[]")
        return item
