"""
agent_b.py — Bridge Chain Reasoner (Vertex AI / Gemini)

Usage:
    python agent_b.py
"""

import json
import os
import time
import google.auth
import google.auth.transport.requests
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID = os.environ["GCP_PROJECT_ID"]
LOCATION   = os.environ.get("GCP_LOCATION", "us-central1")

LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"]              = "true"
os.environ["LANGSMITH_PROJECT"]              = "GREM"
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = "false"
os.environ["LANGSMITH_ENDPOINT"]             = "https://api.smith.langchain.com"
os.environ["LANGSMITH_COMPRESSION"]          = "false"
os.environ["LANGSMITH_BATCH_SIZE"]           = "1"

MODEL         = "google/gemini-2.5-flash-lite"
MAX_TOKENS    = 80
TEMPERATURE   = 0.0
RATE_LIMIT_S  = 0.3
TOKEN_REFRESH_EVERY = 50
INPUT_PATH    = os.environ.get("INPUT_PATH", r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Gemini\outputs\2000_final.json")
OUTPUT_PATH   = "outputs/agent_b_out.json"
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
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Gemini\Context\Context.md", "r") as f:
        context = f.read()
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Gemini\Context\Agent_B.md", "r") as f:
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


def call_gemini(client, system_prompt, user_prompt):
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )


@traceable(name="agent_b_record", run_type="chain", tags=["agent_b", "gemini"])
def process_record(client, system_prompt, record):
    user_prompt   = build_user_prompt(record)
    resp          = call_gemini(client, system_prompt, user_prompt)
    chain_summary = resp.choices[0].message.content.strip()
    tokens_used   = resp.usage.total_tokens
    return chain_summary, tokens_used


def main():
    client        = get_fresh_client()
    system_prompt = load_system_prompt()

    with open(INPUT_PATH, "r") as f:
        records = json.load(f)
    print(f"[agent_b] Loaded {len(records)} records from {INPUT_PATH}")
    print(f"[agent_b] Model: {MODEL}")

    results, done_ids = load_checkpoint()

    for i, record in enumerate(records):
        if record["id"] in done_ids:
            continue

        if i > 0 and i % TOKEN_REFRESH_EVERY == 0:
            client = get_fresh_client()
            print(f"[token] Refreshed at record {i}")

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