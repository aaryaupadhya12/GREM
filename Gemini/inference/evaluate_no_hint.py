"""
evaluate.py — Compute hackathon metrics with adaptive episodic memory

Adaptive Atlas usage: episodic hints injected ONLY when the cross-encoder
is uncertain (small gap between top-1 and top-2 scores). This keeps Atlas
load-bearing at inference while avoiding the noise penalty on confident queries.
"""

import json
import os
import math
import numpy as np
from collections import Counter
from sentence_transformers import CrossEncoder, SentenceTransformer
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()

# ── Config ─────────────────────────────────────────────────────
TEST_PATH    = r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Gemini\Inference\outputs\test_split.json"
MODEL_PATH   = r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\Re-ranker_output"
METRICS_OUT  = r"outputs/metrics_evaluate.json"

ADAPTIVE_HINTS       = True   # Atlas hints only when re-ranker is uncertain
LOW_CONF_THRESHOLD   = 0.1   # gap between top-1 and top-2 score
EPISODIC_K           = 3
# ───────────────────────────────────────────────────────────────


# Load models once
print("[init] Loading re-ranker...")
reranker = CrossEncoder(MODEL_PATH)

print("[init] Loading sentence transformer for episodic search...")
encoder = SentenceTransformer("all-MiniLM-L6-v2")
mongo   = MongoClient(os.environ["MONGO_URI"])["GREM"]


def fetch_episodic_hints(query, k=3):
    try:
        q_emb = encoder.encode(query, normalize_embeddings=True).tolist()
        return list(mongo["episodic_memory"].aggregate([{
            "$vectorSearch": {
                "index":         "episodic_embedding_index",
                "path":          "query_embedding",
                "queryVector":   q_emb,
                "numCandidates": 50,
                "limit":         k,
            }
        }]))
    except Exception as e:
        print(f"[hints] Vector search failed: {e}")
        return []


def ndcg_at_k(gold_ranks, k):
    dcg = sum(1.0 / math.log2(r + 1) for r in gold_ranks if r <= k)
    n_relevant = min(len(gold_ranks), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(n_relevant))
    return dcg / idcg if idcg > 0 else 0.0


def evaluate(test_records):
    metrics = {
        "hits_at_1":   [],
        "hits_at_2":   [],
        "recall_at_2": [],
        "mrr":         [],
        "ndcg_at_2":   [],
        "ndcg_at_5":   [],
    }

    failure_recovery = Counter()
    failure_total    = Counter()
    ground_count     = 0
    lucky_count      = 0
    hint_invoked     = 0     # how many records actually used Atlas hints

    print(f"\n[eval] Running re-ranker on {len(test_records)} test records...")
    print(f"[eval] Adaptive hints: {ADAPTIVE_HINTS}  threshold: {LOW_CONF_THRESHOLD}")

    for i, record in enumerate(test_records):
        query        = record["query"]
        candidates   = record["titles_and_first_sentence"]
        gold_titles  = set(record["gold_titles"])
        failure_mode = record["failure_mode"]

        # ── First pass: distilled re-ranker only (no hints) ──────────
        pairs  = [(query, f"{c['title']} — {c['first_sentence']}") for c in candidates]
        scores = reranker.predict(pairs)

        # ── Adaptive Atlas: rescore only if model uncertain ─────────
        if ADAPTIVE_HINTS:
            sorted_scores  = sorted(scores, reverse=True)
            confidence_gap = sorted_scores[0] - sorted_scores[1]

            if confidence_gap < LOW_CONF_THRESHOLD:
                hint_invoked += 1
                hints = fetch_episodic_hints(query, EPISODIC_K)
                ctx   = " | ".join(h.get("aggregator_chain", "")[:100] for h in hints)
                augmented_query = f"{query}\n[Verified hints: {ctx[:300]}]"
                pairs  = [(augmented_query, f"{c['title']} — {c['first_sentence']}") for c in candidates]
                scores = reranker.predict(pairs)

        # ── Re-rank by score ────────────────────────────────────────
        ranked = sorted(zip(candidates, scores), key=lambda x: -x[1])

        gold_ranks = [
            idx + 1 for idx, (c, _) in enumerate(ranked)
            if c["title"] in gold_titles
        ]

        if not gold_ranks:
            continue

        first_gold = min(gold_ranks)
        n_in_top2  = sum(1 for r in gold_ranks if r <= 2)

        hits_1 = int(first_gold == 1)
        hits_2 = int(first_gold <= 2)

        metrics["hits_at_1"].append(hits_1)
        metrics["hits_at_2"].append(hits_2)
        metrics["recall_at_2"].append(n_in_top2 / len(gold_titles))
        metrics["mrr"].append(1.0 / first_gold)
        metrics["ndcg_at_2"].append(ndcg_at_k(gold_ranks, 2))
        metrics["ndcg_at_5"].append(ndcg_at_k(gold_ranks, 5))

        failure_total[failure_mode] += 1
        if hits_1:
            failure_recovery[failure_mode] += 1

        if hits_1:
            if gold_ranks[0] == 1:
                ground_count += 1
            else:
                lucky_count += 1

        if (i + 1) % 25 == 0:
            running = float(np.mean(metrics["hits_at_1"]))
            print(f"  [{i+1}/{len(test_records)}] running Hits@1: {running:.3f}  hints used: {hint_invoked}")

    n = len(metrics["hits_at_1"])
    avg = {k: float(np.mean(v)) for k, v in metrics.items()}

    correct     = ground_count + lucky_count
    ground_rate = ground_count / correct if correct else 0.0
    lucky_rate  = lucky_count  / correct if correct else 0.0

    mode_recovery = {}
    for mode in failure_total:
        recovered = failure_recovery.get(mode, 0)
        total     = failure_total[mode]
        mode_recovery[mode] = {
            "recovered": recovered,
            "total":     total,
            "rate":      recovered / total if total else 0.0,
        }

    results = {
        "n_test_records":       n,
        "bm25_hits_at_1":       0.0,
        "reranker_hits_at_1":   avg["hits_at_1"],
        "reranker_hits_at_2":   avg["hits_at_2"],
        "reranker_recall_at_2": avg["recall_at_2"],
        "reranker_mrr":         avg["mrr"],
        "reranker_ndcg_at_2":   avg["ndcg_at_2"],
        "reranker_ndcg_at_5":   avg["ndcg_at_5"],
        "delta_hits_at_1":      avg["hits_at_1"] - 0.0,
        "ground_rate":          ground_rate,
        "lucky_rate":           lucky_rate,
        "failure_mode_recovery": mode_recovery,
        "adaptive_hints":       ADAPTIVE_HINTS,
        "hint_invoked_count":   hint_invoked,
        "hint_invoked_rate":    hint_invoked / n if n else 0.0,
    }

    return results


