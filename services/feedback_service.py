"""Feedback service that nudges ensemble weights using simple preference signals."""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Optional
from uuid import uuid4

from models.schemas import FeedbackRequest, FeedbackResponse

DEFAULT_WEIGHTS = {"rule_based": 0.20, "embedding": 0.30, "llm_judge": 0.50}
MIN_WEIGHT = 0.05
MAX_WEIGHT = 0.85
STEP_SIZE = 0.04


def _normalize(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(weights.values()) or 1.0
    normalized = {key: value / total for key, value in weights.items()}
    return {key: round(value, 6) for key, value in normalized.items()}


class FeedbackService:
    def __init__(self) -> None:
        self._weights = deepcopy(DEFAULT_WEIGHTS)
        self._records: List[dict] = []
        self._weight_history: List[Dict[str, float]] = [self.get_current_weights()]

    async def record_feedback(self, request: FeedbackRequest) -> FeedbackResponse:
        if request.score_breakdown:
            self._adjust_weights(
                {
                    str(request.selected_response_id): {
                        "rule_based_total": request.score_breakdown.rule_based_total,
                        "embedding_score": request.score_breakdown.embedding_score,
                        "llm_judge_avg": request.score_breakdown.llm_judge_avg,
                    }
                },
                request.selected_response_id,
                int(request.rating),
            )

        feedback_id = str(uuid4())
        self._records.append(
            {
                "feedback_id": feedback_id,
                "session_id": request.session_id,
                "prompt": request.prompt,
                "selected_response_id": request.selected_response_id,
                "rating": int(request.rating),
                "comment": request.comment,
            }
        )
        return FeedbackResponse(
            feedback_id=feedback_id,
            rating=request.rating,
            updated_weights=self.get_current_weights(),
            message="Feedback recorded successfully.",
        )

    def _adjust_weights(
        self,
        score_breakdown: Dict[str, dict],
        selected_response_id: int,
        rating: int,
    ) -> None:
        if rating == 0:
            return

        selected = score_breakdown.get(str(selected_response_id)) or score_breakdown.get(selected_response_id)
        if not selected:
            return

        method_scores = {
            "rule_based": float(selected.get("rule_based_total", 0.0)),
            "embedding": float(selected.get("embedding_score", 0.0)),
            "llm_judge": float(selected.get("llm_judge_avg", 0.0)),
        }
        dominant = max(method_scores, key=method_scores.get)

        updated = self._weights.copy()
        delta = STEP_SIZE if rating > 0 else -STEP_SIZE
        updated[dominant] += delta

        share = delta / max(len(updated) - 1, 1)
        for method in updated:
            if method == dominant:
                continue
            updated[method] -= share

        for method, value in list(updated.items()):
            updated[method] = min(MAX_WEIGHT, max(MIN_WEIGHT, value))

        self._weights = _normalize(updated)
        self._weight_history.append(self.get_current_weights())

    def get_current_weights(self) -> Dict[str, float]:
        return {key: round(value, 6) for key, value in self._weights.items()}

    def get_feedback_stats(self) -> Dict[str, object]:
        total_feedback = len(self._records)
        positive = sum(1 for record in self._records if record["rating"] > 0)
        negative = sum(1 for record in self._records if record["rating"] < 0)
        neutral = total_feedback - positive - negative

        prompt_ratings: Dict[str, set] = {}
        for record in self._records:
            prompt_ratings.setdefault(record["prompt"], set()).add(record["rating"])
        conflicting_prompts = sum(1 for ratings in prompt_ratings.values() if len(ratings) > 1)

        return {
            "total_feedback": total_feedback,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "positive_rate": round(positive / max(total_feedback, 1), 3),
            "current_weights": self.get_current_weights(),
            "weight_history": self._weight_history[-20:],
            "annotator_consistency": round(
                1 - (conflicting_prompts / max(len(prompt_ratings), 1)),
                3,
            ),
        }


feedback_service = FeedbackService()

