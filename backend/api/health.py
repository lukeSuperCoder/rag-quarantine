"""Health check routes."""
from __future__ import annotations

from flask import Blueprint

from backend.api.common import ok
from backend.services.storage_service import StorageService
from backend.services.vector_service import VectorService
from config.settings import ZHIPU_API_KEY

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    sqlite_status = "ok" if StorageService().healthcheck() else "error"
    milvus_status = "ok" if VectorService().healthcheck() else "error"
    api_key_status = "configured" if ZHIPU_API_KEY and ZHIPU_API_KEY != "your_api_key_here" else "missing"
    return ok({
        "service": "ok",
        "sqlite": sqlite_status,
        "milvus": milvus_status,
        "zhipu_api_key": api_key_status,
    })
