"""
data.py — Preprocessing entry point

Usage:
    python data.py --n 20        # subset of 20 records
    python data.py               # full dev+bridge+hard set
"""

import json
import argparse
import random
import os


def load_md(path):
    with open(path, "r") as f:
        return f.read()


def build_record(r):
    """Restructure one hard_failures record into agent-ready input."""

    candidates = r["candidates"]  # already sorted by rank

    # Top-1 wrong passage (rank 1)
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
        "id":    r["id"],
        "query": r["query"],
        "answer": r["answer"],
        "gold_titles":  r["gold_titles"],
        "type":         r["type"],
        "level":        r["level"],
        "split":        r["split"],
        "gold_ranks":   r["gold_ranks"],
        "first_gold_rank": r["first_gold_rank"],

        # Agent A inputs
        "bridge_candidates":      r["bridge_candidates"],
        "only_answer_has":        r["only_answer_has"],
        "only_wrong_has":         r["only_wrong_has"],
        "titles_and_first_sentence": titles_and_first,

        # Agent B inputs
        "top1_wrong_title": top1_wrong["title"],
        "top1_wrong_text":  top1_wrong["text"],
        "all_candidate_titles": [c["title"] for c in candidates],
    }


def main():
    parser = argparse.ArgumentParser(description="Preprocess hard_failures.json for agent pipeline")
    parser.add_argument("--n", type=int, default=None, help="Subset size (default: full set)")
    parser.add_argument("--input", type=str, default=r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\Dataset\hard_failures.json", help="Input file path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for shuffle")
    args = parser.parse_args()

    # Load
    print(f"Loading {args.input}...")
    with open(args.input, "r") as f:
        data = json.load(f)
    print(f"Total records loaded: {len(data)}")

    # Filter: dev + bridge + hard
    filtered = [
        r for r in data
        if r["split"] == "dev"
        and r["type"] == "bridge"
        and r["level"] == "hard"
    ]
    print(f"After filter (dev + bridge + hard): {len(filtered)}")

    # Shuffle with fixed seed — reproducible subset
    random.seed(args.seed)
    random.shuffle(filtered)

    # Subset if --n provided
    if args.n:
        filtered = filtered[: args.n]
        print(f"Using subset of {args.n} records (seed={args.seed})")

    # Build agent-ready records
    output = [build_record(r) for r in filtered]

    # Save
    os.makedirs("outputs", exist_ok=True)
    out_path = "outputs/subset.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved {len(output)} records → {out_path}")
    print("\nSample record keys:", list(output[0].keys()) if output else "empty")


if __name__ == "__main__":
    main()