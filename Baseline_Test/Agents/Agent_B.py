"""
agent_b.py — Bridge Chain Reasoner

Usage:
    python agent_b.py

Reads:  outputs/subset.json
Writes: outputs/agent_b_out.json  (saves after every record)

Set your API key:
    export GROQ_API_KEY_B="gsk_..."
"""

from openai import OpenAI
import json
import os
import time
from langsmith import traceable
from dotenv import load_dotenv
from langsmith.wrappers import wrap_openai
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY  = os.environ.get("GROQ_API_KEY_B")
LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"]  = "true"
os.environ["LANGSMITH_PROJECT"]  = "GREM"
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = "false"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_COMPRESSION"]      = "false"
os.environ["LANGSMITH_BATCH_SIZE"]       = "1"
MODEL         = "llama-3.3-70b-versatile"
MAX_TOKENS    = 80
TEMPERATURE   = 0.0
RATE_LIMIT_S  = 1.0
INPUT_PATH    = os.environ.get("INPUT_PATH", r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Baseline_Test\outputs\subset_bridge_200.json")
OUTPUT_PATH   = "outputs/agent_b_out.json"
# ─────────────────────────────────────────────────────────────────────────────


def load_system_prompt():
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Baseline_Test\Context\Context.md", "r") as f:
        context = f.read()
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Baseline_Test\Context\Agent_B.md", "r") as f:
        agent = f.read()
    return context + "\n\n" + agent


def build_user_prompt(record):
    titles_block = "\n".join([
        f"  - {t}" for t in record["all_candidate_titles"]
    ])
    bridge = ", ".join(record["bridge_candidates"]) or "None detected"

    return f"""Query: {record["query"]}

Bridge candidates (entities in query): {bridge}

BM25 Top-1 WRONG answer — "{record["top1_wrong_title"]}":
{record["top1_wrong_text"]}

All 10 candidate titles:
{titles_block}

Write your ChainSummary in UNDER 60 TOKENS.
State the two-hop chain and explain why top-1 is wrong."""


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


def call_groq(client, system_prompt, user_prompt):
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )


@traceable(name="agent_b_record", tags=["agent_b", "groq"])
def process_record(client, system_prompt, record):
    user_prompt   = build_user_prompt(record)
    resp          = call_groq(client, system_prompt, user_prompt)
    chain_summary = resp.choices[0].message.content.strip()
    tokens_used   = resp.usage.total_tokens
    return chain_summary, tokens_used


def main():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY_B environment variable not set")

    client = wrap_openai(
    OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
        )
    )
    system_prompt = load_system_prompt()

    with open(INPUT_PATH, "r") as f:
        records = json.load(f)
    print(f"[agent_b] Loaded {len(records)} records from {INPUT_PATH}")

    results, done_ids = load_checkpoint()

    for i, record in enumerate(records):
        if record["id"] in done_ids:
            continue

        print(f"\n[{i+1}/{len(records)}] {record['id']}")
        print(f"  Query      : {record['query'][:90]}")
        print(f"  Gold titles: {record['gold_titles']}")
        print(f"  Top-1 wrong: {record['top1_wrong_title']}")

        try:
            chain_summary, tokens_used = process_record(client, system_prompt, record)

            print(f"  ChainSummary ({tokens_used} tok): {chain_summary}")

            results.append({
                "id":              record["id"],
                "query":           record["query"],
                "gold_titles":     record["gold_titles"],
                "top1_wrong":      record["top1_wrong_title"],
                "first_gold_rank": record["first_gold_rank"],
                "chain_summary":   chain_summary,
                "tokens_used":     tokens_used,
                "model":           MODEL,
                "agent":           "B",
                "timestamp":       time.time(),
            })

            save(results)

        except Exception as e:
            print(f"  ERROR: {e}")
            print(f"  Skipping and continuing...")
            time.sleep(3)
            continue

        time.sleep(RATE_LIMIT_S)

    print(f"\n[agent_b] Done — {len(results)} records saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()