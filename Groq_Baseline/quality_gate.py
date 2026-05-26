"""
quality_gate.py — Quality Gate

Usage:
    python quality_gate.py

Reads:  outputs/agent_c_out.json
Writes: outputs/quality_gated.json

Splits records into passed (→ MongoDB) and failed (→ session RAM).
Prints a summary with sanity checks.
"""

import json
import os


INPUT_PATH  = r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Groq_Baseline\outputs\agent_c_out.json"
OUTPUT_PATH = r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Groq_Baseline\outputs\quality_gated.json"


def print_record(r, label=""):
    print(f"\n  {'─'*60}")
    if label:
        print(f"  [{label}]")
    print(f"  Query      : {r['query'][:90]}")
    print(f"  Gold titles: {r['gold_titles']}")
    print(f"  Top-1 wrong: {r['top1_wrong']}")
    print(f"  Gold rank  : {r['first_gold_rank']}")
    print(f"  Entity     : {r['entity_summary']}")
    print(f"  Chain      : {r['chain_summary']}")
    print(f"  Chunk      : {r['chunk_summary']}")
    print(f"  Relevant   : {r['relevant']}")


def main():
    with open(INPUT_PATH, "r") as f:
        records = json.load(f)

    total  = len(records)
    passed = [r for r in records if r["relevant"] is True]
    failed = [r for r in records if r["relevant"] is False]

    pass_rate = len(passed) / total if total > 0 else 0

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  QUALITY GATE RESULTS")
    print(f"{'='*60}")
    print(f"  Total processed : {total}")
    print(f"  Passed (→ Mongo): {len(passed)}  ({100*pass_rate:.1f}%)")
    print(f"  Failed (→ RAM)  : {len(failed)}  ({100*(1-pass_rate):.1f}%)")

    # ── Sanity checks ─────────────────────────────────────────────────────────
    print(f"\n  Sanity checks:")

    if pass_rate > 0.90:
        print(f"  Pass rate {100*pass_rate:.1f}% is very high — Agent C may not be discriminating.")
        print(f"    Review agent_c.md and tighten the relevant: false conditions.")
    elif pass_rate < 0.30:
        print(f"  Pass rate {100*pass_rate:.1f}% is very low — Agent C may be too strict.")
        print(f"    Check agent_c_out.json for parse errors or prompt issues.")
    else:
        print(f"  Pass rate {100*pass_rate:.1f}% looks reasonable (target: 60-80%)")

    # Token usage
    total_tokens = sum(
        r.get("tokens_used", 0) + r.get("tokens_a", 0) + r.get("tokens_b", 0)
        for r in records
    )
    avg_tokens = total_tokens / total if total > 0 else 0
    print(f"  ✓ Avg tokens per record (A+B+C): {avg_tokens:.0f}")
    print(f"  ✓ Total tokens this run: {total_tokens}")

    # ── Sample output ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  SAMPLE PASSED RECORDS")
    print(f"{'='*60}")
    for r in passed[:2]:
        print_record(r, label="PASSED")

    print(f"\n{'='*60}")
    print(f"  SAMPLE FAILED RECORDS")
    print(f"{'='*60}")
    for r in failed[:2]:
        print_record(r, label="FAILED")

    # ── Save ──────────────────────────────────────────────────────────────────
    output = {
        "summary": {
            "total":     total,
            "passed":    len(passed),
            "failed":    len(failed),
            "pass_rate": round(pass_rate, 4),
            "total_tokens_all_agents": total_tokens,
            "avg_tokens_per_record":   round(avg_tokens, 1),
        },
        "passed": passed,   # → MongoDB Atlas later
        "failed": failed,   # → Session RAM equivalent
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n\nSaved → {OUTPUT_PATH}")
    print(f"Next step: review outputs/quality_gated.json then plug in Aggregator.")


if __name__ == "__main__":
    main()