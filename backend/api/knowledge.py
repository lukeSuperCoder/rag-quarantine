"""Knowledge-base query and chunk management API routes."""
from __future__ import annotations

from flask import Blueprint, request

from backend.api.common import fail, ok
from backend.services.knowledge_service import KnowledgeService

knowledge_bp = Blueprint("knowledge", __name__)


@knowledge_bp.get("/search")
def search_knowledge():
    keyword = (request.args.get("keyword") or "").strip()
    if not keyword:
        return fail(4001, "keyword 不能为空")
    limit = request.args.get("limit", "20")
    try:
        limit_num = max(1, min(int(limit), 100))
    except ValueError:
        return fail(4001, "limit 必须是数字")

    items = KnowledgeService().search(
        keyword=keyword,
        doc_type=request.args.get("doc_type") or None,
        country=request.args.get("country") or None,
        limit=limit_num,
    )
    return ok({"items": items})


@knowledge_bp.get("/chunks/<chunk_id>")
def get_chunk(chunk_id: str):
    chunk = KnowledgeService().get_chunk(chunk_id)
    if not chunk:
        return fail(4003, "chunk 不存在", status=404)
    return ok(chunk)


@knowledge_bp.put("/chunks/<chunk_id>")
def update_chunk(chunk_id: str):
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return fail(4001, "text 不能为空")
    try:
        result = KnowledgeService().update_chunk_text(chunk_id, text)
    except LookupError:
        return fail(4003, "chunk 不存在", status=404)
    except Exception as exc:
        return fail(5002, f"更新向量失败: {exc}", status=500)
    return ok(result)
