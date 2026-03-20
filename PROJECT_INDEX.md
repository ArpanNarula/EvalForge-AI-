# EvalForge AI — Complete File Index

## Backend Structure
```
backend/
├── main.py                          # FastAPI app entry point + lifespan
├── requirements.txt
├── models/
│   ├── __init__.py
│   └── schemas.py                   # All Pydantic request/response models
├── routes/
│   ├── __init__.py
│   ├── generate.py                  # POST /generate
│   ├── evaluate.py                  # POST /evaluate, GET /evaluate/weights
│   ├── feedback.py                  # POST /feedback, GET /feedback/stats
│   ├── history.py                   # GET /history, GET /history/metrics
│   └── retrieve.py                  # POST /retrieve, GET /retrieve/context
├── services/
│   ├── __init__.py
│   ├── llm_service.py               # Multi-response generation (async parallel)
│   ├── evaluation_service.py        # 3-method eval engine
│   ├── embedding_service.py         # ChromaDB + RAG builder
│   └── feedback_service.py          # RLHF-lite weight adjustment
├── database/
│   ├── __init__.py
│   └── db.py                        # SQLAlchemy async ORM
├── utils/
│   ├── __init__.py
│   └── logger.py                    # Structured logging
└── tests/
    ├── test_evaluation_service.py   # Rule-based + embedding + ensemble tests
    └── test_feedback_service.py     # RLHF weight adjustment tests
```

## Frontend Structure
```
frontend/
├── package.json
├── pages/
│   └── index.jsx                    # Main dashboard page
├── components/
│   ├── ResponseCard.jsx             # Per-response display + score breakdown
│   └── MetricsDashboard.jsx         # Weight drift + analytics charts
├── services/
│   └── api.js                       # All fetch wrappers for backend API
└── styles/
    └── globals.css                  # Full dark-mode design system
```

## Setup (3 commands)
```bash
# Backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Tests
cd backend && pytest tests/ -v
```

## API Endpoints
```
POST /generate              →  3-5 parallel responses + RAG injection
POST /evaluate              →  rule-based + embedding + LLM judge scoring
POST /feedback              →  preference signal + RLHF weight update
GET  /feedback/stats        →  weight drift + annotator consistency
GET  /history               →  paginated session history
GET  /history/metrics       →  score distribution + version analytics
POST /retrieve              →  ChromaDB semantic search
GET  /retrieve/context      →  debug RAG context for a query
GET  /docs                  →  Swagger UI
```
