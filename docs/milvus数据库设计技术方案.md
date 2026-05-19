# Quarantine-Rag 技术方案

## 1. 项目概述

### 1.1 背景

为宠物出入境检疫政策法规文档构建 RAG（Retrieval-Augmented Generation）系统。系统将 14 份政策法规文档（.doc/.docx/.xls）经过文本转换、智能分块、向量化后写入 Milvus Lite 向量数据库，支撑后续的智能检索与问答场景。

### 1.2 目标

- 将 14 份异构文档统一转换为结构化文本并分块
- 使用智谱 embedding-3 模型（2048 维）生成向量嵌入
- 基于 Milvus Lite 构建本地向量检索服务
- 支持按文档类型、国家等元数据过滤检索
- 为后续 LLM 问答提供高质量上下文

### 1.3 文档清单与分类

| 文档名称 | 格式 | doc_type | country | 说明 |
|---------|------|----------|---------|------|
| 赴英国犬猫检疫要求.docx | docx | country_export_req | 英国 | 出口检疫要求 |
| 赴日本犬猫检疫要求.docx | docx | country_export_req | 日本 | 出口检疫要求 |
| 赴美国犬检疫要求.docx | docx | country_export_req | 美国 | 出口检疫要求 |
| 赴欧盟犬猫检疫要求.docx | docx | country_export_req | 欧盟 | 出口检疫要求 |
| 海关总署公告2019年第5号.doc | doc | entry_regulation | — | 携带宠物入境检疫监管公告 |
| 中华人民共和国携带宠物入境检疫要求.doc | doc | entry_regulation | — | 入境检疫要求 |
| 海关总署采信狂犬病抗体检测结果的实验室名单.doc | doc | reference_list | — | 采信实验室名单 |
| 海关总署公告2019年第64号.docx | docx | reference_list | — | 更新采信实验室名单 |
| 进境宠物隔离场地名单.xls | xls | reference_list | — | 隔离场地名单 |
| 具备进境宠物隔离检疫条件的口岸名单.doc | doc | reference_list | — | 口岸名单 |
| 中华人民共和国海关进出境行李物品监管办法.doc | doc | legal_text | — | 海关监管办法 |
| 携带入境宠物（犬、猫）信息登记表.doc | doc | form_template | — | 登记表 |
| 海关暂不予放行旅客行李物品暂存凭单.doc | doc | form_template | — | 暂存凭单 |
| "携带出境宠物检疫"功能模块操作手册-申报端.docx | docx | operation_manual | — | 操作手册 |

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐
│  原始文档    │───>│  文本转换     │───>│  智能分块     │───>│  向量化 + 写入   │
│  doc/docx/  │    │ 01_convert   │    │ 02_chunk     │    │ 03_create +     │
│  xls        │    │ _docs.py     │    │ _documents   │    │ 04_embed_and    │
│             │    │              │    │ .py          │    │ _insert.py      │
└─────────────┘    └──────────────┘    └──────────────┘    └────────┬────────┘
                                                                       │
                                                                       ▼
                                                               ┌───────────────┐
                                                               │  Milvus Lite   │
                                                               │  (本地 SQLite  │
                                                               │   模式)        │
                                                               └───────┬───────┘
                                                                       │
                                                                       ▼
                                                                ┌──────────────┐
                                                                │  向量检索     │
                                                                │ 05_search.py │
                                                                └──────────────┘
