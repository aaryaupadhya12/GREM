"""
agent_c.py — Context Relevance Validator

Usage:
    python agent_c.py

Reads:  outputs/agent_a_out.json + outputs/agent_b_out.json
Writes: outputs/agent_c_out.json  (saves after every record)
"""

import json
import os
import time
from langsmith import traceable
from openai import OpenAI
from langsmith.wrappers import wrap_openai
from dotenv import load_dotenv
load_dotenv()


# ── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY  = os.environ.get("GROQ_API_KEY_C")
LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"]  = "true"
os.environ["LANGSMITH_PROJECT"]  = "GREM"
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = "false"
os.environ["LANGSMITH_ENDPOINT"] = "https://apac.api.smith.langchain.com"
os.environ["LANGSMITH_COMPRESSION"]      = "false"
os.environ["LANGSMITH_BATCH_SIZE"]       = "1"
MODEL         = "llama-3.3-70b-versatile"
MAX_TOKENS    = 120
TEMPERATURE   = 0.0
RATE_LIMIT_S  = 1.0
A_PATH        = "outputs/agent_a_out.json"
B_PATH        = "outputs/agent_b_out.json"
OUTPUT_PATH   = "outputs/agent_c_out.json"
# ─────────────────────────────────────────────────────────────────────────────


def load_system_prompt():
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Groq_Baseline\Context\Context.md", "r") as f:
        context = f.read()
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Groq_Baseline\Context\Agent_C.md", "r") as f:
        agent = f.read()
    return context + "\n\n" + agent


def build_user_prompt(query, entity_summary, chain_summary):
    return f"""Query: {query}

Agent A EntitySummary:
{entity_summary}

Agent B ChainSummary:
{chain_summary}

Do Agent A and Agent B agree on which documents should rank 1 and 2?
Write your ChunkSummary in UNDER 80 TOKENS.
Your LAST LINE must be exactly one of:
relevant: true
relevant: false"""


def parse_relevant_flag(raw_output):
    lines = [l.strip() for l in raw_output.strip().split("\n") if l.strip()]

    relevant = None
    for line in reversed(lines):
        if line.lower() == "relevant: true":
            relevant = True
            break
        elif line.lower() == "relevant: false":
            relevant = False
            break

    if relevant is None:
        print(f"  WARNING: could not parse relevant flag. Defaulting to false.")
        print(f"  Raw output: {raw_output}")
        return raw_output, False

    summary_lines = [
        line for line in lines
        if line.lower() not in ("relevant: true", "relevant: false")
    ]
    return " ".join(summary_lines).strip(), relevant


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


def call_groq(client, system_prompt, query, entity_summary, chain_summary):
    user_prompt = build_user_prompt(query, entity_summary, chain_summary)
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )


@traceable(name="agent_c_record", tags=["agent_c", "groq"])
def process_record(client, system_prompt, a, b):
    resp                    = call_groq(client, system_prompt, a["query"], a["entity_summary"], b["chain_summary"])
    raw_output              = resp.choices[0].message.content.strip()
    tokens_used             = resp.usage.total_tokens
    chunk_summary, relevant = parse_relevant_flag(raw_output)
    return chunk_summary, relevant, tokens_used


def main():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY_C environment variable not set")

    client = wrap_openai(
    OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
        )
    )
    system_prompt = load_system_prompt()

    with open(A_PATH, "r") as f:
        a_index = {r["id"]: r for r in json.load(f)}

    with open(B_PATH, "r") as f:
        b_index = {r["id"]: r for r in json.load(f)}

    common_ids = sorted(set(a_index.keys()) & set(b_index.keys()))
    print(f"[agent_c] Records with both A and B complete: {len(common_ids)}")

    only_a = set(a_index.keys()) - set(b_index.keys())
    only_b = set(b_index.keys()) - set(a_index.keys())
    if only_a: print(f"  WARNING: {len(only_a)} records only in A (missing B)")
    if only_b: print(f"  WARNING: {len(only_b)} records only in B (missing A)")

    results, done_ids = load_checkpoint()

    for i, record_id in enumerate(common_ids):
        if record_id in done_ids:
            continue

        a = a_index[record_id]
        b = b_index[record_id]

        print(f"\n[{i+1}/{len(common_ids)}] {record_id}")
        print(f"  Query        : {a['query'][:90]}")
        print(f"  EntitySummary: {a['entity_summary']}")
        print(f"  ChainSummary : {b['chain_summary']}")

        try:
            chunk_summary, relevant, tokens_used = process_record(client, system_prompt, a, b)

            print(f"  ChunkSummary : {chunk_summary}")
            print(f"  Relevant     : {relevant}")
            print(f"  Tokens used  : {tokens_used}")

            results.append({
                "id":              record_id,
                "query":           a["query"],
                "gold_titles":     a["gold_titles"],
                "top1_wrong":      a["top1_wrong"],
                "first_gold_rank": a["first_gold_rank"],
                "entity_summary":  a["entity_summary"],
                "chain_summary":   b["chain_summary"],
                "chunk_summary":   chunk_summary,
                "relevant":        relevant,
                "tokens_used":     tokens_used,
                "tokens_a":        a["tokens_used"],
                "tokens_b":        b["tokens_used"],
                "model":           MODEL,
                "agent":           "C",
                "timestamp":       time.time(),
            })

            save(results)

        except Exception as e:
            print(f"  ERROR: {e}")
            print(f"  Skipping and continuing...")
            time.sleep(3)
            continue

        time.sleep(RATE_LIMIT_S)

    print(f"\n[agent_c] Done — {len(results)} records saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()