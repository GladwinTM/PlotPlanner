# PlotPlanner frontend

Simple React UI for the PlotPlanner backend services.

## What it talks to

| UI area | Backend | Endpoints |
| --- | --- | --- |
| Profile | profile-service `:8001` | `POST/GET/PATCH /v1/profiles` |
| Evidence | knowledge-service `:8002` | `POST /v1/documents` |
| Retrieve | knowledge-service `:8002` | `POST /v1/search` |

There is no chat proxy. The agent/MCP surface remains out of band.

## Run

Start Postgres plus both FastAPI services first, then:

```bash
# backend/
uvicorn profile_api:app --reload --port 8000
uvicorn RAG_KB_api:app --reload --port 8002

# frontend/
npm install
npm run dev
```

Open the Vite URL shown in the terminal (usually http://localhost:5173).

Service URLs are configured in `.env`:

```
VITE_PROFILE_API_URL=http://localhost:8000
VITE_KNOWLEDGE_API_URL=http://localhost:8002
```
