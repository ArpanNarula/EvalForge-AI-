# EvalForge AI

EvalForge AI is a lightweight evaluation workflow for comparing multiple generated responses, scoring them with an ensemble, collecting preference feedback, and surfacing retrieval context for future generations.

## Structure

- `frontend/`: Next.js dashboard for running prompts, reviewing scores, and exploring metrics
- `backend_main.py` plus root `routes/`, `services/`, `models/`: FastAPI backend used locally and for Vercel backend deployment
- `backend/`: convenience wrappers for the documented local backend layout

## Local development

### Backend

```bash
pip install -r requirements.txt
uvicorn backend_main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` for local frontend-to-backend requests.

## Vercel deployment

- Backend project root: repository root
- Frontend project root: `frontend/`
- Frontend environment variable: `NEXT_PUBLIC_API_URL=<backend deployment URL>`

