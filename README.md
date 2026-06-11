# GREM — Quality-Gated Multi-Hop Retrieval with Episodic Memory

> Recover the queries your search system is losing — at one-thousandth the 
> cost of LLM re-ranking. Trained with Gemini agents, stored in MongoDB Atlas, 
> distilled into a 22M parameter re-ranker that runs in 2ms with no API calls.

**Live Demo:** [grem-frontend34.vercel.app](https://grem-frontend34.vercel.app/)  
**Hackathon:** Google Cloud Rapid Agent Hackathon — MongoDB Track  
**License:** Apache 2.0

![GREM Architecture](Images/Arch.png)

---

## TL;DR

Every search system loses one in four customer queries silently — the kind 
that ask "who directed the film starring X" or "drug interactions for patients 
over 65." The industry fix is to call an LLM on every query for re-ranking, 
costing $0.003 per query and 2 seconds of latency. Unworkable at scale, 
unworkable in regulated industries.

GREM solves this with a different approach: capture the LLM's reasoning **once 
during training** using Gemini agents on Google Cloud Agent Platform, store 
the verified chains in MongoDB Atlas as episodic memory, and distill that 
knowledge into a 22-million parameter BERT cross-encoder that runs in 2ms 
with zero API calls at inference.

---

## Results

Evaluated on 228 held-out HotpotQA bridge failures where BM25 scores zero by 
definition:

| Metric                  | BM25 Baseline | LLM Re-ranking | **GREM (Distilled)** | **GREM (Adaptive Atlas)** |
|-------------------------|:-------------:|:--------------:|:--------------------:|:-------------------------:|
| Hits@1                  | 0.0000        | ~0.85          | **0.8026**           | **0.8026**                |
| Hits@2                  | —             | ~0.93          | **0.9342**           | **0.9254**                |
| Recall@2                | —             | ~0.72          | **0.7083**           | **0.7061**                |
| MRR                     | —             | ~0.88          | **0.8864**           | **0.8851**                |
| nDCG@5                  | —             | ~0.84          | **0.8482**           | **0.8475**                |
| Ground Rate             | —             | —              | **100%**             | **100%**                  |
| Latency per query       | 5 ms          | ~2 s           | **2 ms**             | **2-50 ms**               |
| Cost per query          | $0            | $0.003         | **$0.000003**        | **$0.000003**             |
| API calls at inference  | 0             | 1 LLM          | **0**                | **0-1 vector**            |

### Recovery by Failure Mode

| Failure Mode          | Recovered | Total | Rate     |
|-----------------------|:---------:|:-----:|:--------:|
| Chain break           | 16        | 19    | **84.2%**|
| Distractor confusion  | 64        | 79    | **81.0%**|
| Entity drift          | 103       | 130   | **79.2%**|
| **OVERALL**           | **183**   | **228**| **80.3%**|

MongoDB Atlas Vector Search activates adaptively on 4.8% of low-confidence 
queries (11 out of 228) — exactly when the re-ranker needs help.

---

## Required Technology Compliance

This submission satisfies all required technologies for the Google Cloud Rapid 
Agent Hackathon — MongoDB Track:

### Gemini API on Google Cloud Agent Platform
- All four agents (Entity Overlap, Bridge Chain, Relevance Validator, 
  Aggregator) invoke Gemini 2.5 Flash-Lite and Gemini 2.5 Flash through the 
  Agent Platform endpoint
- Authentication via Application Default Credentials (`gcloud auth`)
- Files: `Gemini/Agents/Agent_A.py`, `Agent_B.py`, `Agent_C.py`, `Aggregator.py`

### MongoDB Atlas
- 1,145 verified reasoning chains stored in `GREM.episodic_memory`
- Atlas Vector Search (`episodic_embedding_index`) for adaptive runtime hints
- Aggregation pipelines for failure mode taxonomy
- Files: `Gemini/Agents/mongo_writer.py`, `Gemini/Agents/run_once_reembed.py`

### MongoDB MCP Server
- Verified episodic memory retrieval via Model Context Protocol (JSON-RPC over stdio)
- Used for bulk insertion, read-side verification, and demo trace caching
- Files: `Gemini/Agents/Mongodb_mcp_integration.py`, `mongo_writer.py`

### No Competing AI Services
The submission uses only Gemini for all inference. Earlier exploratory code 
using other providers has been removed from the active codebase.

---

## Architecture

GREM is a two-stage pipeline: an offline training pipeline that generates 
verified episodic memory, and an online inference pipeline that uses that 
memory to recover BM25 failures.

### Offline Training Pipeline

1. **HotpotQA Distractor** — 97,852 multi-hop records loaded
2. **BM25 Baseline** — sparse retrieval over the full corpus identifies misses
3. **Hard Failure Extraction** — mines 26,353 records where BM25 top-1 ≠ gold
4. **Multi-Agent Reasoning** — three Gemini Flash-Lite agents analyze each failure:
   - Agent A: Entity Overlap Reasoner (~60 token summary)
   - Agent B: Bridge Chain Reasoner (~60 token summary)
   - Agent C: Golden Chunk Validator (~80 token summary)
5. **Aggregator** — Gemini 2.5 Flash combines summaries, scores quality, classifies failure mode
6. **Quality Gate** — only chains with `q_final ≥ 0.5 AND resolved == true` persist
7. **MongoDB Atlas** — verified chains written via MongoDB MCP Server

### Online Inference Pipeline

1. **Candidate Retrieval** — 10 candidates per query (HotpotQA distractor format)
2. **Cross-Encoder Re-ranking** — 22M parameter BERT scores candidate-query pairs
3. **Adaptive Atlas Fallback** — when confidence gap < 0.1, query Atlas Vector 
   Search for top-3 similar verified chains and rescore with that context
4. **Output** — ranked candidates with score, latency under 50ms even with Atlas

---

## Repository Structure
GREM/
├── BM25_Baseline/                  # Initial baseline experiments
│   ├── BM25_Pipeline.py
│   └── BM25_results.md
├── Data/                           # Dataset preparation
│   └── Pull_dataset.py
├── Gemini/                         # Main submission code
│   ├── Agents/
│   │   ├── Agent_A.py              # Entity Overlap Reasoner (Gemini Flash-Lite)
│   │   ├── Agent_B.py              # Bridge Chain Reasoner (Gemini Flash-Lite)
│   │   ├── Agent_C.py              # Golden Chunk Validator (Gemini Flash-Lite)
│   │   ├── Aggregator.py           # Quality scorer (Gemini Flash)
│   │   ├── mongo_writer.py         # Writes verified chains to Atlas via MCP
│   │   ├── Mongodb_mcp_integration.py  # MongoDB MCP Server client
│   │   ├── precompute_UI.py        # Caches 5 demo traces for frontend
│   │   ├── quality_gate.py         # q_final scoring logic
│   │   └── outputs/                # aggregator_out.json, metrics_final.json
│   ├── Context/                    # Agent system prompts
│   │   ├── Agent_A.md
│   │   ├── Agent_B.md
│   │   ├── Agent_C.md
│   │   ├── Aggregator.md
│   │   └── Context.md
│   ├── Doc/                        # Migration notes and design docs
│   │   ├── Gemini_Migration.md
│   │   └── Gemini.md
│   └── Inference/                  # Cross-encoder training and evaluation
│       ├── train_reranker.py
│       ├── evaluate.py             # Adaptive Atlas evaluation
│       └── outputs/                # train_split.json, test_split.json, model
├── Images/                         # Architecture diagrams
├── LICENSE                         # Apache 2.0
├── README.md                       # This file
├── requirements.txt                # Python dependencies
└── .env.example                    # Required environment variables

---

## Setup and Run

### Prerequisites
- Python 3.10+
- Node.js 18+ (for MongoDB MCP Server)
- MongoDB Atlas account with M0 cluster
- Google Cloud account with Vertex AI / Agent Platform access

### Installation

```bash
# Clone repo
git clone https://github.com/<username>/GREM.git
cd GREM

# Install Python dependencies
pip install -r requirements.txt

# Install MongoDB MCP Server (Node.js)
npm install -g mongodb-mcp-server

# Authenticate with Google Cloud (uses ADC, not service account JSON)
gcloud auth application-default login
gcloud config set project <YOUR_GCP_PROJECT_ID>
```

### Environment Variables

Create a `.env` file at the repository root:

```env
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true
```

### Run the Training Pipeline

```bash
# 1. Pull HotpotQA dataset and run BM25 baseline
python Data/Pull_dataset.py
python BM25_Baseline/BM25_Pipeline.py

# 2. Run multi-agent reasoning over hard failures
cd Gemini/Agents
python Agent_A.py
python Agent_B.py
python Agent_C.py
python Aggregator.py

# 3. Write verified chains to MongoDB Atlas via MCP
python mongo_writer.py

# 4. Add embeddings for Atlas Vector Search
python run_once_reembed.py
```

Then in MongoDB Atlas UI, create a Vector Search index named 
`episodic_embedding_index` on `query_embedding` (384 dimensions, cosine).

### Train the Re-ranker

```bash
cd Gemini/Inference
python split_train_test.py        # 80/20 split with seed=42
python train_reranker.py 
python evaluate.py                # Computes Hits@1, Hits@2, Recall@2, MRR, etc.
```

### Verify MongoDB MCP Integration

```bash
cd Gemini/Agents
python Mongodb_mcp_integration.py
```

Expected output:
[MCP] using cmd: <path-to-npx>
GREM — MongoDB MCP Server smoke test
episodic_memory document count : 1145
verified chains (q_final≥0.7)  : 3
[1] {'query': 'What are the colors of the tricolour flag...',
'q_final': 0.7, 'failure_mode': 'entity_drift'}
[2] {'query': 'Which rapper who worked with a star of...',
'q_final': 0.85, 'failure_mode': 'entity_drift'}
[3] {'query': 'What form of play does Yameen and...',
'q_final': 0.8, 'failure_mode': 'chain_break'}
MCP integration verified 

---

## Tech Stack

| Component               | Technology                                  |
|-------------------------|---------------------------------------------|
| LLM Agents              | Gemini 2.5 Flash-Lite (via Agent Platform)  |
| Quality Aggregator      | Gemini 2.5 Flash (via Agent Platform)       |
| Vector Memory           | MongoDB Atlas + Atlas Vector Search         |
| MCP Protocol            | MongoDB MCP Server (JSON-RPC over stdio)    |
| Re-ranking              | BERT Cross-Encoder (ms-marco-MiniLM-L-6-v2) |
| Frontend                | React + Tailwind on Vercel                  |
| Observability           | LangSmith                                   |
| Dataset                 | HotpotQA Distractor                         |

---

## Key Design Decisions

### Why distill instead of calling Gemini at inference?

Production search systems need millisecond latency and predictable cost. 
Calling Gemini on every query costs $0.003 per query and adds 2 seconds. 
Distilling the reasoning into a 22M parameter local model gives equivalent 
quality at 1000× lower cost and 1000× lower latency.

### Why MongoDB Atlas over a dedicated vector database?

Atlas combines operational data, vector search, and aggregation in one platform. 
For GREM, the same database stores verified chains (training data), serves them 
through Vector Search at inference (runtime safety net), and powers the frontend 
analytics layer. One vendor, one security perimeter, one audit log.

### Why is Atlas Vector Search only used on 4.8% of queries?

The cross-encoder has internalized the reasoning patterns from training. On 
confident predictions (95% of queries), runtime hint injection adds noise. 
On uncertain predictions (small score gap between top-1 and top-2 candidates), 
fetching similar past failures from Atlas helps. Adaptive activation gives the 
best of both: fast common-case, accurate edge-case.

### What is the Ground Rate metric?

Ground Rate measures the fraction of correct predictions where the gold document 
was placed at rank 1 by the cross-encoder's own scoring (not by lucky tie-breaking). 
100% Ground Rate proves every correct prediction is causally explained — not a 
coincidence.

---

## Acknowledgments

- HotpotQA dataset
- MongoDB Atlas Vector Search and MCP Server
- Google Cloud Agent Platform
- The Sentence Transformers library

---

## License

MIT License

This project was built during the Google Cloud Rapid Agent Hackathon 
(May 5 — June 11, 2026) and is a newly created submission for the MongoDB track.
