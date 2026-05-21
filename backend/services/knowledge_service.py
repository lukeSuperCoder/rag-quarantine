"""Knowledge-base service."""
from __future__ import annotations

from backend.services.storage_service import StorageService
from backend.services.vector_service import VectorService


class KnowledgeService:
    def __init__(self):
        self.storage = StorageService()

    def search(self, keyword: str, doc_type: str | None = None, country: str | None = None, limit: int = 20) -> list[dict]:
        return self.storage.search_chunks(keyword=keyword, doc_type=doc_type, country=country, limit=limit)

    def get_chunk(self, chunk_id: str) -> dict | None:
        return self.storage.get_chunk(chunk_id)

    def update_chunk_text(self, chunk_id: str, text: str) -> dict:
        chunk = self.storage.get_chunk(chunk_id)
        if not chunk:
            raise LookupError(chunk_id)

        updated = dict(chunk)
        updated["text"] = text
        # Update Milvus first. If embedding fails, SQLite remains unchanged.
        VectorService().update_chunk_vector(updated)
        self.storage.update_chunk(chunk_id, text=text)
        return {"chunk_id": chunk_id, "updated": True, "reembedded": True}
