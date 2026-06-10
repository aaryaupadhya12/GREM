"""
split_train_test.py — Create train/test split from verified chains

Reads:  outputs/aggregator_out.json
        outputs/subset_bridge_full.json  (or wherever your original subset is)
Writes: outputs/train_split.json
        outputs/test_split.json

The split is 80/20 with fixed random seed for reproducibility.
"""

import json
import random
import os

# ── Config ─────────────────────────────────────────────────────
random.seed(42)

AGGREGATOR_PATH = r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Gemini\Agents\outputs\aggregator_out.json"
SUBSET_PATH     = r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Gemini\outputs\2000_final.json"
TRAIN_OUT       = "outputs/train_split.json"
TEST_OUT        = "outputs/test_split.json"
TEST_FRACTION   = 0.20
# ───────────────────────────────────────────────────────────────


def main():
    # Load aggregator output (verified chains with q_final, failure_mode)
    with open(AGGREGATOR_PATH, "r", encoding="utf-8") as f:
        agg_records = json.load(f)
    print(f"[load] Aggregator records: {len(agg_records)}")

    # Load original subset (has the full candidate list per query)
    with open(SUBSET_PATH, "r", encoding="utf-8") as f:
        subset_records = json.load(f)
    print(f"[load] Subset records   : {len(subset_records)}")

    # Index subset by id for fast lookup
    subset_by_id = {r["id"]: r for r in subset_records}

    # Keep only records that:
    # 1. Passed quality gate (storage_route == mongodb)
    # 2. Are not parse errors
    # 3. Have matching candidate data in subset
    verified = []
    for r in agg_records:
        if r.get("parse_error"):
            continue
        if r.get("storage_route") != "mongodb":
            continue
        if r["id"] not in subset_by_id:
            continue
        
        # Attach the candidate list from the original subset
        r["titles_and_first_sentence"] = subset_by_id[r["id"]]["titles_and_first_sentence"]
        verified.append(r)
    
    print(f"[filter] Verified records ready for split: {len(verified)}")

    if len(verified) < 50:
        print(f"WARNING: only {len(verified)} verified records — train/test split will be too small")
        print(f"  Need at least 50 for credible metrics")

    # Shuffle deterministically
    random.shuffle(verified)

    # Split
    n_test  = int(len(verified) * TEST_FRACTION)
    test    = verified[:n_test]
    train   = verified[n_test:]

    # Save
    with open(TRAIN_OUT, "w", encoding="utf-8") as f:
        json.dump(train, f, indent=2, ensure_ascii=False)
    
    with open(TEST_OUT, "w", encoding="utf-8") as f:
        json.dump(test, f, indent=2, ensure_ascii=False)

    print(f"\n[output] Train: {len(train)} records → {TRAIN_OUT}")
    print(f"[output] Test : {len(test)} records → {TEST_OUT}")

    # Stratification check — failure mode distribution
    from collections import Counter
    train_modes = Counter(r["failure_mode"] for r in train)
    test_modes  = Counter(r["failure_mode"] for r in test)
    
    print(f"\n[verify] Failure mode distribution:")
    print(f"  {'Mode':<25} {'Train':>10} {'Test':>10}")
    all_modes = set(train_modes.keys()) | set(test_modes.keys())
    for mode in sorted(all_modes):
        print(f"  {mode:<25} {train_modes.get(mode, 0):>10} {test_modes.get(mode, 0):>10}")


if __name__ == "__main__":
    main()