"""Lightweight in-memory embedding service used for retrieval and RAG demos."""

from __future__ import annotations

from typing import List

from models.schemas import RetrievedPrompt
from services.evaluation_service import _cosine_similarity


class _InMemoryCollection:
    def __init__(self, service: "EmbeddingService") -> None:
        self._service = service

    def count(self) -> int:
        return len(self._service._store)


class EmbeddingService:
    def __init__(self) -> None:
        self._store: List[dict] = []
        self.collection = _InMemoryCollection(self)

    async def store_session(
        self,
        session_id: str,
        prompt: str,
        best_response: str,
        best_score: float,
        feedback_rating: int,
    ) -> None:
        record = {
            "session_id": session_id,
            "prompt": prompt,
            "best_response": best_response,
            "best_score": best_score,
            "feedback_rating": feedback_rating,
        }
        self._store = [item for item in self._store if item["session_id"] != session_id]
        self._store.append(record)

    async def retrieve_similar(self, query: str, top_k: int = 3) -> List[RetrievedPrompt]:
        scored: List[RetrievedPrompt] = []
        for item in self._store:
            similarity = round(_cosine_similarity(query, item["prompt"]), 4)
            if similarity <= 0:
                continue
            scored.append(
                RetrievedPrompt(
                    session_id=item["session_id"],
                    prompt=item["prompt"],
                    best_response=item["best_response"],
                    similarity_score=similarity,
                    best_score=float(item.get("best_score", 0.0)),
                    feedback_rating=int(item.get("feedback_rating", 0)),
                )
            )

        scored.sort(key=lambda item: item.similarity_score, reverse=True)
        return scored[:top_k]

    def build_rag_context(self, similar_prompts: List[RetrievedPrompt]) -> str:
        if not similar_prompts:
            return ""

        blocks = []
        for item in similar_prompts:
            blocks.append(
                "\n".join(
                    [
                        f"Past prompt: {item.prompt}",
                        f"Helpful response: {item.best_response}",
                    ]
                )
            )
        return "Use these successful prior examples as context:\n\n" + "\n\n---\n\n".join(blocks)


embedding_service = EmbeddingService()

