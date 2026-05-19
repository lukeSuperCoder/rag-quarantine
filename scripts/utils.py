"""公共工具函数"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import MILVUS_DB_PATH, COLLECTION_NAME
from pymilvus import MilvusClient


def get_client() -> MilvusClient:
    return MilvusClient(MILVUS_DB_PATH)


def get_collection_stats():
    """获取集合统计信息"""
    client = get_client()
    if not client.has_collection(COLLECTION_NAME):
        print(f"集合 {COLLECTION_NAME} 不存在")
        return

    info = client.describe_collection(COLLECTION_NAME)
    print(f"集合: {COLLECTION_NAME}")
    print(f"字段: {[f['name'] for f in info['fields']]}")

    count = client.query(
        collection_name=COLLECTION_NAME,
        filter="",
        output_fields=["count(*)"],
    )
    print(f"记录数: {count}")

    # 按类型统计
    types = client.query(
        collection_name=COLLECTION_NAME,
        filter="",
        output_fields=["doc_type"],
    )
    type_counts = {}
    for t in types:
        dt = t.get("doc_type", "unknown")
        type_counts[dt] = type_counts.get(dt, 0) + 1
    print("\n按类型统计:")
    for dt, cnt in sorted(type_counts.items()):
        print(f"  {dt}: {cnt}")


if __name__ == "__main__":
    get_collection_stats()
