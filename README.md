# GREM — Quality-Gated Multi-Hop Retrieval with Episodic Memory

Distilling multi-agent LLM reasoning into a small cross-encoder for multi-hop
retrieval, with verified reasoning chains stored in MongoDB Atlas.

Built for the Google Cloud Rapid Agent Hackathon (MongoDB Track), May–June 2026.

**Demo:** [grem-frontend34.vercel.app](https://grem-frontend34.vercel.app/) · **License:** MIT

---

## What this does

Multi-hop questions ("who directed the film starring X") break keyword retrieval,
because no single query term matches the bridging document. The usual fix is to
call an LLM to re-rank candidates on every query, which costs latency and money at
inference time.

GREM tries a different split: use Gemini agents **once, during training**, to
produce reasoning about why retrieval failed on hard cases. Keep the chains that
pass a quality gate. Fine-tune a small BERT cross-encoder on them. At inference
there are no LLM calls.

---

## Results

Evaluated on 228 held-out HotpotQA bridge questions, drawn from cases where BM25's
top-1 result was not the gold document. Candidate pool is 10 documents per query
(HotpotQA distractor format), so random ordering gives Hits@1 = 0.10.

| Metric | Random order | GREM (distilled) | GREM (+ Atlas fallback) |
|---|:---:|:---:|:---:|
| Hits@1 | 0.10 | 0.8026 | 0.8026 |
| Hits@2 | 0.20 | 0.9342 | 0.9254 |
| Recall@2 | — | 0.7083 | 0.7061 |
| MRR | — | 0.8864 | 0.8851 |
| nDCG@5 | — | 0.8482 | 0.8475 |
| Latency / query | — | ~2 ms | 2–50 ms |
| LLM calls at inference | — | 0 | 0 |

Atlas Vector Search activates on 11 of 228 queries (4.8%), triggered when the
score gap between the top two candidates is below 0.1. On this evaluation it does
not change results measurably — the differences above are within noise at n=228.

### Coverage by failure type

The 228 cases were labelled by failure mode during the offline pipeline. Gold
document ranked first:

| Failure mode | Recovered | Total | Rate |
|---|:---:|:---:|:---:|
| Chain break | 16 | 19 | 84.2% |
| Distractor confusion | 64 | 79 | 81.0% |
| Entity drift | 103 | 130 | 79.2% |
| **Overall** | **183** | **228** | **80.3%** |

### What these numbers do not show

Three gaps worth stating plainly, since they affect how the results should be read:

**No zero-shot baseline.** The cross-encoder is `ms-marco-MiniLM-L-6-v2`, which is
pretrained for passage re-ranking. Its untuned score on this evaluation set has not
been measured, so the 0.80 above cannot be attributed to GREM's training pipeline —
some unknown fraction is the pretrained checkpoint. **This is the first thing that
should be run.**

**No measured LLM re-ranking comparison.** An earlier version of this README quoted
estimated numbers for a Gemini re-ranking baseline. Those were never run and have
been removed. The cost and latency advantages of distillation over per-query LLM
calls are structural — no API call is made — but the quality comparison is untested.

**BM25 is not a baseline here.** The 228 cases were selected *because* BM25's top-1
was wrong, so BM25 scores zero on them by construction. That is the sampling
criterion, not a result. Random ordering over the 10-candidate pool is the honest
floor, and it is what the table reports.

**Single split, single seed.** 80/20 split at seed 42, n=228, no confidence
intervals. Differences under a few points should not be read as real.

---

## Architecture

### Offline (training)

1. **Data** — HotpotQA distractor, 97,852 multi-hop records
2. **BM25 baseline** — sparse retrieval over the corpus to locate failures
3. **Hard failure extraction** — 26,353 records where BM25 top-1 ≠ gold
4. **Multi-agent reasoning** — three Gemini 2.5 Flash-Lite agents per failure:
   - Agent A — entity overlap
   - Agent B — bridge chain
   - Agent C — golden chunk validation
5. **Aggregator** — Gemini 2.5 Flash combines the three summaries, scores quality,
   labels failure mode
6. **Quality gate** — keep chains with `q_final ≥ 0.5` and `resolved == true`
7. **Storage** — surviving chains written to MongoDB Atlas via the MongoDB MCP Server

1,145 of 26,353 chains passed the gate (4.3%).

**A note on the gate.** Of those 1,145, only 3 scored `q_final ≥ 0.7`. So almost the
entire stored set sits in a narrow 0.5–0.7 band. Either the aggregator prompt
produces degenerate scores, or Gemini cannot meaningfully discriminate the quality
of its own reasoning chains. This has not been diagnosed and it undercuts the
"quality-gated" framing — a gate that admits everything above a floor and nothing
above a ceiling is not doing much gating.

### Online (inference)

1. 10 candidates per query
2. 22M-parameter BERT cross-encoder scores each candidate–query pair
3. If the top-1/top-2 score gap is below 0.1, query Atlas Vector Search for the
   three most similar verified chains and rescore with that context
4. Return ranked candidates

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ (MongoDB MCP Server)
- MongoDB Atlas account (M0 is sufficient)
- Google Cloud project with Vertex AI / Agent Platform access

### Install

```bash
git clone https://github.com/aaryaupadhya12/GREM.git
cd GREM
pip install -r requirements.txt
npm install -g mongodb-mcp-server

gcloud auth application-default login
gcloud config set project <YOUR_GCP_PROJECT_ID>
```

### Environment

`.env` at the repository root:

```env
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true
```

### Training pipeline

```bash
python Data/Pull_dataset.py
python BM25_Baseline/BM25_Pipeline.py

cd Gemini/Agents
python Agent_A.py
python Agent_B.py
python Agent_C.py
python Aggregator.py
python mongo_writer.py
python run_once_reembed.py
```

Then create a Vector Search index in the Atlas UI named `episodic_embedding_index`
on `query_embedding` (384 dimensions, cosine).

### Re-ranker

```bash
cd Gemini/Inference
python split_train_test.py     # 80/20, seed 42
python train_reranker.py
python evaluate.py
```

### Verify MCP integration

```bash
cd Gemini/Agents
python Mongodb_mcp_integration.py
```

---

## Repository layout

```text
GREM/
├── BM25_Baseline/          # baseline retrieval experiments
├── Data/                   # dataset preparation
├── Gemini/
│   ├── Agents/             # the four Gemini agents, Mongo writer, MCP client, quality gate
│   ├── Context/            # agent system prompts
│   ├── Doc/                # design and migration notes
│   └── Inference/          # cross-encoder training and evaluation
├── LICENSE
├── requirements.txt
└── .env.example
```

---

## Stack

| Component | Technology |
|---|---|
| Agents | Gemini 2.5 Flash-Lite (Agent Platform) |
| Aggregator | Gemini 2.5 Flash (Agent Platform) |
| Vector memory | MongoDB Atlas + Atlas Vector Search |
| MCP | MongoDB MCP Server (JSON-RPC over stdio) |
| Re-ranker | BERT cross-encoder (`ms-marco-MiniLM-L-6-v2`) |
| Frontend | React + Tailwind on Vercel |
| Observability | LangSmith |
| Dataset | HotpotQA distractor |

---

## Design notes

**Why distil rather than call Gemini at inference?** Per-query LLM calls add
network latency and per-query cost, and rule the approach out for latency-sensitive
or air-gapped deployments. Distillation moves that cost to training time. Whether
quality is preserved is the part that needs the untested comparison above.

**Why Atlas rather than a dedicated vector database?** The same database stores the
verified chains, serves them through Vector Search at inference, and backs the
frontend analytics. One system, one set of credentials.

**Why does Atlas fire on only 4.8% of queries?** By design — the fallback triggers
only when the cross-encoder is uncertain, measured by a small top-1/top-2 score gap.
Whether the fallback helps on those 11 queries is not established; the aggregate
numbers are unchanged either way, and 11 cases is too few to tell.

---

## Known issues

- Zero-shot cross-encoder baseline not measured (see above)
- LLM re-ranking comparison not measured
- Quality gate score distribution is degenerate; not diagnosed
- Single seed, single split, no confidence intervals
- Evaluation is HotpotQA-only; no transfer test to another multi-hop dataset

---

## Acknowledgments

HotpotQA · MongoDB Atlas and MCP Server · Google Cloud Agent Platform ·
Sentence Transformers

## License

MIT
