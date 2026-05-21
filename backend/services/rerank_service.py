"""Rerank service with guarded fallback behavior."""
from __future__ import annotations

import requests

from config.settings import ZHIPU_API_KEY

RERANK_MODEL = "rerank"
RERANK_SCORE_EPSILON = 1e-4


class RerankService:
    def rerank(self, query: str, hits: list[dict], top_n: int) -> list[dict]:
        if not hits or len(hits) == 1:
            return hits[:top_n]

        documents = [self._format_document(hit) for hit in hits]
        try:
            resp = requests.post(
                "https://open.bigmodel.cn/api/paas/v4/rerank",
                json={
                    "model": RERANK_MODEL,
                    "query": query,
                    "documents": documents,
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
            scored = []
            for item in rerank_results:
                idx = item.get("index")
                score = item.get("relevance_score")
                if isinstance(idx, int) and 0 <= idx < len(hits) and isinstance(score, (int, float)):
                    scored.append((idx, float(score)))
            if not scored:
                return hits[:top_n]
            scores = [score for _, score in scored]
            if max(scores) - min(scores) < RERANK_SCORE_EPSILON:
                return hits[:top_n]
            scored.sort(key=lambda pair: (-pair[1], pair[0]))
            ranked = []
            for idx, score in scored[:top_n]:
                item = dict(hits[idx])
                item["rerank_score"] = score
                ranked.append(item)
            return ranked
        except Exception:
            return hits[:top_n]

    @staticmethod
    def _format_document(hit: dict) -> str:
        return "\n".join([
            f"文档名称: {hit.get('doc_name', '')}",
            f"文档类型: {hit.get('doc_type', '')}",
            f"国家或地区: {hit.get('country') or '无'}",
            f"章节标题: {hit.get('section_title') or '无'}",
            "正文:",
            hit.get("text", ""),
        ])