def print_results(r):
    print("\n" + "=" * 65)
    print(f"  HACKATHON RESULTS — Dev Hard Failures (n={r['n_test_records']})")
    print("=" * 65)
    print(f"  BM25 baseline Hits@1     : {r['bm25_hits_at_1']:.4f}")
    print(f"  GREM Hits@1              : {r['reranker_hits_at_1']:.4f}")
    print(f"  GREM Hits@2              : {r['reranker_hits_at_2']:.4f}")
    print(f"  GREM Recall@2            : {r['reranker_recall_at_2']:.4f}")
    print(f"  GREM MRR                 : {r['reranker_mrr']:.4f}")
    print(f"  GREM nDCG@2              : {r['reranker_ndcg_at_2']:.4f}")
    print(f"  GREM nDCG@5              : {r['reranker_ndcg_at_5']:.4f}")
    print()
    print(f"  RECOVERY DELTA Hits@1    : +{r['delta_hits_at_1']:.4f}")
    print(f"  Ground Rate              : {r['ground_rate']:.4f}")
    print()
    print(f"  Adaptive Atlas usage     : {r['hint_invoked_count']}/{r['n_test_records']} queries ({r['hint_invoked_rate']*100:.1f}%)")
    print()
    print(f"  Recovery by failure mode:")
    for mode, stats in r["failure_mode_recovery"].items():
        print(f"    {mode:25s} {stats['recovered']:>3}/{stats['total']:<3}  ({stats['rate']*100:.1f}%)")
    print("=" * 65)


def write_metrics_to_mongo(results):
    try:
        col = MongoClient(os.environ["MONGO_URI"])["GREM"]["final_metrics"]
        col.delete_many({})
        col.insert_one(results)
        print("[mongo] Final metrics written to GREM.final_metrics")
    except Exception as e:
        print(f"[mongo] Failed to write metrics: {e}")


def main():
    os.makedirs("outputs", exist_ok=True)

    with open(TEST_PATH, "r", encoding="utf-8") as f:
        test_records = json.load(f)
    print(f"[load] Loaded {len(test_records)} test records")

    results = evaluate(test_records)
    print_results(results)

    with open(METRICS_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[save] Metrics → {METRICS_OUT}")

    write_metrics_to_mongo(results)


if __name__ == "__main__":
    main()