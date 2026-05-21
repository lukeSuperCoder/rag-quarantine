"""Document management API routes."""
from __future__ import annotations

from flask import Blueprint, request

from backend.api.common import fail, ok
from backend.services.document_service import DocumentService

documents_bp = Blueprint("documents", __name__)


@documents_bp.post("/upload")
def upload_document():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return fail(4001, "缺少上传文件")

    service = DocumentService()
    try:
        document = service.create_from_upload(
            upload,
            doc_type=request.form.get("doc_type") or None,
            country=request.form.get("country") or "",
        )
        return ok({
            "document_id": document["id"],
            "filename": document["filename"],
            "status": document["status"],
        })
    except ValueError as exc:
        return fail(4002, str(exc))
    except Exception as exc:
        return fail(5001, f"文档处理失败: {exc}", status=500)


@documents_bp.get("")
def list_documents():
    service = DocumentService()
    items = service.list_documents(
        status=request.args.get("status") or None,
        keyword=request.args.get("keyword") or None,
    )
    return ok({"items": items})


@documents_bp.get("/<document_id>")
def get_document(document_id: str):
    service = DocumentService()
    document = service.get_document_detail(document_id)
    if not document:
        return fail(4003, "文档不存在", status=404)
    return ok(document)


@documents_bp.delete("/<document_id>")
def delete_document(document_id: str):
    service = DocumentService()
    deleted = service.delete_document(document_id)
    if not deleted:
        return fail(4003, "文档不存在", status=404)
    return ok({"document_id": document_id, "deleted": True})
