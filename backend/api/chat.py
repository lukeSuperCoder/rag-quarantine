"""Chat session and streaming RAG API routes."""
from __future__ import annotations

import json

from flask import Blueprint, Response, request

from backend.api.common import fail, ok
from backend.services.rag_service import RagService
from backend.services.storage_service import StorageService

chat_bp = Blueprint("chat", __name__)


@chat_bp.post("/sessions")
def create_session():
    payload = request.get_json(silent=True) or {}
    session = StorageService().create_session(title=payload.get("title") or "新会话")
    return ok(session)


@chat_bp.get("/sessions")
def list_sessions():
    return ok({"items": StorageService().list_sessions()})


@chat_bp.put("/sessions/<session_id>")
def update_session(session_id: str):
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    if not title:
        return fail(4001, "标题不能为空")
    session = StorageService().update_session(session_id, title)
    if not session:
        return fail(4003, "会话不存在", status=404)
    return ok(session)


@chat_bp.delete("/sessions/<session_id>")
def delete_session(session_id: str):
    if not StorageService().delete_session(session_id):
        return fail(4003, "会话不存在", status=404)
    return ok({"deleted": True})


@chat_bp.get("/sessions/<session_id>/messages")
def list_messages(session_id: str):
    storage = StorageService()
    if not storage.get_session(session_id):
        return fail(4003, "会话不存在", status=404)
    return ok({"items": storage.list_messages(session_id)})


@chat_bp.post("/stream")
def stream_chat():
    payload = request.get_json(silent=True) or {}
    session_id = payload.get("session_id")
    question = (payload.get("question") or "").strip()
    if not session_id:
        return fail(4001, "session_id 不能为空")
    if not question:
        return fail(4001, "question 不能为空")
    if not StorageService().get_session(session_id):
        return fail(4003, "会话不存在", status=404)

    options = {
        "top_k": int(payload.get("top_k") or 5),
        "rerank": bool(payload.get("rerank", False)),
        "temperature": float(payload.get("temperature") or 0.7),
        "max_history": int(payload.get("max_history") or 20),
    }

    def event_stream():
        for event_name, data in RagService().stream_answer(session_id, question, **options):
            yield f"event: {event_name}\n"
            yield "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"

    return Response(event_stream(), mimetype="text/event-stream")