```

### 2.2 技术选型

| 组件 | 选型 | 版本 | 说明 |
|------|------|------|------|
| 向量数据库 | Milvus Lite | pymilvus 3.0.0 | 本地嵌入式，无需部署服务 |
| Embedding | 智谱 embedding-3 | zai-sdk ≥ 0.2.2 | 2048 维，中文效果好 |
| 文档解析 | macOS textutil + xlrd | xlrd ≥ 2.0.1 | 原生 doc 转换 + Excel 读取 |
| 配置管理 | python-dotenv | ≥ 1.0.0 | .env 管理密钥 |

### 2.3 为什么选择 Milvus Lite

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **Milvus Lite（选择）** | 零部署，本地文件，开发调试方便 | 不支持分布式，单机性能有限 | 开发阶段、小规模数据（<100万条） |
| Docker Milvus Standalone | 完整功能，接近生产环境 | 需要容器环境，资源占用较大 | 中等规模、团队共享 |
| Milvus Distributed | 高可用，水平扩展 | 运维复杂，依赖组件多 | 生产环境、大规模数据 |

本项目数据量约 200-500 条分块记录，Milvus Lite 完全满足需求。后续如需升级，只需将连接方式从本地文件切换为 `uri="http://localhost:19530"` 即可连接 Docker 或分布式 Milvus。

## 3. 项目结构

```
Quarantine-Rag/
├── 政策法规文档/                 # 原始文档（只读，不做修改）
├── data/
│   ├── txt/                     # 转换后的纯文本文件
│   └── chunks.json              # 分块结果（中间产物）
├── config/
│   └── settings.py              # 全局配置（路径、模型参数、索引配置）
├── scripts/
│   ├── 01_convert_docs.py       # 文档格式转换
│   ├── 02_chunk_documents.py    # 智能分块
│   ├── 03_create_collection.py  # 创建 Milvus 集合
│   ├── 04_embed_and_insert.py   # 向量化写入
│   ├── 05_search.py             # 向量检索
│   └── utils.py                 # 公共工具函数
├── docs/                        # 项目文档
├── .env                         # API 密钥（不提交）
├── .gitignore
└── requirements.txt
```

## 4. 数据库设计

### 4.1 集合 Schema

集合名：`quarantine_policies`

| 字段 | 类型 | 说明 | 是否索引 |
|------|------|------|---------|
| id | INT64 (auto_id) | 主键，自增 | 主键索引 |
| text | VARCHAR(4096) | 分块后的文本内容 | — |
| vector | FLOAT_VECTOR(2048) | embedding-3 向量 | HNSW 向量索引 |
| doc_name | VARCHAR(256) | 源文档文件名 | — |
| doc_type | VARCHAR(64) | 文档分类 | 标量索引 |
| country | VARCHAR(64) | 国家/地区（仅出口要求类文档有值） | 标量索引 |
| chunk_index | INT32 | 文档内分块序号 | — |
| section_title | VARCHAR(256) | 章节标题 | — |

### 4.2 索引设计

```python
# 向量索引 — HNSW（适合中小规模，召回率高）
INDEX_PARAMS = {
    "metric_type": "COSINE",      # 余弦相似度
    "index_type": "HNSW",
    "params": {"M": 16, "efConstruction": 256},
}

# 搜索参数
SEARCH_PARAMS = {
    "metric_type": "COSINE",
    "params": {"ef": 64},
}

# 标量索引 — 支持按 doc_type 和 country 过滤
# doc_type: 支持精确匹配过滤
# country: 支持精确匹配过滤
```

**索引选择理由：**
- HNSW：适合中小规模数据的近似最近邻搜索，召回率高，查询延迟低
- COSINE 度量：embedding-3 模型输出已归一化，余弦相似度适合语义匹配
- 标量索引：支持 `doc_type == "country_export_req" and country == "英国"` 类型的组合过滤

### 4.3 存储方式

使用 Milvus Lite 本地文件模式：
```python
from pymilvus import MilvusClient
client = MilvusClient("./milvus_quarantine.db")  # 本地 SQLite 存储
```

## 5. 分块策略

### 5.1 总体原则

- 最大分块长度：1500 字（超出则截断）
- 最小分块长度：50 字（过短则合并到上一块）
- 每个分块保留源文档标题作为上下文
- 分块时尽量保持语义完整性，不跨章节切割

### 5.2 按文档类型的分块策略

#### country_export_req（赴英国/日本/美国/欧盟检疫要求）

```
策略：按条目分块
粒度：每个要求条目（芯片植入、疫苗接种、血清检测、隔离要求等）独立分块
目标大小：200-500 字

