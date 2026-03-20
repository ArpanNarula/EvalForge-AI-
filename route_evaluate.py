"""
EvalForge AI — routes/evaluate.py
POST /evaluate  →  run all three scoring methods and return ranked results.

Uses current RLHF-adjusted weights from the feedback service so that
past user preference signals influence future rankings.
"""

from fastapi import APIRouter, HTTPException

from models.schemas import EvaluationRequest, EvaluationResult
from services.evaluation_service import EvaluationService
from services.feedback_service import feedback_service
from route_history import register_session
from utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)

_eval = EvaluationService()
_feedback = feedback_service


@router.post("/", response_model=EvaluationResult, summary="Evaluate and rank responses")
async def evaluate_responses(request: EvaluationRequest):
    """
    Run the three-method evaluation pipeline:
      1. Rule-based scoring (length, structure, keyword overlap)
      2. Embedding similarity scoring
      3. LLM-as-Judge (correctness, relevance, clarity)

    Combines into weighted ensemble using RLHF-adjusted weights.
    """
    # Fetch live weights — these drift based on accumulated user feedback
    weights = _feedback.get_current_weights()
    log.info(
        f"[{request.session_id}] Evaluating {len(request.responses)} responses "
        f"with weights rule={weights['rule_based']:.2f} / "
        f"emb={weights['embedding']:.2f} / judge={weights['llm_judge']:.2f}"
    )

    try:
        result = await _eval.evaluate_responses(
            session_id=request.session_id,
            prompt=request.prompt,
            responses=request.responses,
            weight_overrides=weights,
        )
    except Exception as exc:
        log.error(f"[{request.session_id}] Evaluation failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    best_score = next((score.final_score for score in result.scores if score.response_id == result.best_response_id), None)
    best_response = next((response for response in request.responses if response.id == result.best_response_id), None)
    if best_response is not None and best_score is not None:
        register_session(
            session_id=request.session_id,
            prompt=request.prompt,
            prompt_version=getattr(request, "version_tag", None),
            best_response_text=best_response.text,
            best_score=best_score,
        )

    log.info(
        f"[{request.session_id}] Best response_id={result.best_response_id} "
        f"score={(best_score or 0.0):.1f}"
    )
    return result


@router.get("/weights", summary="Current ensemble scoring weights")
async def get_scoring_weights():
    """Returns the live scoring weights (updated by RLHF feedback loop)."""
    stats = _feedback.get_feedback_stats()
    return {
        "weights": stats["current_weights"],
        "total_feedback_sessions": stats["total_feedback"],
        "positive_rate": stats["positive_rate"],
        "note": "Weights shift over time as user feedback signals accumulate.",
    }
