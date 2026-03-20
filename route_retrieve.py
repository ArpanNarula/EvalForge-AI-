"""
EvalForge AI — routes/retrieve.py
POST /retrieve  →  semantic search over stored prompt embeddings.
GET  /retrieve/context  →  build RAG context string for a given query.

This is the retrieval side of the RAG pipeline.
Prompts + best responses are indexed in ChromaDB after feedback.
New queries retrieve the most semantically similar past sessions
to inject as context into generation.
"""

from fastapi import APIRouter, HTTPException, Query

from models.schemas import RetrievalRequest, RetrievalResult
from services.embedding_service import embedding_service
from utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)

_emb = embedding_service


@router.post("", response_model=RetrievalResult, summary="Retrieve similar past prompts")
@router.post("/", response_model=RetrievalResult, include_in_schema=False)
async def retrieve_similar(request: RetrievalRequest):
    """
    Semantic search over all stored prompt embeddings in ChromaDB.
    Returns top-k most similar past prompts with their best responses.
    These are used to inject prior knowledge into new generation calls (RAG).
    """
    log.info(f"Retrieval query: '{request.query[:60]}' (top_k={request.top_k})")
    try:
        similar = await _emb.retrieve_similar(request.query, top_k=request.top_k)
    except Exception as exc:
        log.error(f"Retrieval failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return RetrievalResult(
        query=request.query,
        similar_prompts=similar,
        context_injected=len(similar) > 0,
    )


@router.get("/context", summary="Build RAG context string for a query")
async def get_rag_context(query: str, top_k: int = Query(3, ge=1, le=10)):
    """
    Returns the formatted RAG context block that would be injected
    into the system prompt for this query. Useful for debugging RAG behaviour.
    """
    try:
        similar = await _emb.retrieve_similar(query, top_k=top_k)
        context = _emb.build_rag_context(similar)
        return {
            "query": query,
            "similar_prompts_found": len(similar),
            "context_block": context or "(no similar prompts in store yet)",
            "will_inject": bool(context),
        }
    except Exception as exc:
        log.error(f"RAG context build failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stats", summary="ChromaDB collection stats")
async def retrieval_stats():
    """Returns the number of prompts indexed in the vector store."""
    try:
        count = _emb.collection.count()
        return {
            "indexed_prompts": count,
            "collection": "evalforge_prompts",
            "embedding_model": "all-MiniLM-L6-v2 (SentenceTransformers)",
            "similarity_metric": "cosine",
        }
    except Exception as exc:
        return {"error": str(exc), "indexed_prompts": 0}
