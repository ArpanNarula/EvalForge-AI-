"""
EvalForge AI — tests/test_evaluation_service.py
Unit tests for the evaluation engine.
Run with: pytest tests/ -v
"""

import pytest
from datetime import datetime

from models.schemas import GeneratedResponse, GenerationStrategy
from services.evaluation_service import EvaluationService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def eval_service():
    return EvaluationService()


def make_response(idx: int, text: str, strategy=GenerationStrategy.BALANCED) -> GeneratedResponse:
    return GeneratedResponse(
        id=idx,
        strategy=strategy,
        strategy_label=strategy.value.title(),
        text=text,
        word_count=len(text.split()),
        char_count=len(text),
        generated_at=datetime.utcnow(),
    )


PROMPT = "Explain how backpropagation works in neural networks."

GOOD_RESPONSE = """
Backpropagation is the algorithm used to train neural networks by computing
gradients of the loss function with respect to each weight.

Steps:
1. Forward pass: compute predictions
2. Compute loss using a loss function (e.g. cross-entropy)
3. Backward pass: apply chain rule to compute gradients layer by layer
4. Update weights using gradient descent

This process repeats until the network converges to a minimum loss.
"""

SHORT_RESPONSE = "It updates weights."

IRRELEVANT_RESPONSE = "The weather in Paris is lovely in spring."


# ── Rule-based scoring tests ───────────────────────────────────────────────────

class TestRuleBasedScoring:
    def test_good_response_scores_well(self, eval_service):
        score = eval_service.rule_based_score(GOOD_RESPONSE, PROMPT)
        assert score.total >= 60, f"Good response scored only {score.total}"

    def test_short_response_penalized(self, eval_service):
        score = eval_service.rule_based_score(SHORT_RESPONSE, PROMPT)
        assert score.length_score <= 10

    def test_bullet_points_rewarded(self, eval_service):
        with_bullets = "- Point one\n- Point two\n- Point three"
        score = eval_service.rule_based_score(with_bullets, PROMPT)
        assert score.structure_score >= 10

    def test_irrelevant_response_low_keyword(self, eval_service):
        score = eval_service.rule_based_score(IRRELEVANT_RESPONSE, PROMPT)
        assert score.keyword_score <= 5

    def test_total_bounded(self, eval_service):
        for text in [GOOD_RESPONSE, SHORT_RESPONSE, IRRELEVANT_RESPONSE]:
            score = eval_service.rule_based_score(text, PROMPT)
            assert 0 <= score.total <= 100, f"Score out of bounds: {score.total}"

    def test_completeness_score_proper_ending(self, eval_service):
        complete = "This is a complete sentence."
        incomplete = "This is not complete"
        score_complete = eval_service.rule_based_score(complete, PROMPT)
        score_incomplete = eval_service.rule_based_score(incomplete, PROMPT)
        assert score_complete.completeness_score > score_incomplete.completeness_score


# ── Embedding scoring tests ───────────────────────────────────────────────────

class TestEmbeddingScoring:
    @pytest.mark.asyncio
    async def test_on_topic_response_higher_than_off_topic(self, eval_service):
        on_topic = await eval_service.embedding_score(PROMPT, GOOD_RESPONSE)
        off_topic = await eval_service.embedding_score(PROMPT, IRRELEVANT_RESPONSE)
        assert on_topic.normalized_score > off_topic.normalized_score

    @pytest.mark.asyncio
    async def test_score_bounded(self, eval_service):
        score = await eval_service.embedding_score(PROMPT, GOOD_RESPONSE)
        assert 0 <= score.cosine_similarity <= 1
        assert 0 <= score.normalized_score <= 100


# ── Weighted ensemble tests ───────────────────────────────────────────────────

class TestWeightedEnsemble:
    def test_custom_weights_applied(self, eval_service):
        from models.schemas import RuleBasedScore, EmbeddingScore, LLMJudgeScore

        rule = RuleBasedScore(length_score=20, structure_score=20, keyword_score=20, completeness_score=20, total=80)
        emb  = EmbeddingScore(cosine_similarity=0.5, normalized_score=50)
        judge = LLMJudgeScore(correctness=90, relevance=90, clarity=90, average=90, explanation="")

        # If judge weight is 1.0, final should equal judge score
        score = eval_service.compute_final_score(
            rule, emb, judge, weights={"rule_based": 0.0, "embedding": 0.0, "llm_judge": 1.0}
        )
        assert abs(score - 90.0) < 0.5

    def test_final_score_bounded(self, eval_service):
        from models.schemas import RuleBasedScore, EmbeddingScore, LLMJudgeScore

        rule  = RuleBasedScore(length_score=25, structure_score=25, keyword_score=25, completeness_score=25, total=100)
        emb   = EmbeddingScore(cosine_similarity=1.0, normalized_score=100)
        judge = LLMJudgeScore(correctness=100, relevance=100, clarity=100, average=100, explanation="")

        score = eval_service.compute_final_score(rule, emb, judge)
        assert 0 <= score <= 100


# ── Integration test (mocked LLM judge) ──────────────────────────────────────

class TestPipelineIntegration:
    @pytest.mark.asyncio
    async def test_best_response_is_highest_scorer(self, eval_service, monkeypatch):
        """End-to-end test: the best_response_id should match the highest final_score."""

        # Monkeypatch LLM judge to return predictable scores without API call
        from models.schemas import LLMJudgeScore

        async def mock_judge(prompt, responses):
            # Good response (id=0) gets high scores; short gets low
            mapping = {0: (90, 90, 90), 1: (40, 40, 40), 2: (60, 60, 60)}
            results = []
            for r in responses:
                c, rel, cl = mapping.get(r.id, (50, 50, 50))
                results.append(LLMJudgeScore(correctness=c, relevance=rel, clarity=cl, average=(c+rel+cl)/3, explanation=""))
            return results

        monkeypatch.setattr(eval_service, "llm_judge_scores", mock_judge)

        responses = [
            make_response(0, GOOD_RESPONSE, GenerationStrategy.BALANCED),
            make_response(1, SHORT_RESPONSE, GenerationStrategy.CONCISE),
            make_response(2, "A moderately good response about backpropagation and gradients.", GenerationStrategy.DETAILED),
        ]

        result = await eval_service.evaluate_responses(
            session_id="test-session",
            prompt=PROMPT,
            responses=responses,
        )

        assert result.best_response_id == 0, f"Expected id=0 to be best, got {result.best_response_id}"
        scores_by_id = {s.response_id: s.final_score for s in result.scores}
        assert scores_by_id[0] > scores_by_id[1]
