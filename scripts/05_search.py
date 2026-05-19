"""向量检索 + 可选重排序"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import (
    MILVUS_DB_PATH, COLLECTION_NAME, EMBEDDING_MODEL,
    SEARCH_PARAMS, ZHIPU_API_KEY,
)
from pymilvus import MilvusClient
from zai import ZhipuAiClient


def search(
    query: str,
    top_k: int = 5,
    doc_type: str | None = None,
    country: str | None = None,
    rerank: bool = False,
):
    """向量检索"""
    if not ZHIPU_API_KEY or ZHIPU_API_KEY == "your_api_key_here":
        print("错误: 请先在 .env 文件中设置 ZHIPU_API_KEY")
        return

    zhipu = ZhipuAiClient(api_key=ZHIPU_API_KEY)
    milvus = MilvusClient(MILVUS_DB_PATH)
    milvus.load_collection(COLLECTION_NAME)

    # 查询向量化
    resp = zhipu.embeddings.create(model=EMBEDDING_MODEL, input=[query])
    query_vector = resp.data[0].embedding

    # 构建 filter
    filters = []
    if doc_type:
        filters.append(f'doc_type == "{doc_type}"')
    if country:
        filters.append(f'country == "{country}"')
    filter_expr = " and ".join(filters) if filters else ""

    # 检索
    results = milvus.search(
        collection_name=COLLECTION_NAME,
        data=[query_vector],
        limit=top_k,
        output_fields=["text", "doc_name", "doc_type", "country", "section_title"],
        search_params=SEARCH_PARAMS,
        filter=filter_expr or "",
    )

    if not results or not results[0]:
        print("未找到相关结果")
        return []

    hits = results[0]

    # 可选重排序
    if rerank and len(hits) > 1:
        texts = [hit["entity"]["text"] for hit in hits]
        try:
            rerank_resp = zhipu.rerank.create(
                model="bge-reranker-v2-m3",
                query=query,
                documents=texts,
            )
            # 按重排序结果重新排列
            reranked_indices = [r.index for r in rerank_resp.results]
            hits = [hits[i] for i in reranked_indices]
        except Exception as e:
            print(f"(重排序失败，使用原始排序: {e})")

    # 输出结果
    print(f"\n查询: {query}")
    if filter_expr:
        print(f"过滤: {filter_expr}")
    print(f"返回 {len(hits)} 条结果:\n")

    for i, hit in enumerate(hits):
        entity = hit["entity"]
        score = hit["distance"]
        print(f"--- 结果 {i + 1} (相似度: {score:.4f}) ---")
        print(f"  文档: {entity['doc_name']}")
        print(f"  类型: {entity['doc_type']} | 国家: {entity['country'] or '无'}")
        print(f"  章节: {entity.get('section_title', '')}")
        print(f"  内容: {entity['text'][:200]}...")
        print()
    return hits


def main():
    print("=== 宠物检疫政策 RAG 检索 ===")
    print("输入问题进行检索，输入 q 退出\n")
    print("特殊命令:")
    print("  /filter <doc_type>  - 设置文档类型过滤")
    print("  /country <country>  - 设置国家过滤")
    print("  /rerank             - 开关重排序")
    print("  /topk <n>           - 设置返回数量")
    print()

    current_filter = {}
    rerank = False
    top_k = 5

    while True:
        try:
            query = input("查询> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出")
            break

        if not query:
            continue
        if query.lower() == "q":
            break

        if query.startswith("/filter "):
            current_filter["doc_type"] = query[8:].strip() or None
            print(f"  文档类型过滤: {current_filter.get('doc_type', '无')}")
            continue
        if query.startswith("/country "):
            current_filter["country"] = query[9:].strip() or None
            print(f"  国家过滤: {current_filter.get('country', '无')}")
            continue
        if query == "/rerank":
            rerank = not rerank
            print(f"  重排序: {'开启' if rerank else '关闭'}")
            continue
        if query.startswith("/topk "):
            top_k = int(query[6:].strip())
            print(f"  返回数量: {top_k}")
            continue

        search(
            query,
            top_k=top_k,
            doc_type=current_filter.get("doc_type"),
            country=current_filter.get("country"),
            rerank=rerank,
        )


if __name__ == "__main__":
    main()
