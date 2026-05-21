"""RAG orchestration service for chat and SSE streaming."""
from __future__ import annotations

from zai import ZhipuAiClient

from backend.services.rerank_service import RerankService
from backend.services.storage_service import StorageService
from backend.services.vector_service import VectorService
from config.settings import ZHIPU_API_KEY

SYSTEM_PROMPT = """你是宠物检疫政策法规咨询助手。根据检索到的参考资料回答用户问题。

要求：
1. 基于参考资料中的事实回答，不要编造信息。
2. 如果参考资料中没有相关内容，明确告知用户。
3. 涉及知识库事实时，引用具体政策文件名称和章节。
4. 回答简洁准确，优先给出结论。"""

CHAT_MODEL = "glm-5.1"


class RagService:
    def __init__(self):
        self.storage = StorageService()
        self.vector = VectorService()
        self.zhipu = ZhipuAiClient(api_key=ZHIPU_API_KEY) if ZHIPU_API_KEY else None

    def stream_answer(self, session_id: str, question: str, top_k: int = 5, rerank: bool = False, temperature: float = 0.7, max_history: int = 20):
        retrieval_query = self._build_retrieval_query(session_id, question)
        self.storage.add_message(session_id, "user", question)
        try:
            yield "retrieve_start", {"query": retrieval_query, "top_k": top_k, "rerank": rerank}
            hits = self.vector.search(retrieval_query, top_k=top_k, limit_multiplier=2 if rerank else 1)
            if rerank:
                hits = RerankService().rerank(retrieval_query, hits, top_n=top_k)
            else:
                hits = hits[:top_k]
            sources = [self._source_from_hit(hit) for hit in hits]
            yield "retrieve_done", {"count": len(sources)}

            answer = self._generate_answer(
                session_id=session_id,
                question=question,
                sources=sources,
                temperature=temperature,
                max_history=max_history,
            )
            for part in self._split_answer(answer):
                yield "delta", {"content": part}
            yield "sources", {"items": sources}
            message = self.storage.add_message(session_id, "assistant", answer, sources=sources)
            yield "done", {"message_id": message["id"], "session_id": session_id}
        except Exception as exc:
            yield "error", {"code": 5004, "message": str(exc)}

    def _generate_answer(self, session_id: str, question: str, sources: list[dict], temperature: float, max_history: int) -> str:
        if not self.zhipu:
            raise RuntimeError("ZHIPU_API_KEY 未配置")

        context_text = self._format_context(sources)
        messages = [{"role": "system", "content": SYSTEM_PROMPT + f"\n\n--- 参考资料 ---\n\n{context_text}"}]
        history = self.storage.recent_messages_for_model(session_id, max_history=max_history)
        if history and history[-1]["role"] == "user" and history[-1]["content"] == question:
            history = history[:-1]
        messages.extend(history)
        messages.append({"role": "user", "content": question})
        response = self.zhipu.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            max_tokens=4096,
            temperature=temperature,
        )
        return response.choices[0].message.content

    @staticmethod
    def _format_context(sources: list[dict]) -> str:
        if not sources:
            return "未检索到相关资料。"
        blocks = []
        for source in sources:
            title = f"[来源: {source['doc_name']}"
            if source.get("section_title"):
                title += f" - {source['section_title']}"
            title += f" - chunk {source['chunk_index']}]"
            blocks.append(f"{title}\n{source['text']}")
        return "\n\n---\n\n".join(blocks)

    def _build_retrieval_query(self, session_id: str, question: str) -> str:
        """Add the previous user turn to short follow-up questions for retrieval.

        The model already receives chat history, but vector retrieval needs an
        explicit query. Without this, questions like "那需要准备哪些材料？" lose the
        previous "宠物入境中国" topic and retrieve weak or empty references.
        """
        normalized = question.strip()
        if not normalized:
            return question

        follow_up_markers = ("那", "那么", "这个", "这些", "上述", "前面", "它", "其", "还需要", "需要准备")
        is_follow_up = len(normalized) <= 24 or normalized.startswith(follow_up_markers)
        if not is_follow_up:
            return question

        history = self.storage.recent_messages_for_model(session_id, max_history=8)
        previous_user_questions = [
            item["content"].strip()
            for item in history
            if item["role"] == "user" and item["content"].strip() and item["content"].strip() != normalized
        ]
        if not previous_user_questions:
            return question

        return f"{previous_user_questions[-1]} {question}"

    def _source_from_hit(self, hit: dict) -> dict:
        stored_chunk = None
        if not hit.get("chunk_id"):
            stored_chunk = self.storage.find_chunk_by_source(hit.get("doc_name", ""), hit.get("chunk_index", 0))
        return {
            "chunk_id": hit.get("chunk_id") or (stored_chunk or {}).get("chunk_id", ""),
            "document_id": hit.get("document_id") or (stored_chunk or {}).get("document_id", ""),
            "doc_name": hit.get("doc_name", ""),
            "doc_type": hit.get("doc_type", ""),
            "country": hit.get("country", ""),
            "section_title": hit.get("section_title", ""),
            "chunk_index": hit.get("chunk_index", 0),
            "score": hit.get("rerank_score", hit.get("score")),
            "text": hit.get("text", ""),
        }

    @staticmethod
    def _split_answer(answer: str, size: int = 24):
        if not answer:
            return
        for idx in range(0, len(answer), size):
            yield answer[idx:idx + size]
