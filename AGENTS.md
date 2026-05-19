# Repository Guidelines

## Project Structure & Module Organization

Quarantine-Rag is a script-based Python RAG project for pet import/export quarantine policy documents. Raw source files live in `政策法规文档/` and should be treated as input data. Converted text and chunk output live in `data/txt/` and `data/chunks.json`. The local Milvus Lite database is stored in `milvus_quarantine.db/`.

Core code is organized as direct-entry scripts under `scripts/`: `01_convert_docs.py`, `02_chunk_documents.py`, `03_create_collection.py`, `04_embed_and_insert.py`, `05_search.py`, and `06_chat.py`. Shared settings are in `config/settings.py`; design notes are in `docs/`.

## Build, Test, and Development Commands

Create an environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the full local pipeline:

```bash
python scripts/01_convert_docs.py
python scripts/02_chunk_documents.py
python scripts/03_create_collection.py
python scripts/04_embed_and_insert.py
```

Use `python scripts/05_search.py` for interactive semantic search and `python scripts/06_chat.py` for RAG chat. `03_create_collection.py` recreates the collection, so avoid running it when preserving the current local database matters.

## Coding Style & Naming Conventions

Use Python 3 with 4-space indentation and standard type hints where they clarify interfaces. Keep scripts runnable from the repository root; current scripts add the project root to `sys.path` manually. Follow the numbered script naming pattern for pipeline stages. Keep configuration constants uppercase in `config/settings.py`.

When changing chunk metadata, preserve the downstream contract: `text`, `doc_name`, `doc_type`, `country`, `chunk_index`, and `section_title`.

## Testing Guidelines

There is no formal test suite yet. Validate changes with targeted runtime checks:

```bash
python -c "from config.settings import COLLECTION_NAME, VECTOR_DIM; print(COLLECTION_NAME, VECTOR_DIM)"
python scripts/02_chunk_documents.py
python scripts/05_search.py
```

For embedding, search, rerank, or chat changes, verify behavior with a real `ZHIPU_API_KEY` in `.env`. For schema or vector-dimension changes, rebuild the Milvus collection and reinsert all vectors.

## Commit & Pull Request Guidelines

This directory currently has no local Git history, so no repository-specific commit convention is established. Use concise imperative commit subjects such as `Add chunk metadata validation` or `Update Milvus search filters`.

Pull requests should describe the changed pipeline stage, list any regenerated files under `data/` or `milvus_quarantine.db/`, and include manual verification commands. Include screenshots or terminal snippets only when they clarify CLI output or retrieval behavior.

## Security & Configuration Tips

Store secrets only in `.env`; never commit real API keys. `ZHIPU_API_KEY` is required for embedding, rerank, and chat. Document conversion relies on macOS `textutil` for Word files and `xlrd` for `.xls` files.
