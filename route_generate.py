"""
EvalForge AI — routes/generate.py
POST /generate  →  multi-response generation with optional RAG context injection.

Flow:
  1. Receive prompt + strategy list from client
  2. Retrieve semantically similar past sessions from ChromaDB (RAG)
  3. Inject retrieved context into generation system prompts
  4. Run N parallel LLM calls (one per strategy)
  5. Return all responses under a shared session_id
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from models.schemas import GenerationResult, PromptRequest
from services.embedding_service import embedding_service
from services.llm_service import LLMService
from utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)

_llm = LLMService()
_emb = embedding_service


@router.post("/", response_model=GenerationResult, summary="Generate multiple responses")
async def generate_responses(request: PromptRequest):
    """
    Generate 3–5 responses using strategy diversification.
    Automatically retrieves similar past prompts for RAG context.
    """
    session_id = str(uuid.uuid4())
    log.info(f"[{session_id}] Generation request: '{request.prompt[:60]}...'")

    # RAG: retrieve similar past prompts and inject as context
    similar = await _emb.retrieve_similar(request.prompt, top_k=2)
    rag_context = _emb.build_rag_context(similar)
    if rag_context:
        log.info(f"[{session_id}] RAG: injected {len(similar)} similar prompt(s).")
        request.rag_context = rag_context

    try:
        responses = await _llm.generate_responses(request)
    except Exception as exc:
        log.error(f"[{session_id}] Generation failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    log.info(f"[{session_id}] Generated {len(responses)} responses.")
    return GenerationResult(
        session_id=session_id,
        prompt=request.prompt,
        prompt_version=request.version_tag or "v1",
        responses=responses,
        generated_at=datetime.utcnow(),
        rag_context_used=bool(rag_context),
        similar_prompts_found=len(similar),
    )
