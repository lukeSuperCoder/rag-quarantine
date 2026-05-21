"""Text chunking service wrapping the existing chunking script."""
from __future__ import annotations

from pathlib import Path

from backend.services.common import load_script_module

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNK_SCRIPT = PROJECT_ROOT / "scripts" / "02_chunk_documents.py"


class ChunkService:
    def __init__(self):
        self._module = load_script_module("chunk_documents_service_module", CHUNK_SCRIPT)

    def chunk_file(self, txt_path: Path, doc_type: str | None = None, country: str = "", doc_name: str | None = None) -> list[dict]:
        doc_name = doc_name or txt_path.stem.strip()
        text = self._module.clean_text(txt_path.read_text(encoding="utf-8"))

        if not doc_type:
            doc_type, inferred_country = self._module.get_doc_meta(txt_path.name)
            country = country or inferred_country

        if doc_type == "country_export_req":
            chunks = self._module.chunk_country_export(text, doc_name, doc_type, country)
        elif doc_type == "entry_regulation":
            chunks = self._module.chunk_entry_regulation(text, doc_name, doc_type, country)
        elif doc_type == "reference_list":
            if "64号" in doc_name:
                chunks = self._module.chunk_reference_list_lab64(text, doc_name, doc_type, country)
            elif "采信" in doc_name:
                chunks = self._module.chunk_reference_list_designated(text, doc_name, doc_type, country)
            elif "口岸" in doc_name:
                chunks = self._module.chunk_reference_list_port(text, doc_name, doc_type, country)
            elif "隔离场地" in doc_name:
                chunks = self._module.chunk_reference_list_isolation(text, doc_name, doc_type, country)
            else:
                chunks = self._module.chunk_by_paragraphs(text, doc_name, doc_type, country)
        elif doc_type == "legal_text":
            chunks = self._module.chunk_legal_text(text, doc_name, doc_type, country)
        elif doc_type == "form_template":
            chunks = self._module.chunk_form_template(text, doc_name, doc_type, country)
        elif doc_type == "operation_manual":
            chunks = self._module.chunk_operation_manual(text, doc_name, doc_type, country)
        else:
            chunks = self._module.chunk_by_paragraphs(text, doc_name, doc_type or "unknown", country)

        return chunks
