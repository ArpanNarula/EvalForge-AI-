"""Pydantic schemas used by routes, services, and tests."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class GenerationStrategy(str, Enum):
    BALANCED = "balanced"
    CONCISE = "concise"
    DETAILED = "detailed"
    CREATIVE = "creative"
    STRUCTURED = "structured"


class FeedbackRating(int, Enum):
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1


class PromptRequest(BaseModel):
    prompt: str
    strategies: List[GenerationStrategy] = Field(
        default_factory=lambda: [
            GenerationStrategy.BALANCED,
            GenerationStrategy.CONCISE,
            GenerationStrategy.DETAILED,
        ]
    )
    num_responses: int = 3
    version_tag: Optional[str] = None
    rag_context: Optional[str] = None


class GeneratedResponse(BaseModel):
    id: int
    strategy: GenerationStrategy
    strategy_label: str
    text: str
    word_count: int
    char_count: int
    generated_at: datetime


class GenerationResult(BaseModel):
    session_id: str
    prompt: str
    prompt_version: str
    responses: List[GeneratedResponse]
    generated_at: datetime
    rag_context_used: bool = False
    similar_prompts_found: int = 0


class RuleBasedScore(BaseModel):
    length_score: float
    structure_score: float
    keyword_score: float
    completeness_score: float
    total: float


class EmbeddingScore(BaseModel):
    cosine_similarity: float
    normalized_score: float


class LLMJudgeScore(BaseModel):
    correctness: float
    relevance: float
    clarity: float
    average: float
    explanation: str


class ResponseScore(BaseModel):
    response_id: int
    rule_based: RuleBasedScore
    embedding: EmbeddingScore
    llm_judge: LLMJudgeScore
    final_score: float
    rank: int


class EvaluationRequest(BaseModel):
    session_id: str
    prompt: str
    responses: List[GeneratedResponse]


class EvaluationResult(BaseModel):
    session_id: str
    best_response_id: int
    scores: List[ResponseScore]
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackScoreBreakdown(BaseModel):
    rule_based_total: float
    embedding_score: float
    llm_judge_avg: float


class FeedbackRequest(BaseModel):
    session_id: str
    prompt: str
    selected_response_id: int
    selected_response_text: str
    rating: FeedbackRating
    comment: Optional[str] = None
    score_breakdown: Optional[FeedbackScoreBreakdown] = None


class FeedbackResponse(BaseModel):
    feedback_id: str
    rating: FeedbackRating
    updated_weights: Dict[str, float]
    message: str


class HistoryEntry(BaseModel):
    session_id: str
    prompt: str
    prompt_version: str
    best_response_text: str
    best_score: float
    feedback_rating: Optional[int] = None
    created_at: datetime


class HistoryResponse(BaseModel):
    entries: List[HistoryEntry]
    total: int
    page: int
    page_size: int


class RetrievedPrompt(BaseModel):
    session_id: str
    prompt: str
    best_response: str
    similarity_score: float
    best_score: float = 0.0
    feedback_rating: int = 0


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = Field(default=3, ge=1, le=10)


class RetrievalResult(BaseModel):
    query: str
    similar_prompts: List[RetrievedPrompt]
    context_injected: bool

