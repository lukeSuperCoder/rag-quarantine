"""Embedding and Milvus service."""
from __future__ import annotations

from pymilvus import MilvusClient
from zai import ZhipuAiClient

from backend.services.common import escape_milvus_string
from config.settings import COLLECTION_NAME, EMBEDDING_MODEL, MILVUS_DB_PATH, SEARCH_PARAMS, VECTOR_DIM, ZHIPU_API_KEY


class VectorService:
    def __init__(self):
        self.zhipu = ZhipuAiClient(api_key=ZHIPU_API_KEY) if ZHIPU_API_KEY else None
        self._milvus_error: Exception | None = None
        try:
            self.milvus = MilvusClient(MILVUS_DB_PATH)
        except Exception as exc:
            self.milvus = None
            self._milvus_error = exc

    def healthcheck(self) -> bool:
        try:
            return self._client().has_collection(COLLECTION_NAME)
        except Exception:
            return False

    def _client(self) -> MilvusClient:
        if self.milvus is None:
            raise RuntimeError(f"Milvus 连接失败: {self._milvus_error}")
        return self.milvus

    def collection_fields(self) -> set[str]:
        info = self._client().describe_collection(COLLECTION_NAME)
        return {field["name"] for field in info.get("fields", [])}

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self.zhipu:
            raise RuntimeError("ZHIPU_API_KEY 未配置")
        resp = self.zhipu.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        vectors = [item.embedding for item in resp.data]
        if any(len(vec) != VECTOR_DIM for vec in vectors):
            raise RuntimeError("embedding 向量维度与 VECTOR_DIM 不一致")
        return vectors

    def upsert_chunks(self, chunks: list[dict]) -> None:
        if not chunks:
            return
        fields = self.collection_fields()
        vectors = self.embed_texts([chunk["text"] for chunk in chunks])
        rows = []
        for chunk, vector in zip(chunks, vectors):
            row = {
                "text": chunk["text"][:4096],
                "vector": vector,
                "doc_name": chunk.get("doc_name", "")[:256],
                "doc_type": chunk.get("doc_type", "")[:64],
                "country": chunk.get("country", "")[:64],
                "chunk_index": int(chunk.get("chunk_index", 0)),
                "section_title": (chunk.get("section_title") or "")[:256],
            }
            if "document_id" in fields:
                row["document_id"] = chunk.get("document_id", "")[:128]
            if "chunk_id" in fields:
                row["chunk_id"] = chunk.get("id") or chunk.get("chunk_id", "")
            rows.append(row)
        self._client().insert(collection_name=COLLECTION_NAME, data=rows)

    def update_chunk_vector(self, chunk: dict) -> None:
        self.delete_chunk(chunk)
        self.upsert_chunks([{
            "id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "text": chunk["text"],
            "doc_name": chunk["doc_name"],
            "doc_type": chunk["doc_type"],
            "country": chunk["country"],
            "chunk_index": chunk["chunk_index"],
            "section_title": chunk.get("section_title", ""),
        }])

    def search(self, query: str, top_k: int = 5, doc_type: str | None = None, country: str | None = None, limit_multiplier: int = 1) -> list[dict]:
        if not self.zhipu:
            raise RuntimeError("ZHIPU_API_KEY 未配置")
        self._client().load_collection(COLLECTION_NAME)
        query_vector = self.embed_texts([query])[0]
        filters = []
        if doc_type:
            filters.append(f'doc_type == "{escape_milvus_string(doc_type)}"')
        if country:
            filters.append(f'country == "{escape_milvus_string(country)}"')
        filter_expr = " and ".join(filters)
        fields = ["text", "doc_name", "doc_type", "country", "section_title", "chunk_index"]
        schema_fields = self.collection_fields()
        if "chunk_id" in schema_fields:
            fields.append("chunk_id")
        if "document_id" in schema_fields:
            fields.append("document_id")
        results = self._client().search(
            collection_name=COLLECTION_NAME,
            data=[query_vector],
            limit=max(top_k, top_k * limit_multiplier),
            output_fields=fields,
            search_params=SEARCH_PARAMS,
            filter=filter_expr,
        )
        if not results or not results[0]:
            return []
        normalized = []
        for hit in results[0]:
            entity = hit["entity"]
            normalized.append({
                "chunk_id": entity.get("chunk_id") or "",
                "document_id": entity.get("document_id") or "",
                "text": entity.get("text", ""),
                "doc_name": entity.get("doc_name", ""),
                "doc_type": entity.get("doc_type", ""),
                "country": entity.get("country", ""),
                "section_title": entity.get("section_title", ""),
                "chunk_index": entity.get("chunk_index", 0),
                "score": hit.get("distance"),
            })
        return normalized

    def delete_document_vectors(self, document: dict) -> None:
        fields = self.collection_fields()
        if "document_id" in fields:
            expr = f'document_id == "{escape_milvus_string(document["id"])}"'
        else:
            expr = f'doc_name == "{escape_milvus_string(document["doc_name"])}"'
        self._client().delete(collection_name=COLLECTION_NAME, filter=expr)

    def delete_chunk(self, chunk: dict) -> None:
        fields = self.collection_fields()
        if "chunk_id" in fields:
            expr = f'chunk_id == "{escape_milvus_string(chunk["chunk_id"])}"'
        else:
            expr = (
                f'doc_name == "{escape_milvus_string(chunk["doc_name"])}" '
                f'and chunk_index == {int(chunk["chunk_index"])}'
            )
        self._client().delete(collection_name=COLLECTION_NAME, filter=expr)
