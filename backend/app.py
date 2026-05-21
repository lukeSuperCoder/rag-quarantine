"""Flask application entrypoint for the intelligent QA backend."""
from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask
from flask_cors import CORS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.chat import chat_bp
from backend.api.documents import documents_bp
from backend.api.health import health_bp
from backend.api.knowledge import knowledge_bp
from backend.db.init_db import init_db
from backend.services.storage_service import StorageService


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    CORS(app)

    init_db()
    StorageService().bootstrap_from_chunks_file()

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(documents_bp, url_prefix="/api/documents")
    app.register_blueprint(knowledge_bp, url_prefix="/api/knowledge")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True, use_reloader=False, threaded=True)
