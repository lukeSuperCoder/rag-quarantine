# Quarantine-Rag

Quarantine-Rag 是一个面向宠物出入境检疫政策法规文档的本地 RAG 项目。项目将 `政策法规文档/` 中的 Word、Excel 原始资料转换为文本，按政策语义分块，使用智谱 `embedding-3` 生成向量，并写入本地 Milvus Lite 数据库，最后提供语义检索和法规问答能力。

## 功能概览

- 支持 `.doc`、`.docx`、`.xls` 政策资料转换为纯文本。
- 按文档类型执行差异化分块，保留 `doc_name`、`doc_type`、`country`、`section_title` 等元数据。
- 使用智谱 `embedding-3` 生成 2048 维向量。
- 使用 Milvus Lite 本地数据库存储和检索政策片段。
- 支持按文档类型、国家或地区过滤检索。
- 支持 RAG 对话，并可开启重排序；当重排序分数区分度过低时会自动回退原始向量排序，避免错误重排。

## 项目结构

```text
Quarantine-Rag/
├── AGENTS.md                    # Codex/Agent 项目协作说明
├── config/
│   └── settings.py              # 路径、模型、Milvus 索引和搜索配置
├── docs/
│   ├── milvus数据库设计需求.md
│   └── milvus数据库设计技术方案.md
├── scripts/
│   ├── 01_convert_docs.py       # 原始文档转 txt
│   ├── 02_chunk_documents.py    # 文本清洗和分块
│   ├── 03_create_collection.py  # 创建或重建 Milvus collection
│   ├── 04_embed_and_insert.py   # 向量化并写入 Milvus
│   ├── 05_search.py             # 交互式语义检索
│   ├── 06_chat.py               # RAG 对话
│   └── utils.py                 # 公共工具
├── 政策法规文档/                 # 原始政策法规资料
├── requirements.txt
└── .gitignore
```

以下目录为本地生成或敏感内容，默认不提交：

```text
.env
.venv/
data/
milvus_quarantine.db/
milvus_quarantine_demo.db/
__pycache__/
.claude/
```

## 环境准备

项目依赖 Python 3 和 macOS `textutil`。其中 `.doc/.docx` 转换依赖 macOS 系统自带 `textutil`，`.xls` 转换依赖 `xlrd`。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

在项目根目录创建 `.env`：

```bash
ZHIPU_API_KEY=你的智谱API密钥
```

`ZHIPU_API_KEY` 用于 embedding、重排序和 RAG 对话，不能提交到 Git。

## 运行完整流水线

从原始文档开始重建本地检索库：

```bash
python scripts/01_convert_docs.py
python scripts/02_chunk_documents.py
python scripts/03_create_collection.py
python scripts/04_embed_and_insert.py
```

注意：`scripts/03_create_collection.py` 会重建 Milvus collection。如果需要保留当前本地数据库，不要直接运行该脚本。

## 交互式检索

```bash
python scripts/05_search.py
```

支持命令：

```text
/filter <doc_type>   设置文档类型过滤
/country <country>   设置国家或地区过滤
/rerank              开关重排序
/topk <n>            设置返回数量
q                    退出
```

示例问题：

```text
宠物入境中国需要隔离多久？
从日本带犬猫入境中国有什么要求？
赴美国犬检疫需要哪些材料？
```

## RAG 对话

```bash
python scripts/06_chat.py
```

支持命令：

```text
/rerank   开关重排序
/topk <n> 设置检索数量
c         清空对话历史
q         退出
```

`06_chat.py` 的回答会基于检索到的政策片段生成，并要求引用具体政策文件或条款。重排序开启后会多取候选片段再调用智谱 rerank；如果 rerank 返回分数几乎没有区分度，会自动使用原始向量检索顺序。

## 数据与配置

核心配置位于 `config/settings.py`：

```python
COLLECTION_NAME = "quarantine_policies"
VECTOR_DIM = 2048
EMBEDDING_MODEL = "embedding-3"
```

Milvus 使用本地文件模式：

```python
MILVUS_DB_PATH = "milvus_quarantine.db"
```

默认向量索引为 HNSW，距离度量为 COSINE，适合当前小规模政策文档检索场景。

## 分块元数据约定

下游检索和问答依赖以下字段，请修改分块逻辑时保持兼容：

```text
text
doc_name
doc_type
country
chunk_index
section_title
```

当前主要 `doc_type` 包括：

```text
country_export_req
entry_regulation
reference_list
legal_text
form_template
operation_manual
```

## 常用验证命令

```bash
python -c "from config.settings import COLLECTION_NAME, VECTOR_DIM; print(COLLECTION_NAME, VECTOR_DIM)"
python scripts/02_chunk_documents.py
python scripts/05_search.py
python scripts/06_chat.py
```

如果修改了 schema、向量维度、embedding 模型或分块字段，需要重新创建 collection 并重新写入向量。

