"""RAG 对话：Milvus 检索 + 重排序 + 智谱 GLM-5.1 对话"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import (
    MILVUS_DB_PATH, COLLECTION_NAME, EMBEDDING_MODEL,
    SEARCH_PARAMS, ZHIPU_API_KEY,
)
import requests
from pymilvus import MilvusClient
from zai import ZhipuAiClient

SYSTEM_PROMPT = """你是宠物检疫政策法规咨询助手。根据以下检索到的参考资料回答用户问题。

要求：
1. 基于参考资料中的事实回答，不要编造信息
2. 如果参考资料中没有相关内容，明确告知用户
3. 引用具体的政策文件名称或条款
4. 回答要简洁准确，重点突出"""

CHAT_MODEL = "glm-5.1"
RERANK_MODEL = "rerank"
RERANK_SCORE_EPSILON = 1e-4


class RAGChat:
    def __init__(self):
        self.zhipu = ZhipuAiClient(api_key=ZHIPU_API_KEY)
        self.milvus = MilvusClient(MILVUS_DB_PATH)
        self.milvus.load_collection(COLLECTION_NAME)

    def retrieve(self, query: str, top_k: int = 5, rerank: bool = False) -> list[str]:
        """从 Milvus 检索相关文档片段，可选重排序"""
        resp = self.zhipu.embeddings.create(model=EMBEDDING_MODEL, input=[query])
        query_vector = resp.data[0].embedding

        # 向量检索多取一些，重排序后截取 top_k
        search_limit = top_k * 2 if rerank else top_k
        results = self.milvus.search(
            collection_name=COLLECTION_NAME,
            data=[query_vector],
            limit=search_limit,
            output_fields=["text", "doc_name", "doc_type", "country", "section_title"],
            search_params=SEARCH_PARAMS,
        )

        if not results or not results[0]:
            return []

        hits = results[0]

        # 重排序
        if rerank and len(hits) > 1:
            hits = self._rerank(query, hits, top_n=top_k)

        contexts = []
        for hit in hits[:top_k]:
            e = hit["entity"]
            source = f"[来源: {e['doc_name']}"
            if e.get("section_title"):
                source += f" - {e['section_title']}"
            source += "]"
            contexts.append(f"{source}\n{e['text']}")

        return contexts

    def _rerank(self, query: str, hits: list[dict], top_n: int = 5) -> list[dict]:
        """调用智谱 rerank API 对检索结果重排序"""
        documents = [self._format_rerank_document(hit) for hit in hits]
        try:
            resp = requests.post(
                "https://open.bigmodel.cn/api/paas/v4/rerank",
                json={
                    "model": RERANK_MODEL,
                    "query": query,
                    "documents": documents,
                    # 取回全部候选，便于本地做分数退化判断和稳定排序。
                    "top_n": len(documents),
                },
                headers={
                    "Authorization": f"Bearer {ZHIPU_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            resp.raise_for_status()
            rerank_results = resp.json().get("results", [])
            if not rerank_results:
                print("  (重排序未返回结果，使用原始排序)")
                return hits[:top_n]

            scored_results = []
            for r in rerank_results:
                idx = r.get("index")
                score = r.get("relevance_score")
                if not isinstance(idx, int) or idx < 0 or idx >= len(hits):
                    continue
                if not isinstance(score, (int, float)):
                    continue
                scored_results.append((idx, float(score)))

            if not scored_results:
                print("  (重排序结果格式异常，使用原始排序)")
                return hits[:top_n]

            scores = [score for _, score in scored_results]
            if max(scores) - min(scores) < RERANK_SCORE_EPSILON:
                print("  (重排序分数区分度过低，使用原始排序)")
                return hits[:top_n]

            # 分数有效时，按 rerank 分数排序；同分时保持原始向量检索顺序。
            scored_results.sort(key=lambda item: (-item[1], item[0]))
            return [hits[idx] for idx, _ in scored_results[:top_n]]
        except Exception as e:
            print(f"  (重排序失败，使用原始排序: {e})")
            return hits[:top_n]

    @staticmethod
    def _format_rerank_document(hit: dict) -> str:
        """给 rerank 模型补充元信息，避免只看正文时混淆方向和国家。"""
        e = hit["entity"]
        metadata = [
            f"文档名称: {e.get('doc_name', '')}",
            f"文档类型: {e.get('doc_type', '')}",
            f"国家或地区: {e.get('country') or '无'}",
            f"章节标题: {e.get('section_title') or '无'}",
        ]
        return "\n".join(metadata) + f"\n正文:\n{e['text']}"

    def chat(self, query: str, history: list[dict], top_k: int = 5, rerank: bool = False) -> tuple[str, list[str]]:
        """RAG 对话：检索 + LLM 生成，返回 (回答, 检索来源列表)"""
        contexts = self.retrieve(query, top_k=top_k, rerank=rerank)

        context_text = "\n\n---\n\n".join(contexts) if contexts else "未检索到相关资料。"
        system_msg = SYSTEM_PROMPT + f"\n\n--- 参考资料 ---\n\n{context_text}"

        messages = [{"role": "system", "content": system_msg}]
        messages.extend(history)
        messages.append({"role": "user", "content": query})

        response = self.zhipu.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            max_tokens=4096,
            temperature=0.7,
        )

        return response.choices[0].message.content, contexts

    def close(self):
        self.milvus.close()


def main():
    if not ZHIPU_API_KEY or ZHIPU_API_KEY == "your_api_key_here":
        print("错误: 请先在 .env 文件中设置 ZHIPU_API_KEY")
        return

    rag = RAGChat()
    print("=== 宠物检疫政策 RAG 对话助手 ===")
    print(f"模型: {CHAT_MODEL}")
    print("输入问题开始对话，输入 q 退出，输入 c 清空历史\n")
    print("特殊命令:")
    print("  /rerank  - 开关重排序")
    print("  /topk <n>- 设置检索数量")
    print()

    history: list[dict] = []
    rerank = False
    top_k = 5

    while True:
        try:
            query = input("用户> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出")
            break

        if not query:
            continue
        if query.lower() == "q":
            break
        if query.lower() == "c":
            history.clear()
            print("  (已清空对话历史)\n")
            continue
        if query == "/rerank":
            rerank = not rerank
            print(f"  (重排序: {'开启' if rerank else '关闭'})\n")
            continue
        if query.startswith("/topk "):
            top_k = int(query[6:].strip())
            print(f"  (检索数量: {top_k})\n")
            continue

        answer, contexts = rag.chat(query, history, top_k=top_k, rerank=rerank)
        rerank_tag = " (含重排序)" if rerank else ""
        print(f"  [检索到 {len(contexts)} 条相关文档{rerank_tag}]")
        print(f"\n助手> {answer}\n")

        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})
        if len(history) > 20:
            history = history[-20:]

    rag.close()


if __name__ == "__main__":
    main()
