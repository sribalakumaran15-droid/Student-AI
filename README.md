# StudyAI: AI Student Academic Assistant

StudyAI is a production-style EdTech application with a React/Vite frontend and FastAPI backend. It combines JWT authentication, SQLAlchemy persistence, course discovery, document-grounded chat, quizzes, profile statistics, and a responsive SaaS dashboard.

## Stack

- Frontend: React, Vite, Tailwind CSS, Axios, React Router, Lucide React
- Backend: FastAPI, SQLAlchemy, SQLite by default, PostgreSQL-ready via `DATABASE_URL`
- AI/RAG: OpenAI-compatible chat API when configured, local document extraction and retrieval fallback
- Documents: PDF, DOCX, TXT, max 10 MB per upload

## Project structure

```text
frontend/                 React/Vite application
  src/components/         Sidebar, layout, stats, empty states, toast
  src/pages/              Landing, auth, dashboard, chat, materials, courses, quiz, profile
  src/services/api.js     Axios client and JWT interceptor
backend/                  FastAPI application
  routes/                 REST endpoints
  models/                 SQLAlchemy relationships
  services/               AI, document/RAG, and quiz services
  database/               Engine and session setup
data/courses.json         Demo curriculum used to seed the database
```

## Run locally

Create and activate a Python environment, then install backend dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

Copy `.env.example` to `.env`, then set a long random `JWT_SECRET`. Add `OPENAI_API_KEY` to enable cloud-generated answers; the application remains usable with local fallback answers when it is empty.

Start the API in one terminal:

```powershell
uvicorn backend.app:app --reload --port 8000
```

Install and start the frontend in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API documentation is available at `http://localhost:8000/docs`.

If the Windows `npm` wrapper is broken, invoke npm's internal CLI directly:

```powershell
& "C:\Program Files\nodejs\node.exe" "C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js" install
& "C:\Program Files\nodejs\node.exe" "C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js" run dev
```

## Authentication and security

Passwords are hashed with Werkzeug and never stored directly. Login and registration return JWT access tokens. Protected endpoints require `Authorization: Bearer <token>`. API keys, JWT secrets, database URLs, CORS origins, and model names are environment variables. Configure a strong secret before deployment and use PostgreSQL in production.

## RAG flow

1. The user uploads a PDF, DOCX, or TXT document.
2. The document service extracts and cleans text.
3. Text is split into overlapping chunks and stored in `document_chunks`.
4. Local retrieval selects relevant chunks for the question.
5. StudyAI sends the selected context to the OpenAI-compatible model when configured.
6. Chat responses include source document and chunk metadata where available.

The local fallback makes the project runnable without an API key. Replace `backend/services/document_service.py` retrieval with a hosted vector database or embedding index when scaling beyond development.

## API surface

- `POST /api/auth/register`, `POST /api/auth/login`
- `GET /api/dashboard`, `GET/PUT /api/profile`
- `GET /api/courses`, `GET /api/courses/{id}`
- `POST /api/documents/upload`, `GET /api/documents`, `DELETE /api/documents/{id}`
- `POST /api/chat`, `GET /api/chat/history`
- `POST /api/quiz/generate`, `POST /api/quiz/submit`, `GET /api/quiz/history`

## Verification

```powershell
python -m compileall -q backend
python -c "from fastapi.testclient import TestClient; from backend.app import app; print(TestClient(app).get('/api/health').json())"
cd frontend
npm run build
```

The former Streamlit app remains available as `app.py` for reference, but the production-style experience is the React/FastAPI pair described above.
