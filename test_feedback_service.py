"""
EvalForge AI — tests/test_feedback_service.py
Tests for the RLHF-lite feedback and weight adjustment system.
"""

import pytest
from services.feedback_service import FeedbackService, DEFAULT_WEIGHTS
from models.schemas import FeedbackRequest, FeedbackRating


@pytest.fixture
def svc():
    """Fresh FeedbackService per test — avoids weight drift bleeding between tests."""
    return FeedbackService()


def make_request(rating: int, session_id="sess-001"):
    return FeedbackRequest(
        session_id=session_id,
        prompt="What is gradient descent?",
        selected_response_id=0,
        selected_response_text="Gradient descent is an optimization algorithm...",
        rating=FeedbackRating(rating),
    )


class TestFeedbackRecording:
    @pytest.mark.asyncio
    async def test_feedback_returns_id(self, svc):
        result = await svc.record_feedback(make_request(1))
        assert result.feedback_id
        assert len(result.feedback_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_stats_increment(self, svc):
        await svc.record_feedback(make_request(1))
        await svc.record_feedback(make_request(-1))
        stats = svc.get_feedback_stats()
        assert stats["total_feedback"] == 2
        assert stats["positive"] == 1

    @pytest.mark.asyncio
    async def test_positive_rate_calculation(self, svc):
        await svc.record_feedback(make_request(1))
        await svc.record_feedback(make_request(1))
        await svc.record_feedback(make_request(-1))
        stats = svc.get_feedback_stats()
        assert abs(stats["positive_rate"] - 2/3) < 0.01


class TestWeightAdjustment:
    def test_weights_sum_to_one(self, svc):
        score_breakdown = {
            "0": {"rule_based_total": 40, "embedding_score": 50, "llm_judge_avg": 90}
        }
        svc._adjust_weights(score_breakdown, 0, rating=1)
        weights = svc.get_current_weights()
        assert abs(sum(weights.values()) - 1.0) < 1e-6, f"Weights don't sum to 1: {weights}"

    def test_weights_stay_bounded(self, svc):
        score_breakdown = {
            "0": {"rule_based_total": 10, "embedding_score": 10, "llm_judge_avg": 99}
        }
        # Apply many positive signals for llm_judge
        for _ in range(100):
            svc._adjust_weights(score_breakdown, 0, rating=1)

        weights = svc.get_current_weights()
        for k, v in weights.items():
            assert 0.05 <= v <= 0.85, f"Weight {k}={v} out of bounds"

    def test_positive_feedback_increases_dominant_method(self, svc):
        # LLM judge has highest score for response 0 → positive signal should raise judge weight
        score_breakdown = {
            "0": {"rule_based_total": 20, "embedding_score": 30, "llm_judge_avg": 95}
        }
        before = svc.get_current_weights()["llm_judge"]
        svc._adjust_weights(score_breakdown, 0, rating=1)
        after = svc.get_current_weights()["llm_judge"]
        assert after > before

    def test_negative_feedback_decreases_dominant_method(self, svc):
        score_breakdown = {
            "0": {"rule_based_total": 20, "embedding_score": 30, "llm_judge_avg": 95}
        }
        before = svc.get_current_weights()["llm_judge"]
        svc._adjust_weights(score_breakdown, 0, rating=-1)
        after = svc.get_current_weights()["llm_judge"]
        assert after < before