示例输出：
{
  "text": "【赴英国犬猫检疫要求】疫苗接种：宠物须接种狂犬病疫苗...",
  "section_title": "疫苗接种",
  "chunk_index": 2
}
```

#### entry_regulation（入境检疫法规）

```
策略：按编号小节分块
粒度：以"（一）（二）（三）"或"一、二、三、"为分界点
目标大小：300-800 字
```

#### reference_list（实验室/口岸/隔离场名单）

```
策略：每条记录一个 chunk
粒度：名单中每条记录独立分块，加上文档标题作为前缀
目标大小：按条目自然长度

示例输出：
{
  "text": "【海关总署采信狂犬病抗体检测实验室名单】1. 中国农业大学兽医学院...",
  "section_title": "中国农业大学兽医学院",
  "chunk_index": 0
}
```

#### legal_text（海关监管办法）

```
策略：按条文分块
粒度：关联条文合并（如第二条和其解释性内容合并）
目标大小：200-600 字
```

#### form_template（表单模板）

```
策略：按区域分块
粒度：表单分为"字段描述"和"注意事项"两类分块
目标大小：按区域自然长度
```

#### operation_manual（操作手册）

```
策略：按章节分块
粒度：以章节标题为分界点
目标大小：500-1000 字
```

### 5.3 分块输出格式

`data/chunks.json` 中每条记录的结构：

```json
{
  "text": "分块文本内容...",
  "doc_name": "赴英国犬猫检疫要求.docx",
  "doc_type": "country_export_req",
  "country": "英国",
  "chunk_index": 0,
  "section_title": "疫苗接种"
}
```

## 6. 各模块详细设计

### 6.1 文档转换模块（01_convert_docs.py）

**输入：** `政策法规文档/` 目录下的 .doc/.docx/.xls 文件
**输出：** `data/txt/` 目录下的 .txt 文件

转换规则：
- `.doc/.docx`：使用 macOS 原生 `textutil -convert txt` 命令转换，保留段落结构
- `.xls`：使用 Python xlrd 库读取，按行拼接为文本

```python
# .doc/.docx 转换
textutil -convert txt -output data/txt/xxx.txt "政策法规文档/xxx.docx"

# .xls 转换
import xlrd
workbook = xlrd.open_workbook("政策法规文档/xxx.xls")
# 逐行读取，拼接为文本
```

### 6.2 智能分块模块（02_chunk_documents.py）

**输入：** `data/txt/` 下的 .txt 文件
**输出：** `data/chunks.json`

处理流程：
1. 读取 `settings.py` 中的文档分类映射（doc_name → doc_type, country）
2. 根据文件名匹配分类
3. 按分类应用对应分块策略
4. 校验分块质量（长度检查、空块过滤）
5. 输出 JSON 文件

### 6.3 集合创建模块（03_create_collection.py）

**输入：** `config/settings.py` 中的配置
**输出：** Milvus Lite 数据库文件

```python
from pymilvus import MilvusClient, DataType

client = MilvusClient("./milvus_quarantine.db")

# 定义 Schema
schema = client.create_schema(auto_id=True, enable_dynamic_field=False)
schema.add_field("id", DataType.INT64, is_primary=True)
schema.add_field("text", DataType.VARCHAR, max_length=4096)
schema.add_field("vector", DataType.FLOAT_VECTOR, dim=2048)
schema.add_field("doc_name", DataType.VARCHAR, max_length=256)
schema.add_field("doc_type", DataType.VARCHAR, max_length=64)
schema.add_field("country", DataType.VARCHAR, max_length=64)
schema.add_field("chunk_index", DataType.INT32)
schema.add_field("section_title", DataType.VARCHAR, max_length=256)

