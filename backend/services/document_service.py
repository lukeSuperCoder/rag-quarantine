"""Document upload, conversion, chunking, and indexing workflow."""
from __future__ import annotations

from pathlib import Path
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from backend.services.chunk_service import ChunkService
from backend.services.common import load_script_module, new_id
from backend.services.storage_service import StorageService
from backend.services.vector_service import VectorService
from config.settings import DATA_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONVERT_SCRIPT = PROJECT_ROOT / "scripts" / "01_convert_docs.py"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_TXT_DIR = DATA_DIR / "upload_txt"
ALLOWED_EXTENSIONS = {".doc", ".docx", ".xls"}


class DocumentService:
    def __init__(self):
        self.storage = StorageService()

    def create_from_upload(self, upload: FileStorage, doc_type: str | None = None, country: str = "") -> dict:
        ext = Path(upload.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError("仅支持 .doc、.docx、.xls 文件")

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_TXT_DIR.mkdir(parents=True, exist_ok=True)

        safe_stem = secure_filename(Path(upload.filename).stem) or "upload"
        filename = f"{new_id('upload')}_{safe_stem}{ext}"
        source_path = UPLOAD_DIR / filename
        upload.save(source_path)

        doc_name = Path(upload.filename).stem.strip()
        document = self.storage.create_document(
            filename=upload.filename,
            doc_name=doc_name,
            doc_type=doc_type or "",
            country=country or "",
            source_path=str(source_path),
            status="uploaded",
        )
        try:
            self._process_document(document["id"], source_path, doc_type=doc_type, country=country)
        except Exception as exc:
            self.storage.update_document(document["id"], status="failed", error_message=str(exc))
            raise
        return self.storage.get_document(document["id"])

    def _process_document(self, document_id: str, source_path: Path, doc_type: str | None = None, country: str = "") -> None:
        convert_module = load_script_module("convert_docs_service_module", CONVERT_SCRIPT)

        self.storage.update_document(document_id, status="converting", error_message="")
        if source_path.suffix.lower() in {".doc", ".docx"}:
            txt_path = convert_module.convert_doc_docx(source_path, UPLOAD_TXT_DIR)
        else:
            txt_path = convert_module.convert_xls(source_path, UPLOAD_TXT_DIR)
        if not txt_path:
            raise RuntimeError("文档转换失败")
        self.storage.update_document(document_id, txt_path=str(txt_path), status="chunking")

        document = self.storage.get_document(document_id)
        chunks = ChunkService().chunk_file(
            Path(txt_path),
            doc_type=doc_type or document.get("doc_type") or None,
            country=country or document.get("country") or "",
            doc_name=document["doc_name"],
        )
        if not chunks:
            raise RuntimeError("文档未生成有效分块")

        chunks_for_storage = self.storage.replace_chunks(document_id, chunks)
        chunks_for_vector = []
        for chunk in chunks_for_storage:
            chunks_for_vector.append({
                "id": chunk["id"],
                "document_id": document_id,
                "text": chunk["text"],
                "doc_name": chunk["doc_name"],
                "doc_type": chunk["doc_type"],
                "country": chunk["country"],
                "chunk_index": chunk["chunk_index"],
                "section_title": chunk["section_title"],
            })

        self.storage.update_document(document_id, status="embedding")
        VectorService().upsert_chunks(chunks_for_vector)
        first_chunk = chunks_for_storage[0]
        self.storage.update_document(
            document_id,
            status="ready",
            doc_type=first_chunk.get("doc_type", ""),
            country=first_chunk.get("country", ""),
            error_message="",
        )

    def list_documents(self, status: str | None = None, keyword: str | None = None) -> list[dict]:
        return self.storage.list_documents(status=status, keyword=keyword)

    def get_document_detail(self, document_id: str) -> dict | None:
        document = self.storage.get_document(document_id)
        if not document:
            return None
        preview = ""
        txt_path = document.get("txt_path")
        if txt_path and Path(txt_path).exists():
            preview = Path(txt_path).read_text(encoding="utf-8", errors="ignore")[:1000]
        document["txt_preview"] = preview
        return document

    def delete_document(self, document_id: str) -> bool:
        document = self.storage.get_document(document_id)
        if not document:
            return False
        VectorService().delete_document_vectors(document)
        return self.storage.delete_document(document_id)
