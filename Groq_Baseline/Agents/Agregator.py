"""
aggregator.py — Grounded Reasoning Synthesiser

Usage:
    python aggregator.py

Reads:  outputs/quality_gated.json  (passed array only)
Writes: outputs/aggregator_out.json (saves after every record)

Records with q_final > 0.5 AND resolved == true → MongoDB
Everything else                                  → session RAM

Set your API key:
    export GROQ_API_KEY_AGG="gsk_..."
"""

import json
import os
import time
from openai import OpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from dotenv import load_dotenv
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY_AGG")
LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"]               = "true"
os.environ["LANGSMITH_PROJECT"]               = "GREM"
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"]  = "false"
os.environ["LANGSMITH_ENDPOINT"]              = "https://apac.api.smith.langchain.com"
os.environ["LANGSMITH_COMPRESSION"]           = "false"
os.environ["LANGSMITH_BATCH_SIZE"]            = "1"
MODEL          = "llama-3.3-70b-versatile"
MAX_TOKENS     = 350        # aggregator_chain ~260 + JSON structure overhead
TEMPERATURE    = 0.0
RATE_LIMIT_S   = 1.0
INPUT_PATH     = r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Groq_Baseline\outputs\quality_gated.json"
OUTPUT_PATH    = "outputs/aggregator_out.json"
# ─────────────────────────────────────────────────────────────────────────────


def load_system_prompt():
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Groq_Baseline\Context\Context.md", "r") as f:
        context = f.read()
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Groq_Baseline\Context\Aggregator.md", "r") as f:
        aggregator = f.read()
    return context + "\n\n" + aggregator


def build_user_prompt(record):
    return f"""Query: {record["query"]}

Agent A EntitySummary:
{record["entity_summary"]}

Agent B ChainSummary:
{record["chain_summary"]}

Agent C ChunkSummary:
{record["chunk_summary"]}

Produce your JSON output now."""


def parse_aggregator_output(raw_output):
    try:
        clean  = raw_output.strip().strip("```json").strip("```").strip()
        parsed = json.loads(clean)
        return {
            "aggregator_chain": parsed.get("aggregator_chain", ""),
            "q_final":          float(parsed.get("q_final", 0.0)),
            "resolved":         bool(parsed.get("resolved", False)),
            "failure_mode":     parsed.get("failure_mode", "unknown"),
            "parse_error":      False,
        }
    except Exception as e:
        print(f"  WARNING: JSON parse failed — {e}")
        print(f"  Raw: {raw_output[:200]}")
        return {
            "aggregator_chain": raw_output,
            "q_final":          0.0,
            "resolved":         False,
            "failure_mode":     "parse_error",
            "parse_error":      True,
        }


def load_checkpoint():
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r") as f:
            results = json.load(f)
        done_ids = {r["id"] for r in results}
        print(f"[checkpoint] Resuming — {len(done_ids)} records already done")
        return results, done_ids
    return [], set()


def save(results):
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)


def call_groq(client, system_prompt, record):
    user_prompt = build_user_prompt(record)
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )


@traceable(name="aggregator_record", run_type="chain", tags=["aggregator", "groq"])
def process_record(client, system_prompt, record):
    resp        = call_groq(client, system_prompt, record)
    raw_output  = resp.choices[0].message.content.strip()
    tokens_used = resp.usage.total_tokens
    parsed      = parse_aggregator_output(raw_output)
    return parsed, tokens_used


def main():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY_AGG environment variable not set")

    client = wrap_openai(
        OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
    )
    system_prompt = load_system_prompt()

    # ── Load passed records from quality gate ─────────────────────────────────
    with open(INPUT_PATH, "r") as f:
        data = json.load(f)

    passed_records = data["passed"]        # extract passed array — NOT the root object
    print(f"[aggregator] Loaded {len(passed_records)} passed records from quality gate")

    results, done_ids = load_checkpoint()

    # ── Counters for summary ──────────────────────────────────────────────────
    mongo_count = 0
    ram_count   = 0
    error_count = 0

    for i, record in enumerate(passed_records):
        if record["id"] in done_ids:
            continue

        print(f"\n[{i+1}/{len(passed_records)}] {record['id']}")
        print(f"  Query      : {record['query'][:90]}")
        print(f"  Gold titles: {record['gold_titles']}")

        try:
            parsed, tokens_used = process_record(client, system_prompt, record)

            # ── Quality writeback decision ────────────────────────────────────
            goes_to_mongo = parsed["q_final"] > 0.5 and parsed["resolved"]
            storage_route = "mongodb" if goes_to_mongo else "session_ram"

            if goes_to_mongo:
                mongo_count += 1
            else:
                ram_count += 1

            if parsed["parse_error"]:
                error_count += 1

            print(f"  Chain      : {parsed['aggregator_chain'][:120]}")
            print(f"  q_final    : {parsed['q_final']}")
            print(f"  resolved   : {parsed['resolved']}")
            print(f"  failure    : {parsed['failure_mode']}")
            print(f"  storage    : {storage_route}")
            print(f"  tokens     : {tokens_used}")

            results.append({
                # Identity
                "id":               record["id"],
                "query":            record["query"],
                "gold_titles":      record["gold_titles"],
                "top1_wrong":       record["top1_wrong"],
                "first_gold_rank":  record["first_gold_rank"],
                # Agent summaries (carried forward)
                "entity_summary":   record["entity_summary"],
                "chain_summary":    record["chain_summary"],
                "chunk_summary":    record["chunk_summary"],
                # Aggregator output
                "aggregator_chain": parsed["aggregator_chain"],
                "q_final":          parsed["q_final"],
                "resolved":         parsed["resolved"],
                "failure_mode":     parsed["failure_mode"],
                "parse_error":      parsed["parse_error"],
                # Routing
                "storage_route":    storage_route,
                # Meta
                "tokens_used":      tokens_used,
                "tokens_a":         record.get("tokens_a", 0),
                "tokens_b":         record.get("tokens_b", 0),
                "tokens_c":         record.get("tokens_used", 0),
                "model":            MODEL,
                "agent":            "aggregator",
                "timestamp":        time.time(),
            })

            save(results)

        except Exception as e:
            print(f"  ERROR: {e}")
            print(f"  Skipping and continuing...")
            time.sleep(3)
            continue

        time.sleep(RATE_LIMIT_S)

    # ── Final summary ─────────────────────────────────────────────────────────
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  AGGREGATOR COMPLETE")
    print(f"{'='*60}")
    print(f"  Total processed : {total}")
    print(f"  → MongoDB       : {mongo_count}  ({100*mongo_count/total:.1f}% if total else 0%)")
    print(f"  → Session RAM   : {ram_count}   ({100*ram_count/total:.1f}% if total else 0%)")
    print(f"  Parse errors    : {error_count}")
    print(f"\n  Saved → {OUTPUT_PATH}")

    if error_count > 5:
        print(f"\n  WARNING: {error_count} parse errors — review Aggregator.md JSON output instruction")

    # ── Failure mode distribution ─────────────────────────────────────────────
    from collections import Counter
    modes = Counter(r["failure_mode"] for r in results if not r["parse_error"])
    print(f"\n  Failure mode distribution:")
    for mode, count in modes.most_common():
        print(f"    {mode}: {count}")


if __name__ == "__main__":
    main()