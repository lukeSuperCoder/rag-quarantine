# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quarantine-Rag is a RAG system for pet import/export quarantine policy documents. It processes Word/Excel documents from `政策法规文档/`, converts them to text, chunks by document type, generates embeddings via Zhipu AI, stores in Milvus Lite, and provides semantic search + multi-turn chat with reranking.

All documentation and code comments are in Chinese.

## Commands

### Python environment
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Data pipeline (run in order)
```bash
python scripts/01_convert_docs.py      # doc/docx/xls → txt (macOS textutil + xlrd)
python scripts/02_chunk_documents.py    # type-aware chunking → data/chunks.json
python scripts/03_create_collection.py  # create/recreate Milvus collection (WARNING: drops existing)
python scripts/04_embed_and_insert.py   # batch embed + insert into Milvus
```

### CLI tools
```bash
python scripts/05_search.py             # interactive semantic search with filters
python scripts/06_chat.py               # multi-turn RAG chat
```

### Backend server
```bash
python backend/app.py                   # Flask on http://127.0.0.1:8000
```

### Frontend
```bash
cd web
npm install
npm run dev                             # Vite dev server on http://127.0.0.1:5173
npm run build
```

### Validation (no formal test suite)
```bash
python -c "from config.settings import COLLECTION_NAME, VECTOR_DIM; print(COLLECTION_NAME, VECTOR_DIM)"
python scripts/02_chunk_documents.py    # re-chunk and verify output
python scripts/05_search.py             # interactive search test
```

## Architecture

### Two interfaces sharing the same services

The project has a CLI pipeline (`scripts/`) and a web application (`backend/` + `web/`), both using the same configuration and Milvus database.

### Configuration
- `config/settings.py` — all paths, Milvus params, Zhipu AI model names, index/search configs
- `.env` — `ZHIPU_API_KEY` only (required for embedding, rerank, and chat)

### Data pipeline (`scripts/`)
Numbered scripts form a linear pipeline. `utils.py` holds shared helpers. Each script adds the project root to `sys.path` and imports from `config.settings`.

### Web application
- **Backend** (`backend/`): Flask with service-layer architecture
  - `api/` — Flask blueprints: `health`, `documents`, `knowledge`, `chat`
  - `services/` — business logic: `StorageService` (SQLite), `VectorService` (Milvus), `RerankService`, `RagService` (streaming), `DocumentService`, `ChunkService`
  - `db/init_db.py` — SQLite schema bootstrap
  - On startup: `init_db()` + `StorageService.bootstrap_from_chunks_file()` imports existing `data/chunks.json`
- **Frontend** (`web/`): Vue 3 + Element Plus + Pinia
  - `views/` — ChatView, DocumentsView, KnowledgeView, SettingsView
  - `stores/` — Pinia stores per domain
  - `api/client.js` — Axios client with mock fallback, SSE streaming support

### Key design patterns
- **Document-type chunking**: `02_chunk_documents.py` uses different strategies per doc type (country export requirements, entry regulations, reference lists, legal texts, form templates, operation manuals)
- **Chunk metadata contract**: `text`, `doc_name`, `doc_type`, `country`, `chunk_index`, `section_title` — preserve these when modifying chunking
- **Rerank with fallback**: fetches 2x candidates when rerank enabled; auto-falls back to vector search on API failure or low score discrimination (< 1e-4)
- **Follow-up query enhancement**: short/ambiguous queries append previous user question for better retrieval
- **Vector config**: Zhipu `embedding-3` (2048-dim), Milvus HNSW (M=16, efConstruction=256, COSINE)

### Storage
- `milvus_quarantine.db/` — Milvus Lite local vector database
- `data/chunks.json` — intermediate chunk data
- `data/txt/` — converted plain text from source documents
- SQLite (in `backend/`) — document metadata, chat sessions/messages
