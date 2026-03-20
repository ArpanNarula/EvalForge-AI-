"""
EvalForge AI - FastAPI Backend Entry Point
Production-grade LLM Evaluation & Feedback Engine
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.db import init_db
from routes import evaluate, feedback, generate, history, retrieve
from utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown lifecycle."""
    logger.info("Starting EvalForge AI backend...")
    await init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Shutting down EvalForge AI backend.")


app = FastAPI(
    title="EvalForge AI",
    description="LLM Evaluation & Feedback Engine - simulating RLHF-style improvement loops",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
frontend_url = os.getenv("FRONTEND_URL")
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]
if frontend_url:
    allowed_origins.append(frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(generate.router, prefix="/generate", tags=["Generation"])
app.include_router(evaluate.router, prefix="/evaluate", tags=["Evaluation"])
app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
app.include_router(history.router, prefix="/history", tags=["History"])
app.include_router(retrieve.router, prefix="/retrieve", tags=["Retrieval"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "EvalForge AI"}


@app.get("/")
async def root():
    return {
        "service": "EvalForge AI",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "generate": "/generate",
        "evaluate": "/evaluate",
        "feedback": "/feedback",
        "history": "/history",
        "retrieve": "/retrieve",
    }
