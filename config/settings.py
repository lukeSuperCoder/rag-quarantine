import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TXT_DIR = DATA_DIR / "txt"
CHUNKS_FILE = DATA_DIR / "chunks.json"
DOCS_DIR = PROJECT_ROOT / "政策法规文档"

# Milvus 配置
MILVUS_DB_PATH = str(PROJECT_ROOT / "milvus_quarantine.db")
COLLECTION_NAME = "quarantine_policies"
VECTOR_DIM = 2048

# 智谱 API
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
EMBEDDING_MODEL = "embedding-3"
EMBEDDING_BATCH_SIZE = 10
EMBEDDING_INTERVAL = 0.5

# 索引配置
INDEX_PARAMS = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {"M": 16, "efConstruction": 256},
}
SEARCH_PARAMS = {
    "metric_type": "COSINE",
    "params": {"ef": 64},
}
