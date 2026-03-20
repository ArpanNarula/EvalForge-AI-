"""
EvalForge AI — routes/history.py
GET /history  →  paginated history of all evaluation sessions.
GET /history/{session_id}  →  full detail for one session.
GET /history/metrics  →  aggregate evaluation metrics for dashboard.

In production this queries PostgreSQL via SQLAlchemy.
For the demo, an in-memory store is used — swap the storage backend
by replacing the _store calls with SQLAlchemy async queries.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from models.schemas import HistoryEntry, HistoryResponse
from utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)

# ── In-memory session store ──────────────────────────────────────────────────
# Replace with: `from database.db import AsyncSessionLocal` + SQLAlchemy queries
_sessions: List[dict] = []


def register_session(
    session_id: str,
    prompt: str,
    prompt_version: Optional[str],
    best_response_text: str,
    best_score: float,
    feedback_rating: Optional[int] = None,
):
    """Called by the generate + evaluate pipeline to log completed sessions."""
    existing = next((item for item in _sessions if item["session_id"] == session_id), None)
    record = {
        "session_id": session_id,
        "prompt": prompt,
        "prompt_version": prompt_version or "v1",
        "best_response_text": best_response_text,
        "best_score": best_score,
        "feedback_rating": feedback_rating,
        "created_at": datetime.utcnow(),
    }
    if existing:
        existing.update(record)
        return
    _sessions.append(record)


def update_session_feedback(session_id: str, feedback_rating: int):
    """Attach feedback to an existing history record."""
    match = next((item for item in _sessions if item["session_id"] == session_id), None)
    if match:
        match["feedback_rating"] = feedback_rating


@router.get("/", response_model=HistoryResponse, summary="Paginated session history")
async def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    min_score: Optional[float] = Query(None, description="Filter by minimum score"),
    version: Optional[str] = Query(None, description="Filter by prompt version tag"),
):
    """
    Returns paginated evaluation session history.
    Supports filtering by minimum score and prompt version.
    """
    filtered = _sessions

    if min_score is not None:
        filtered = [s for s in filtered if s["best_score"] >= min_score]
    if version:
        filtered = [s for s in filtered if s["prompt_version"] == version]

    # Sort newest first
    filtered = sorted(filtered, key=lambda s: s["created_at"], reverse=True)
    start = (page - 1) * page_size
    page_data = filtered[start : start + page_size]

    entries = [HistoryEntry(**s) for s in page_data]
    return HistoryResponse(
        entries=entries,
        total=len(filtered),
        page=page,
        page_size=page_size,
    )


@router.get("/metrics", summary="Aggregate evaluation metrics for dashboard")
async def get_metrics():
    """
    Returns aggregate metrics across all sessions.
    Useful for the evaluation metrics dashboard.
    """
    if not _sessions:
        return {"message": "No sessions recorded yet.", "sessions": 0}

    scores = [s["best_score"] for s in _sessions]
    rated = [s for s in _sessions if s["feedback_rating"] is not None]
    positive = [s for s in rated if s.get("feedback_rating", 0) > 0]

    # Score distribution buckets
    buckets = {"0-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for sc in scores:
        if sc < 40: buckets["0-40"] += 1
        elif sc < 60: buckets["40-60"] += 1
        elif sc < 80: buckets["60-80"] += 1
        else: buckets["80-100"] += 1

    versions = {}
    for s in _sessions:
        v = s.get("prompt_version", "v1")
        if v not in versions:
            versions[v] = {"count": 0, "avg_score": 0.0, "scores": []}
        versions[v]["count"] += 1
        versions[v]["scores"].append(s["best_score"])

    for v in versions:
        sc_list = versions[v].pop("scores")
        versions[v]["avg_score"] = round(sum(sc_list) / len(sc_list), 1)

    return {
        "total_sessions": len(_sessions),
        "avg_best_score": round(sum(scores) / len(scores), 1),
        "max_score": round(max(scores), 1),
        "min_score": round(min(scores), 1),
        "score_distribution": buckets,
        "feedback_coverage": f"{len(rated)}/{len(_sessions)}",
        "positive_rate": round(len(positive) / max(len(rated), 1), 3),
        "prompt_versions": versions,
    }


@router.get("/{session_id}", summary="Get full detail for one session")
async def get_session(session_id: str):
    """Returns the full stored record for a single session."""
    match = next((s for s in _sessions if s["session_id"] == session_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Session not found.")
    return match
