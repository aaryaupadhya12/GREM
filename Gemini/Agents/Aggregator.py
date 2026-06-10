"""
aggregator.py — Grounded Reasoning Synthesiser (Vertex AI / Gemini)

Usage:
    python aggregator.py

Records with q_final > 0.5 AND resolved == true → MongoDB
Everything else                                  → session RAM
"""

import json
import os
import time
import google.auth
import google.auth.transport.requests
from openai import OpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from dotenv import load_dotenv
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID = os.environ["GCP_PROJECT_ID"]
LOCATION   = os.environ.get("GCP_LOCATION", "us-central1")

MODEL          = "google/gemini-2.5-flash-lite"
MAX_TOKENS     = 3000
TEMPERATURE    = 0.0
RATE_LIMIT_S   = 0.3
TOKEN_REFRESH_EVERY = 50
INPUT_PATH     = r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Gemini\outputs\quality_gated.json"
OUTPUT_PATH    = "outputs/aggregator_out.json"
# ─────────────────────────────────────────────────────────────────────────────


def get_fresh_client():
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    return wrap_openai(
        OpenAI(
            api_key=credentials.token,
            base_url=f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/openapi/"
        )
    )


def load_system_prompt():
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Gemini\Context\Context.md", "r", encoding="utf-8") as f:
        context = f.read()
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Gemini\Context\Aggregator.md", "r", encoding="utf-8") as f:
        aggregator = f.read()
    return context + "\n\n" + aggregator


def build_user_prompt(record):
    gold_ranks_str = ", ".join(
        str(r) for r in record.get("gold_ranks", [record["first_gold_rank"]])
    )

    return f"""Query: {record["query"]}
First gold rank: {record["first_gold_rank"]}
All gold ranks: {gold_ranks_str}

Agent A EntitySummary:
{record["entity_summary"]}

Agent B ChainSummary:
{record["chain_summary"]}

Agent C ChunkSummary:
{record["chunk_summary"]}

Produce your JSON output now. No markdown fences. Start with {{ and end with }}."""


def parse_aggregator_output(raw_output):
    """Robust JSON parser — handles markdown fences, prefixes, truncation."""
    try:
        clean = raw_output.strip()

        # Strip markdown fences if present
        if clean.startswith("```"):
            # Remove first line (```json or ```)
            if "\n" in clean:
                clean = clean.split("\n", 1)[1]
            else:
                clean = clean.replace("```json", "").replace("```", "")
        if clean.endswith("```"):
            clean = clean.rsplit("```", 1)[0]

        # Extract JSON between first { and last }
        start = clean.find("{")
        end   = clean.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No valid JSON braces found")

        clean = clean[start:end + 1].strip()

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
        print(f"  Raw: {raw_output[:300]}")
        return {
            "aggregator_chain": raw_output,
            "q_final":          0.0,
            "resolved":         False,
            "failure_mode":     "parse_error",
            "parse_error":      True,
        }


def load_checkpoint():
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            results = json.load(f)
        done_ids = {r["id"] for r in results}
        print(f"[checkpoint] Resuming — {len(done_ids)} records already done")
        return results, done_ids
    return [], set()


def save(results):
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def call_gemini(client, system_prompt, record):
    user_prompt = build_user_prompt(record)
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        response_format={"type": "json_object"},   # ADD THIS LINE
    )
def process_record(client, system_prompt, record):
    resp        = call_gemini(client, system_prompt, record)
    raw_output  = resp.choices[0].message.content.strip()
    tokens_used = resp.usage.total_tokens
    parsed      = parse_aggregator_output(raw_output)
    return parsed, tokens_used


def main():
    client        = get_fresh_client()
    system_prompt = load_system_prompt()

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    passed_records = data["passed"]
    print(f"[aggregator] Loaded {len(passed_records)} passed records from quality gate")
    print(f"[aggregator] Model: {MODEL}")

    results, done_ids = load_checkpoint()

    mongo_count = 0
    ram_count   = 0
    error_count = 0

    for i, record in enumerate(passed_records):
        if record["id"] in done_ids:
            continue

        if i > 0 and i % TOKEN_REFRESH_EVERY == 0:
            client = get_fresh_client()
            print(f"[token] Refreshed at record {i}")

        print(f"\n[{i+1}/{len(passed_records)}] {record['id']}")
        print(f"  Query      : {record['query'][:90]}")
        print(f"  Gold titles: {record['gold_titles']}")

        try:
            parsed, tokens_used = process_record(client, system_prompt, record)

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
                "id":               record["id"],
                "query":            record["query"],
                "gold_titles":      record["gold_titles"],
                "top1_wrong":       record["top1_wrong"],
                "first_gold_rank":  record["first_gold_rank"],
                "gold_ranks":       record.get("gold_ranks", [record["first_gold_rank"]]),
                "entity_summary":   record["entity_summary"],
                "chain_summary":    record["chain_summary"],
                "chunk_summary":    record["chunk_summary"],
                "aggregator_chain": parsed["aggregator_chain"],
                "q_final":          parsed["q_final"],
                "resolved":         parsed["resolved"],
                "failure_mode":     parsed["failure_mode"],
                "parse_error":      parsed["parse_error"],
                "storage_route":    storage_route,
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

    total = len(results)
    print(f"\n{'='*60}")
    print(f"  AGGREGATOR COMPLETE")
    print(f"{'='*60}")
    print(f"  Total processed : {total}")
    if total > 0:
        print(f"  → MongoDB       : {mongo_count}  ({100*mongo_count/total:.1f}%)")
        print(f"  → Session RAM   : {ram_count}   ({100*ram_count/total:.1f}%)")
    print(f"  Parse errors    : {error_count}")
    print(f"\n  Saved → {OUTPUT_PATH}")

    if error_count > 5:
        print(f"\n  WARNING: {error_count} parse errors — review Aggregator.md JSON output instruction")

    from collections import Counter
    modes = Counter(r["failure_mode"] for r in results if not r["parse_error"])
    print(f"\n  Failure mode distribution:")
    for mode, count in modes.most_common():
        print(f"    {mode}: {count}")


if __name__ == "__main__":
    main()