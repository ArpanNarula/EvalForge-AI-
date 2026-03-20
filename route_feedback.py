"""
EvalForge AI — routes/feedback.py
POST /feedback  →  record human preference signal + trigger weight update.
GET  /feedback/stats  →  annotator consistency + weight drift dashboard.

This route is the RLHF data collection endpoint.
Every thumb up/down is a labeled preference pair that nudges the scoring weights.
"""

from fastapi import APIRouter, HTTPException

from models.schemas import FeedbackRequest, FeedbackResponse
from route_history import update_session_feedback
from services.embedding_service import embedding_service
from services.feedback_service import feedback_service
from utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)

_feedback = feedback_service
_emb = embedding_service


@router.post("/", response_model=FeedbackResponse, summary="Record user preference")
async def record_feedback(request: FeedbackRequest):
    """
    Record a human preference signal:
    - Stores which response was selected and its rating (1 / -1 / 0)
    - Adjusts ensemble scoring weights via RLHF-lite Bradley-Terry update
    - Embeds and stores the session in ChromaDB for future RAG retrieval

    The embedding storage step is critical: it means future similar prompts
    will see this session's best response as a retrieved example.
    """
    try:
        result = await _feedback.record_feedback(request)
    except Exception as exc:
        log.error(f"Feedback recording failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    # Store positively-rated sessions in the vector DB for RAG
    if request.rating > 0:
        try:
            best_score = 0.0
            if request.score_breakdown:
                weights = _feedback.get_current_weights()
                best_score = round(
                    request.score_breakdown.rule_based_total * weights["rule_based"]
                    + request.score_breakdown.embedding_score * weights["embedding"]
                    + request.score_breakdown.llm_judge_avg * weights["llm_judge"],
                    1,
                )
            await _emb.store_session(
                session_id=request.session_id,
                prompt=request.prompt,
                best_response=request.selected_response_text,
                best_score=best_score,
                feedback_rating=request.rating,
            )
            log.info(f"[{request.session_id}] Stored positively-rated session in ChromaDB.")
        except Exception as exc:
            # Non-critical — don't fail the feedback call if embedding storage fails
            log.warning(f"ChromaDB storage failed (non-fatal): {exc}")

    update_session_feedback(request.session_id, int(request.rating))
    return result


@router.get("/stats", summary="Annotator consistency & weight drift stats")
async def feedback_stats():
    """
    Returns metrics useful for an annotation consistency dashboard:
    - Total feedback count
    - Positive vs negative split
    - Current ensemble weights (shows how much they've drifted from defaults)
    - Per-method weight history (simplified for this implementation)
    """
    stats = _feedback.get_feedback_stats()
    defaults = {"rule_based": 0.20, "embedding": 0.30, "llm_judge": 0.50}

    weight_drift = {
        k: round(stats["current_weights"].get(k, 0) - defaults[k], 4)
        for k in defaults
    }

    return {
        **stats,
        "default_weights": defaults,
        "weight_drift_from_default": weight_drift,
        "interpretation": {
            k: ("no drift" if abs(v) < 0.01 else f"{'increased' if v > 0 else 'decreased'} by {abs(v):.3f}")
            for k, v in weight_drift.items()
        },
    }