# 创建集合 + 索引
client.create_collection(
    collection_name="quarantine_policies",
    schema=schema,
)
client.create_index(
    collection_name="quarantine_policies",
    field_name="vector",
    index_params=INDEX_PARAMS,
)
```

### 6.4 向量化写入模块（04_embed_and_insert.py）

**输入：** `data/chunks.json`
**输出：** Milvus 集合中的向量数据

处理流程：
1. 读取 chunks.json
2. 批量调用智谱 embedding-3（每批 10 条，批次间隔 0.5s，避免限流）
3. 将向量与元数据组装后写入 Milvus
4. 输出写入统计信息

```python
from zai import ZhipuAiClient

client = ZhipuAiClient(api_key=ZHIPU_API_KEY)

response = client.embeddings.create(
    model="embedding-3",
    input=batch_texts,  # 最多 10 条
)
vectors = [item.embedding for item in response.data]
```

### 6.5 检索模块（05_search.py）

**输入：** 用户查询文本（+ 可选过滤条件）
**输出：** Top-K 相关分块及元数据

```python
results = client.search(
    collection_name="quarantine_policies",
    data=[query_vector],
    limit=5,
    output_fields=["text", "doc_name", "doc_type", "country", "section_title"],
    filter='doc_type == "country_export_req" and country == "英国"',
    search_params=SEARCH_PARAMS,
)
```

支持的功能：
- 纯语义检索（无过滤）
- 按文档类型过滤
- 按国家/地区过滤
- 组合过滤

## 7. 依赖与环境

### 7.1 Python 依赖

```
pymilvus==3.0.0
zai-sdk>=0.2.2
xlrd>=2.0.1
python-dotenv>=1.0.0
```

### 7.2 系统依赖

- macOS（使用 textutil 转换 doc/docx）
- Python 3.9+

### 7.3 环境变量

```bash
# .env
ZHIPU_API_KEY=your_api_key_here
```

## 8. 实施步骤与里程碑

| 阶段 | 步骤 | 产出 | 预计耗时 |
|------|------|------|---------|
| Step 1 | 基础设施搭建 | config/settings.py, .env, .gitignore, requirements.txt | 已完成 |
| Step 2 | 文档转换 | data/txt/ 下 14 个 txt 文件 | 0.5h |
| Step 3 | 文本分块 | data/chunks.json（预计 200-500 条） | 1h |
| Step 4 | 创建集合 | milvus_quarantine.db | 0.5h |
| Step 5 | 向量化写入 | 集合内数据就绪 | 1h |
| Step 6 | 检索演示 | 05_search.py 可用 | 0.5h |
| Step 7 | 验证优化 | 端到端验证通过 | 1h |

## 9. 验证方案

### 9.1 各步骤验证

| 步骤 | 验证方法 | 通过标准 |
|------|---------|---------|
| 文档转换 | 检查 data/txt/ 文件数 | 14 个 txt 文件，内容可读 |
| 分块 | 检查 chunks.json 条数 | 200-500 条，抽检分块质量 |
| 集合创建 | describe_collection() | 字段和索引符合设计 |
| 写入 | query() 统计 | 记录数 = chunks 条数 |
| 检索 | 用已知问题测试 | 结果相关且准确 |

### 9.2 检索测试用例

| 查询 | 期望命中文档类型 | 期望命中 country |
|------|-----------------|-----------------|
| 带猫去英国需要什么手续 | country_export_req | 英国 |
| 狂犬病抗体检测要去哪个实验室 | reference_list | — |
| 入境宠物需要隔离吗 | entry_regulation | — |
| 海关监管办法对携带宠物有什么规定 | legal_text | — |
| 日本对犬的芯片有什么要求 | country_export_req | 日本 |

## 10. 后续扩展方向

- **LLM 问答集成：** 基于检索结果调用智谱 GLM-4 生成自然语言回答
- **重排序优化：** 使用智谱重排序模型对检索结果二次排序
- **Web 界面：** 构建 Streamlit/Gradio 交互界面
- **生产部署：** 从 Milvus Lite 切换到 Docker Milvus Standalone
- **增量更新：** 支持新文档的增量分块和写入
