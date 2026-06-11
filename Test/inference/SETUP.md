# Inference Pipeline — Setup Instructions

Quality-Gated Multi-Hop Retrieval using BM25 + Dense Retrieval,
RRF Fusion, Episodic Memory, and BERT Cross-Encoder Reranking.

Keep in mind that there are two modes for this right now: one which uses free stuff like groq and sentence-transformers whereas for the final demo we might use Vertex AI and Gemini API which are paid. migration to Google Cloud still pending.

---

## What You Need Before Starting

| Requirement | Where to get it | Cost |
|---|---|---|
| Python 3.10+ | python.org | Free |
| MongoDB Atlas account | cloud.mongodb.com | Free (M0 tier) |
| Groq API key | console.groq.com | Free (14,400 req/day) |


---

## Part 1 — Local Setup (Free)

This gets the pipeline running entirely on your machine with no
paid services. Complete this before touching Docker or GCP.

### 1.1 — Clone and create virtual environment

```bash
git clone <your-repo-url>
cd your-project

python -m venv venv

# Mac / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# Confirm you are inside the venv
which python     # should show .../venv/bin/python
```

### 1.2 — Install dependencies

```bash
pip install -r requirements.txt
```

This downloads approximately 800MB on first run:
- `sentence-transformers` — all-MiniLM-L6-v2 (~90MB)
- `cross-encoder` model — ms-marco-MiniLM-L-6-v2 (~90MB)
- `faiss-cpu` — vector index library
- `pymongo`, `groq`, `langchain-core`, `rank-bm25`, etc.

### 1.3 — Get your API keys

**MongoDB Atlas (free)**
1. Go to cloud.mongodb.com → Create free account
2. Create a new project → Build a Database → M0 Free tier
3. Choose any cloud provider and region
4. Create a database user (username + password — save these)
5. Under Network Access → Add IP Address → Add Current IP
6. Under Database → Connect → Drivers → copy the connection string
   It looks like: `mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/`

**Groq (free)**
1. Go to console.groq.com → Sign up
2. API Keys → Create API Key → copy it

### 1.4 — Create your .env file

```bash
cp .env.template .env
```

Open `.env` and fill in the two free values:

```bash
# .env

# Required now (free)
MONGO_URI=mongodb+srv://youruser:yourpassword@cluster0.xxxxx.mongodb.net/
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Leave blank until final demo
GEMINI_API_KEY=
GCP_PROJECT=
USE_PAID=false
```

> **Important:** `.env` is in `.gitignore` and `.dockerignore`.
> Never commit it. Never paste it anywhere.

### 1.5 — Seed MongoDB with test data

```bash
python upload_synthetic_memory.py
```

Expected output:
```
Connecting to MongoDB Atlas...
Connected ✓
episodic_memory : inserted 30 documents ✓
passages        : inserted 34 documents ✓
inference_results: collection created ✓
```

At the end it prints the Atlas Vector Search index JSON.
**Save that JSON — you need it in the next step.**

### 1.6 — Create the Atlas Vector Search index

This is a one-time manual step in the Atlas UI.
It cannot be done via Python — Atlas requires the UI or API.

1. Go to your cluster in Atlas UI
2. Left sidebar → **Search & Vector Search**
3. Click **Create Search Index**
4. Select **JSON Editor** (not Visual Editor)
5. Set:
   - Database: `hotpotqa_rag`
   - Collection: `episodic_memory`
   - Index name: `episodic_embedding_index`
6. Paste this JSON:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 768,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "failure_type"
    },
    {
      "type": "filter",
      "path": "quality_score"
    }
  ]
}
```

7. Click **Create Search Index**
8. Wait approximately 2 minutes for status to show **Active**

### 1.7 — Replace placeholder embeddings with real vectors

The upload script used hash-based placeholder vectors.
This step replaces them with real semantic embeddings
so Atlas Vector Search returns meaningful results.

```bash
python run_once_reembed.py
```

Expected output:
```
Connecting to MongoDB Atlas...
Connected ✓
Found 30 documents to re-embed

Loading all-MiniLM-L6-v2...
Embedding 30 queries...
Batches: 100%|████████| 1/1 [00:00<00:00]
Embeddings shape: (30, 384)

Updated 30 documents ✓
```

After this completes:

> **You must delete and recreate the Atlas index**
> because the embedding dimension changed from 768 to 384.

Repeat step 1.6 but change `numDimensions` from `768` to `384`.
Delete the old index first (three-dot menu → Delete).

### 1.9 — Run the pipeline

```bash
python inference_pipeline.py
```

Expected output:
```
[Dense] Loading local embedding model...
[Dense] Embedder ready ✓
[EpisodicMemory] Loading embedding model...
[EpisodicMemory] Embedder ready ✓
[Reranker] Loading BERT cross-encoder...
[Reranker] Cross-encoder ready ✓
[BM25] Building index from MongoDB...
[BM25] Ready — 34 passages
[BM25] 34 candidates
[Dense] Building FAISS index over 34 passages...
[Dense] FAISS index ready — 34 vectors, dim=384
[Dense] 34 candidates
[RRF] Fused 34 BM25 + 34 dense → 34 candidates
[ColdStartGate] Query 100 — episodic memory ACTIVE
[EpisodicMemory] 3 hints  top_sim=0.847
[Reranker] Top: [Roland Garros]  combined=1.000
[BridgeVerifier] verdict=grounded  bridge=Paris
[MongoDB] Saved  query: Which tennis player...
[Narrator] The tennis player who won...

=======================================================
RESULT
=======================================================
Top passage  : Roland Garros
Bridge entity: Paris
Chain        : Eiffel Tower → Paris → Roland Garros → Novak Djokovic
Verdict      : grounded
```

## Part 4 — Switch to Paid Mode (Final Demo)

Do this only when you are ready for the final presentation.
Each API call to Vertex AI and Gemini costs money.

### 4.1 — Re-embed episodic memory with Vertex AI vectors

```bash
# Add GCP_PROJECT to your .env first, then:
python reembed_vertex.py
```

This replaces 384-dim sentence-transformer vectors with
768-dim Vertex AI textembedding-gecko vectors.

After it completes, recreate the Atlas index one more time
with `numDimensions: 768` (same process as step 1.6).

### 4.2 — Add Gemini API key to .env

```bash
# Get key from aistudio.google.com → Get API Key
# Add to .env:
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

---

## Summary — Run Order

```
First time setup
────────────────
1.  python -m venv venv && source venv/bin/activate
2.  pip install -r requirements.txt
3.  cp .env.template .env  →  fill in MONGO_URI + GROQ_API_KEY
4.  python upload_synthetic_memory.py
5.  Create Atlas vector search index (UI, numDimensions: 768)
6.  python run_once_reembed.py
7.  Recreate Atlas index (UI, numDimensions: 384)
8.  python verify_upload.py        ← all 11 checks must pass
9.  python inference_pipeline.py   ← first successful run

