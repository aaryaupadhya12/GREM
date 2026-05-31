# GREM — Generative Retrieval & Extraction Model

![Vercel](https://img.shields.io/badge/Frontend-Vercel-black?logo=vercel)
![Cloud Run](https://img.shields.io/badge/Backend-Cloud%20Run-4285F4?logo=googlecloud)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi)
![MongoDB](https://img.shields.io/badge/DB-MongoDB%20Atlas-47A248?logo=mongodb)
![Bun](https://img.shields.io/badge/Runtime-Bun-f9f1e1?logo=bun)

---

## Stack

| Layer | Service |
|-------|---------|
| Frontend | Vercel (TanStack Router + Vite) |
| Backend | Google Cloud Run / Hugging Face Spaces |
| ML Pipeline | FastAPI · BM25 · BERT Reranker |
| Database | MongoDB Atlas |

```
Browser → Vercel (/api/* proxy) → Cloud Run (FastAPI) → MongoDB Atlas
```

---

## Quickstart (Local)

```bash
# Frontend
bun install
cp .env.example .env.local
bun run dev

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

`.env.local`

```env
GREM_API_URL=http://localhost:8080
GREM_API_KEY=dev-secret
VITE_PUBLIC_APP_ENV=development
```

---

## Production Deploy

### 1 · Frontend → Vercel

```bash
# vite.config.ts — set Nitro preset
nitro: { preset: 'vercel' }
```

```bash
vercel --prod
```

**Vercel environment variables:**

```env
GREM_API_URL=https://<your-cloud-run-or-hf-url>
GREM_API_KEY=<secret>
VITE_PUBLIC_APP_ENV=production
```

**`vercel.json`**

```json
{
  "buildCommand": "bun run build",
  "outputDirectory": ".vercel/output",
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://<BACKEND_URL>/api/$1" }
  ]
}
```

---

### 2a · Backend → Google Cloud Run

```bash
# Authenticate
gcloud auth login
gcloud config set project <PROJECT_ID>

# Store secrets
echo -n "<api-key>"        | gcloud secrets create grem-api-key   --data-file=-
echo -n "<mongodb-uri>"    | gcloud secrets create mongodb-uri     --data-file=-

# Build & push
gcloud builds submit --tag gcr.io/<PROJECT_ID>/grem-backend

# Deploy
gcloud run deploy grem-backend \
  --image      gcr.io/<PROJECT_ID>/grem-backend \
  --region     us-central1 \
  --memory     8Gi \
  --cpu        4 \
  --min-instances 0 \
  --max-instances 5 \
  --set-secrets GREM_API_KEY=grem-api-key:latest \
  --set-secrets MONGODB_URI=mongodb-uri:latest \
  --allow-unauthenticated
```

**`backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

### 2b · Backend → Hugging Face Spaces (Free Tier)

```yaml
# Space README.md header
---
title: GREM Backend
sdk: docker
app_port: 7860
hardware: cpu-upgrade   # or t4-small for GPU
---
```

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
```

**Space secrets** *(Settings → Repository secrets)*

```
GREM_API_KEY=<secret>
MONGODB_URI=<mongodb+srv://...>
```

---

## Environment Variables

### Frontend

| Key | Value |
|-----|-------|
| `GREM_API_URL` | Backend URL |
| `GREM_API_KEY` | Shared API secret |
| `VITE_PUBLIC_APP_ENV` | `production` |

### Backend

| Key | Value |
|-----|-------|
| `GREM_API_KEY` | Shared API secret |
| `MONGODB_URI` | Atlas connection string |
| `HF_TOKEN` | *(HF Spaces only)* |

---

## API

```
POST /api/infer
x-api-key: <GREM_API_KEY>
Content-Type: application/json

{ "query": "..." }
```

```json
{ "results": [...] }
```
