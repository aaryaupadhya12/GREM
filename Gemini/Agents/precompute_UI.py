"""
precompute_demo.py — Cache 5 demo inference traces in MongoDB via MCP
"""
import os
import json
import random
from sentence_transformers import CrossEncoder
from dotenv import load_dotenv
load_dotenv()

# Import MCP client
from Mongodb_mcp_integration import mcp_delete_many, mcp_insert_many

random.seed(42)

MODEL_PATH = r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\Re-ranker_output"
TEST_PATH  = r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Gemini\Inference\outputs\test_split.json"

DB         = "GREM"
COLLECTION = "demo_traces"

print("Loading re-ranker...")
reranker = CrossEncoder(MODEL_PATH)

with open(TEST_PATH, "r", encoding="utf-8") as f:
    test_records = json.load(f)

# Pick 5 records — one chain_break, two entity_drift, two distractor
chain_break  = sorted([r for r in test_records if r["failure_mode"] == "chain_break"],         key=lambda r: -r["q_final"])
entity_drift = sorted([r for r in test_records if r["failure_mode"] == "entity_drift"],        key=lambda r: -r["q_final"])
distractor   = sorted([r for r in test_records if r["failure_mode"] == "distractor_confusion"], key=lambda r: -r["q_final"])

demo_records = [
    chain_break[0],
    entity_drift[0],
    entity_drift[1],
    distractor[0],
    distractor[1],
]

print(f"\nProcessing {len(demo_records)} demo records...")

traces = []
for i, r in enumerate(demo_records, 1):
    query      = r["query"]
    candidates = r["titles_and_first_sentence"]
    gold_set   = set(r["gold_titles"])

    pairs  = [(query, f"{c['title']} — {c['first_sentence']}") for c in candidates]
    scores = reranker.predict(pairs).tolist()

    bm25_ranking = [
        {
            "rank":    idx + 1,
            "title":   c["title"],
            "snippet": c["first_sentence"][:200],
            "is_gold": c["title"] in gold_set,
        }
        for idx, c in enumerate(candidates)
    ]

    ranked = sorted(zip(candidates, scores), key=lambda x: -x[1])
    grem_ranking = [
        {
            "rank":    idx + 1,
            "title":   c["title"],
            "snippet": c["first_sentence"][:200],
            "is_gold": c["title"] in gold_set,
            "score":   round(float(s), 4),
        }
        for idx, (c, s) in enumerate(ranked)
    ]

    bm25_first_gold = min(
        (idx + 1 for idx, c in enumerate(candidates) if c["title"] in gold_set),
        default=99
    )
    grem_first_gold = min(
        (idx + 1 for idx, (c, _) in enumerate(ranked) if c["title"] in gold_set),
        default=99
    )

    trace = {
        "demo_id":          f"q{i}",
        "query":            query,
        "failure_mode":     r["failure_mode"],
        "gold_titles":      r["gold_titles"],
        "aggregator_chain": r.get("aggregator_chain", "")[:500],
        "q_final":          r["q_final"],
        "bm25_first_gold":  bm25_first_gold,
        "grem_first_gold":  grem_first_gold,
        "bm25_ranking":     bm25_ranking,
        "grem_ranking":     grem_ranking,
    }
    traces.append(trace)
    print(f"  [{i}] {r['failure_mode']:25s} BM25 rank {bm25_first_gold} → GREM rank {grem_first_gold}")

# ── Write via MCP ──────────────────────────────────────────────
print(f"\nClearing existing demo_traces via MCP...")
mcp_delete_many(DB, COLLECTION, {})

print(f"Inserting {len(traces)} demo traces via MCP...")
result = mcp_insert_many(DB, COLLECTION, traces)

if "error" in result:
    print(f"✗ MCP insert failed: {result['error']}")
else:
    print(f"{len(traces)} demo traces saved to {DB}.{COLLECTION}")