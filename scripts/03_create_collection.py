"""创建 Milvus 集合"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import (
    MILVUS_DB_PATH, COLLECTION_NAME, VECTOR_DIM,
    INDEX_PARAMS,
)
from pymilvus import MilvusClient, DataType


def main():
    client = MilvusClient(MILVUS_DB_PATH)

    # 删除已有同名集合（开发阶段）
    if client.has_collection(COLLECTION_NAME):
        client.drop_collection(COLLECTION_NAME)
        print(f"已删除旧集合: {COLLECTION_NAME}")

    # 创建 schema
    schema = client.create_schema(auto_id=True, enable_dynamic_field=False)
    schema.add_field("id", DataType.INT64, is_primary=True)
    schema.add_field("text", DataType.VARCHAR, max_length=4096)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=VECTOR_DIM)
    schema.add_field("doc_name", DataType.VARCHAR, max_length=256)
    schema.add_field("doc_type", DataType.VARCHAR, max_length=64)
    schema.add_field("country", DataType.VARCHAR, max_length=64)
    schema.add_field("chunk_index", DataType.INT32)
    schema.add_field("section_title", DataType.VARCHAR, max_length=256)

    # 创建索引
    index_params = client.prepare_index_params()
    index_params.add_index("vector", **INDEX_PARAMS)

    # 创建集合
    client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
        index_params=index_params,
    )

    info = client.describe_collection(COLLECTION_NAME)
    print(f"集合创建成功: {COLLECTION_NAME}")
    print(f"  向量维度: {VECTOR_DIM}")
    print(f"  字段: {[f['name'] for f in info['fields']]}")


if __name__ == "__main__":
    main()
