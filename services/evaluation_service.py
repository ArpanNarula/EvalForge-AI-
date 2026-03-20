"""Evaluation engine combining heuristics, semantic similarity, and a judge layer."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List

from models.schemas import (
    EmbeddingScore,
    EvaluationResult,
    GeneratedResponse,
    LLMJudgeScore,
    ResponseScore,
    RuleBasedScore,
)

DEFAULT_EVAL_WEIGHTS = {"rule_based": 0.20, "embedding": 0.30, "llm_judge": 0.50}

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "with",
}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9']+", text.lower())
    return [token for token in tokens if token not in STOP_WORDS and len(token) > 2]


def _vectorize(tokens: Iterable[str]) -> Counter:
    return Counter(tokens)


def _cosine_similarity(left: str, right: str) -> float:
    left_vec = _vectorize(_tokenize(left))
    right_vec = _vectorize(_tokenize(right))
    if not left_vec or not right_vec:
        return 0.0

    intersection = set(left_vec) & set(right_vec)
    numerator = sum(left_vec[token] * right_vec[token] for token in intersection)
    left_norm = math.sqrt(sum(value * value for value in left_vec.values()))
    right_norm = math.sqrt(sum(value * value for value in right_vec.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(0.0, min(1.0, numerator / (left_norm * right_norm)))


def _normalize_weights(weights: Dict[str, float] | None) -> Dict[str, float]:
    merged = {**DEFAULT_EVAL_WEIGHTS, **(weights or {})}
    total = sum(max(value, 0.0) for value in merged.values()) or 1.0
    return {key: max(value, 0.0) / total for key, value in merged.items()}


class EvaluationService:
    def rule_based_score(self, response_text: str, prompt: str) -> RuleBasedScore:
        words = response_text.split()
        word_count = len(words)
        lowered = response_text.lower()

        if word_count >= 80:
            length_score = 25.0
        elif word_count >= 50:
            length_score = 21.0
        elif word_count >= 25:
            length_score = 16.0
        elif word_count >= 10:
            length_score = 9.0
        elif word_count >= 5:
            length_score = 5.0
        else:
            length_score = 2.0

        bullet_lines = len(re.findall(r"(?m)^\s*([-*]|\d+\.)\s+", response_text))
        structure_score = 0.0
        if bullet_lines >= 2:
            structure_score += 12.0
        elif bullet_lines == 1:
            structure_score += 6.0
        if "\n" in response_text:
            structure_score += 5.0
        if any(marker in lowered for marker in ("steps", "summary", "because", "therefore", "first", "finally")):
            structure_score += 6.0
        if len(re.findall(r"[.!?]", response_text)) >= 2:
            structure_score += 4.0
        structure_score = min(structure_score, 25.0)

        prompt_tokens = set(_tokenize(prompt))
        response_tokens = set(_tokenize(response_text))
        overlap = len(prompt_tokens & response_tokens)
        keyword_ratio = overlap / max(len(prompt_tokens), 1)
        keyword_score = min(25.0, keyword_ratio * 25.0 * 1.2)

        completeness_score = 0.0
        if word_count >= 8:
            completeness_score += 10.0
        if response_text.strip().endswith((".", "!", "?")):
            completeness_score += 8.0
        if len(re.findall(r"[.!?]", response_text)) >= 1:
            completeness_score += 4.0
        if any(marker in lowered for marker in ("because", "therefore", "process", "update", "repeat")):
            completeness_score += 3.0
        completeness_score = min(completeness_score, 25.0)

        total = round(
            _clamp(length_score + structure_score + keyword_score + completeness_score),
            1,
        )
        return RuleBasedScore(
            length_score=round(length_score, 1),
            structure_score=round(structure_score, 1),
            keyword_score=round(keyword_score, 1),
            completeness_score=round(completeness_score, 1),
            total=total,
        )

    async def embedding_score(self, prompt: str, response_text: str) -> EmbeddingScore:
        cosine = round(_cosine_similarity(prompt, response_text), 4)
        normalized = round(cosine * 100.0, 1)
        return EmbeddingScore(cosine_similarity=cosine, normalized_score=normalized)

    async def llm_judge_scores(
        self,
        prompt: str,
        responses: List[GeneratedResponse],
    ) -> List[LLMJudgeScore]:
        scores: List[LLMJudgeScore] = []
        for response in responses:
            rule = self.rule_based_score(response.text, prompt)
            embedding = await self.embedding_score(prompt, response.text)
            correctness = _clamp(rule.keyword_score * 2.2 + rule.completeness_score * 1.8)
            relevance = _clamp(embedding.normalized_score * 0.8 + rule.keyword_score * 1.3)
            clarity = _clamp(rule.length_score * 2.0 + rule.structure_score * 1.8)
            average = round((correctness + relevance + clarity) / 3.0, 1)

            if relevance < 25:
                explanation = "Mostly off-topic relative to the prompt."
            elif clarity >= 70 and correctness >= 70:
                explanation = "Clear, on-topic, and reasonably complete."
            elif clarity < 45:
                explanation = "Relevant, but the explanation is still thin or abrupt."
            else:
                explanation = "Solid answer with room for more specificity."

            scores.append(
                LLMJudgeScore(
                    correctness=round(correctness, 1),
                    relevance=round(relevance, 1),
                    clarity=round(clarity, 1),
                    average=average,
                    explanation=explanation,
                )
            )
        return scores

    def compute_final_score(
        self,
        rule_score: RuleBasedScore,
        embedding_score: EmbeddingScore,
        judge_score: LLMJudgeScore,
        weights: Dict[str, float] | None = None,
    ) -> float:
        normalized = _normalize_weights(weights)
        final_score = (
            rule_score.total * normalized["rule_based"]
            + embedding_score.normalized_score * normalized["embedding"]
            + judge_score.average * normalized["llm_judge"]
        )
        return round(_clamp(final_score), 1)

    async def evaluate_responses(
        self,
        session_id: str,
        prompt: str,
        responses: List[GeneratedResponse],
        weight_overrides: Dict[str, float] | None = None,
    ) -> EvaluationResult:
        judge_scores = await self.llm_judge_scores(prompt, responses)
        scored: List[ResponseScore] = []

        for response, judge_score in zip(responses, judge_scores):
            rule_score = self.rule_based_score(response.text, prompt)
            embedding_score = await self.embedding_score(prompt, response.text)
            final_score = self.compute_final_score(
                rule_score,
                embedding_score,
                judge_score,
                weights=weight_overrides,
            )
            scored.append(
                ResponseScore(
                    response_id=response.id,
                    rule_based=rule_score,
                    embedding=embedding_score,
                    llm_judge=judge_score,
                    final_score=final_score,
                    rank=0,
                )
            )

        ranked = sorted(scored, key=lambda item: item.final_score, reverse=True)
        for index, response_score in enumerate(ranked, start=1):
            response_score.rank = index

        best_response_id = ranked[0].response_id if ranked else -1
        return EvaluationResult(
            session_id=session_id,
            best_response_id=best_response_id,
            scores=ranked,
        )

