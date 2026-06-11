"""
data.py — Preprocessing entry point

Usage:
    python data.py                              # full dev + bridge + failures only
    python data.py --n 200                      # subset of 200 records
    python data.py --type comparison            # dev + comparison failures
    python data.py --type bridge                # dev + bridge failures (default)
    python data.py --type all                   # dev + all types + failures
    python data.py --failures_only false        # include passing records too
    python data.py --type comparison --n 200    # 200 comparison failures

Output file named automatically:
    outputs/subset_{type}_{n or 'full'}.json
"""

import json
import argparse
import random
import os
from collections import Counter


def build_record(r):
    """Restructure one record into agent-ready input."""

    candidates = r["candidates"]  # already sorted by rank

    # Top-1 wrong passage
    top1_wrong = next((c for c in candidates if c["rank"] == 1), candidates[0])

    # Titles + first sentence only for Agent A (saves tokens)
    titles_and_first = []
    for c in candidates:
        first_sent = c["text"].split(".")[0].strip() + "."
        titles_and_first.append({
            "rank":           c["rank"],
            "title":          c["title"],
            "first_sentence": first_sent,
            "is_gold":        c["is_gold"],
            "bm25_score":     c["bm25_score"],
        })

    return {
        # Identity
        "id":              r["id"],
        "query":           r["query"],
        "answer":          r["answer"],
        "gold_titles":     r["gold_titles"],
        "type":            r["type"],
        "level":           r["level"],
        "split":           r["split"],
        "gold_ranks":      r["gold_ranks"],
        "first_gold_rank": r["first_gold_rank"],
        "top1_correct":    r["top1_correct"],

        # BM25 metrics (kept for baseline comparison later)
        "hits_at_1":   r["hits_at_1"],
        "hits_at_3":   r["hits_at_3"],
        "mrr":         r["mrr"],
        "ndcg_at_10":  r["ndcg_at_10"],

        # Agent A inputs
        "bridge_candidates":         r["bridge_candidates"],
        "only_answer_has":           r["only_answer_has"],
        "only_wrong_has":            r["only_wrong_has"],
        "titles_and_first_sentence": titles_and_first,

        # Agent B inputs
        "top1_wrong_title":     top1_wrong["title"],
        "top1_wrong_text":      top1_wrong["text"],
        "all_candidate_titles": [c["title"] for c in candidates],
    }


def print_breakdown(records, label):
    types  = Counter(r["type"]  for r in records)
    levels = Counter(r["level"] for r in records)
    fails  = sum(1 for r in records if not r["top1_correct"])
    pct    = 100 * fails / len(records) if records else 0
    print(f"\n  {label}")
    print(f"  Total   : {len(records)}")
    print(f"  Types   : {dict(types)}")
    print(f"  Levels  : {dict(levels)}")
    print(f"  Failures: {fails}  ({pct:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Preprocess BM25 results for agent pipeline")
    parser.add_argument("--n",             type=int, default=None,
                        help="Subset size after shuffle (default: full set)")
    parser.add_argument("--type",          type=str, default="bridge",
                        choices=["bridge", "comparison", "all"],
                        help="Question type: bridge | comparison | all  (default: bridge)")
    parser.add_argument("--failures_only", type=str, default="true",
                        help="Only BM25 failures top1_correct==False (default: true)")
    parser.add_argument("--input",         type=str, default="hard_failures.json",
                        help="Input JSON file path")
    parser.add_argument("--seed",          type=int, default=42,
                        help="Random seed (default: 42)")
    args = parser.parse_args()

    failures_only = args.failures_only.lower() != "false"

    # ── Load ──────────────────────────────────────────────────────────────────
    print(f"Loading {args.input}...")
    with open(args.input, "r") as f:
        data = json.load(f)
    print(f"Total records in file: {len(data)}")

    # ── Show full dev breakdown before filtering ───────────────────────────────
    dev_all = [r for r in data if r["split"] == "dev"]
    print_breakdown(dev_all, "DEV — full (before filter)")

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = [r for r in data if r["split"] == "dev"]

    if args.type != "all":
        filtered = [r for r in filtered if r["type"] == args.type]

    if failures_only:
        filtered = [r for r in filtered if not r["top1_correct"]]

    print_breakdown(filtered, f"AFTER FILTER — type={args.type}  failures_only={failures_only}")

    # ── Shuffle with fixed seed ────────────────────────────────────────────────
    random.seed(args.seed)
    random.shuffle(filtered)

    # ── Subset ────────────────────────────────────────────────────────────────
    if args.n:
        if args.n > len(filtered):
            print(f"\n  WARNING: --n {args.n} > available {len(filtered)}, using full set")
        else:
            filtered = filtered[: args.n]
            print(f"\n  Subset: {args.n} records  (seed={args.seed})")

    # ── Build agent-ready records ──────────────────────────────────────────────
    output = [build_record(r) for r in filtered]

    # ── Auto-name output file ──────────────────────────────────────────────────
    size_tag = str(args.n) if args.n and args.n <= len(filtered) else "full"
    out_name = f"subset_{args.type}_{size_tag}.json"
    os.makedirs("outputs", exist_ok=True)
    out_path = os.path.join("outputs", out_name)

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved {len(output)} records → {out_path}")
    print(f"\nNext — set input path for agents:")
    print(f"  Windows : set INPUT_PATH=outputs/{out_name}")
    print(f"  Mac/Linux: export INPUT_PATH=outputs/{out_name}")
    print(f"  Then run : python agent_a.py")


if __name__ == "__main__":
    main()