"""
run_once_reembed.py
===================
Run this ONCE after upload_synthetic_memory.py.

What it does:
  - Pulls all 30 episodic_memory documents from MongoDB
  - Generates real sentence-transformers embeddings
    (all-MiniLM-L6-v2, 384-dim) for each query
  - Replaces the placeholder SHA256 hash vectors with
    real semantic vectors
  - Prints a similarity sanity check at the end

Why this is needed:
  upload_synthetic_memory.py used a deterministic hash function
  to generate placeholder embeddings so the upload would work
  without any ML dependencies. Those vectors are random noise —
  Atlas Vector Search will return random results until you replace
  them with real embeddings.

After this script finishes:
  - Recreate the Atlas Vector Search index with numDimensions: 384
    (the old index used 768 — it must be deleted and recreated)
  - Run verify_upload.py to confirm everything works

Usage:
    pip install sentence-transformers pymongo python-dotenv
    export MONGO_URI="mongodb+srv://user:pass@cluster.mongodb.net/"
    python run_once_reembed.py
"""

import os
import numpy as np
from dotenv import load_dotenv
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer

load_dotenv()

MONGO_URI  = os.environ.get("MONGO_URI", "")
DB_NAME    = "hotpotqa_rag"
COLLECTION = "episodic_memory"
MODEL_NAME = "all-MiniLM-L6-v2"
DIM        = 384


def run():
    # ── connect ───────────────────────────────────────────────────────────────
    if not MONGO_URI or "<user>" in MONGO_URI:
        raise SystemExit(
            "ERROR: Set MONGO_URI first.\n"
            "  export MONGO_URI='mongodb+srv://user:pass@cluster.mongodb.net/'"
        )

    print("Connecting to MongoDB Atlas...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10_000)
    client.admin.command("ping")
    print("Connected ✓\n")

    col     = client[DB_NAME][COLLECTION]
    records = list(col.find({}, {"_id": 1, "query": 1}))

    if not records:
        raise SystemExit(
            "ERROR: No documents found in episodic_memory.\n"
            "Run upload_synthetic_memory.py first."
        )

    print(f"Found {len(records)} documents to re-embed\n")

    # ── load model ────────────────────────────────────────────────────────────
    print(f"Loading {MODEL_NAME}...")
    print("(~90MB download on first run, cached afterwards)\n")
    model = SentenceTransformer(MODEL_NAME)

    # ── embed all queries in one batch (fast) ─────────────────────────────────
    queries = [r["query"] for r in records]
    print(f"Embedding {len(queries)} queries...")
    embeddings = model.encode(
        queries,
        normalize_embeddings = True,
        batch_size           = 32,
        show_progress_bar    = True,
    )
    print(f"Embeddings shape: {embeddings.shape}  (expected: ({len(queries)}, {DIM}))\n")

    # ── write back to MongoDB ─────────────────────────────────────────────────
    print("Writing embeddings to MongoDB...")
    updated = 0
    for rec, emb in zip(records, embeddings):
        result = col.update_one(
            {"_id": rec["_id"]},
            {"$set": {"embedding": emb.tolist()}}
        )
        if result.modified_count:
            updated += 1

    print(f"Updated {updated}/{len(records)} documents ✓\n")

    # ── sanity check: similarity between two related queries ──────────────────
    print("── Similarity sanity check ──────────────────────────────")
    print("These pairs should have HIGH similarity (both about geography):\n")

    test_pairs = [
        (
            "Which tennis player won the tournament held in the city where the Eiffel Tower is located in 2023?",
            "What is the name of the river that runs through the city where the Louvre museum is located?",
            "Both about Paris landmarks — should be similar",
        ),
        (
            "Who founded the company that makes the iPhone?",
            "In what year was the company founded that created the search engine with the largest market share?",
            "Both about tech company founders — should be moderately similar",
        ),
        (
            "Which tennis player won the tournament held in the city where the Eiffel Tower is located in 2023?",
            "Who composed the Four Seasons and what nationality was he?",
            "Sports vs classical music — should be LOW similarity",
        ),
    ]

    test_queries = list({q for pair in test_pairs for q in pair[:2]})
    test_embs    = model.encode(test_queries, normalize_embeddings=True)
    emb_map      = dict(zip(test_queries, test_embs))

    for q1, q2, label in test_pairs:
        e1  = emb_map[q1]
        e2  = emb_map[q2]
        sim = float(np.dot(e1, e2))
        bar = "█" * int(max(0, sim) * 20)
        print(f"  {label}")
        print(f"  similarity = {sim:.4f}  {bar}")
        print(f"    Q1: {q1[:65]}...")
        print(f"    Q2: {q2[:65]}...\n")

    # ── Atlas index reminder ───────────────────────────────────────────────────
    print("=" * 65)
    print("NEXT STEP — Recreate Atlas Vector Search index")
    print("=" * 65)
    print("""
The old index used 768 dimensions (from the SHA256 placeholder).
You MUST delete it and create a new one with 384 dimensions.

1. Atlas UI → your cluster → Search & Vector Search
2. Find index named 'episodic_embedding_index' → DELETE it
3. Click 'Create Search Index' → JSON editor
4. Select: database=hotpotqa_rag  collection=episodic_memory
5. Paste this JSON:

{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 384,
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

6. Index name: episodic_embedding_index
7. Click Create — takes ~2 minutes to build

Then run: python verify_upload.py
""")

    client.close()
    print("run_once_reembed.py complete ✓")


if __name__ == "__main__":
    run()