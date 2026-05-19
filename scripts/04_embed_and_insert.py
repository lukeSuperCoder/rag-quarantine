"""向量化写入：调用智谱 embedding-3 + 写入 Milvus"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import (
    MILVUS_DB_PATH, COLLECTION_NAME, EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE, EMBEDDING_INTERVAL, CHUNKS_FILE,
    ZHIPU_API_KEY,
)
from pymilvus import MilvusClient
from zai import ZhipuAiClient


def get_embeddings_batch(client: ZhipuAiClient, texts: list[str]) -> list[list[float]]:
    """批量获取向量"""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def main():
    if not ZHIPU_API_KEY or ZHIPU_API_KEY == "your_api_key_here":
        print("错误: 请先在 .env 文件中设置 ZHIPU_API_KEY")
        sys.exit(1)

    # 加载分块数据
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"加载 {len(chunks)} 个分块")

    # 初始化客户端
    zhipu = ZhipuAiClient(api_key=ZHIPU_API_KEY)
    milvus = MilvusClient(MILVUS_DB_PATH)

    # 批量处理
    total = len(chunks)
    inserted = 0

    for i in range(0, total, EMBEDDING_BATCH_SIZE):
        batch = chunks[i : i + EMBEDDING_BATCH_SIZE]
        texts = [c["text"] for c in batch]

        print(f"  处理 {i + 1}-{min(i + EMBEDDING_BATCH_SIZE, total)}/{total}...", end=" ", flush=True)

        try:
            vectors = get_embeddings_batch(zhipu, texts)
        except Exception as e:
            print(f"嵌入失败: {e}")
            # 逐条重试
            vectors = []
            for text in texts:
                try:
                    vec = get_embeddings_batch(zhipu, [text])
                    vectors.append(vec[0])
                except Exception as e2:
                    print(f"\n  跳过失败文本: {e2}")
                    vectors.append([0.0] * 2048)

        # 构建写入数据
        data = []
        for j, chunk in enumerate(batch):
            data.append({
                "text": chunk["text"][:4096],
                "vector": vectors[j],
                "doc_name": chunk["doc_name"][:256],
                "doc_type": chunk["doc_type"][:64],
                "country": chunk["country"][:64],
                "chunk_index": chunk["chunk_index"],
                "section_title": (chunk.get("section_title") or "")[:256],
            })

        milvus.insert(collection_name=COLLECTION_NAME, data=data)
        inserted += len(data)
        print(f"已写入 {inserted}/{total}")

        if i + EMBEDDING_BATCH_SIZE < total:
            time.sleep(EMBEDDING_INTERVAL)

    print(f"\n写入完成: 共 {inserted} 条记录")


if __name__ == "__main__":
    main()
