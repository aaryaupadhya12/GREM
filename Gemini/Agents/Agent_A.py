"""
agent_a.py — Entity Overlap Reasoner (Vertex AI / Gemini)

Usage:
    python agent_a.py

Reads:  outputs/subset_bridge_*.json
Writes: outputs/agent_a_out.json  (saves after every record)

Auth:
    gcloud auth application-default login  (one time)

.env requires:
    GCP_PROJECT_ID=your-project-id
    GCP_LOCATION=us-central1
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
RATE_LIMIT_S  = 0.3      # Vertex AI has higher rate limits than Groq free tier
TOKEN_REFRESH_EVERY = 50 # refresh bearer token every N records
INPUT_PATH    = os.environ.get("INPUT_PATH", r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Gemini\outputs\2000_final.json")
OUTPUT_PATH   = "outputs/agent_a_out.json"
# ─────────────────────────────────────────────────────────────────────────────


def get_fresh_client():
    """Bearer tokens expire after 1 hour. Refresh periodically."""
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
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Gemini\Context\Agent_A.md", "r") as f:
        agent = f.read()
    return context + "\n\n" + agent


def build_user_prompt(record):
    titles_block = "\n".join([
        f"  Rank {t['rank']} {'[GOLD]' if t['is_gold'] else '      '} "
        f"{t['title']} — {t['first_sentence']}"
        for t in record["titles_and_first_sentence"]
    ])

    bridge      = ", ".join(record["bridge_candidates"]) or "None detected"
    answer_only = ", ".join(record["only_answer_has"])   or "None"
    wrong_only  = ", ".join(record["only_wrong_has"])    or "None"

    return f"""Query: {record["query"]}

Bridge candidates (entities in query): {bridge}
Entities ONLY in gold answer (not in BM25 top-1): {answer_only}
Entities ONLY in BM25 top-1 wrong answer: {wrong_only}

Candidates (title + first sentence):
{titles_block}

Write your EntitySummary in UNDER 60 TOKENS. Name the bridge entity explicitly."""


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


@traceable(name="agent_a_record", run_type="chain", tags=["agent_a", "gemini"])
def process_record(client, system_prompt, record):
    user_prompt    = build_user_prompt(record)
    resp           = call_gemini(client, system_prompt, user_prompt)
    entity_summary = resp.choices[0].message.content.strip()
    tokens_used    = resp.usage.total_tokens
    return entity_summary, tokens_used


def main():
    client        = get_fresh_client()
    system_prompt = load_system_prompt()

    with open(INPUT_PATH, "r") as f:
        records = json.load(f)
    print(f"[agent_a] Loaded {len(records)} records from {INPUT_PATH}")
    print(f"[agent_a] Model: {MODEL}")

    results, done_ids = load_checkpoint()

    for i, record in enumerate(records):
        if record["id"] in done_ids:
            continue

        # Refresh bearer token periodically (expires after 1 hour)
        if i > 0 and i % TOKEN_REFRESH_EVERY == 0:
            client = get_fresh_client()
            print(f"[token] Refreshed at record {i}")

        print(f"\n[{i+1}/{len(records)}] {record['id']}")
        print(f"  Query      : {record['query'][:90]}")
        print(f"  Gold titles: {record['gold_titles']}")
        print(f"  Top-1 wrong: {record['top1_wrong_title']}")

        try:
            entity_summary, tokens_used = process_record(client, system_prompt, record)

            print(f"  EntitySummary ({tokens_used} tok): {entity_summary}")

            results.append({
                "id":              record["id"],
                "query":           record["query"],
                "gold_titles":     record["gold_titles"],
                "top1_wrong":      record["top1_wrong_title"],
                "first_gold_rank": record["first_gold_rank"],
                "entity_summary":  entity_summary,
                "tokens_used":     tokens_used,
                "model":           MODEL,
                "agent":           "A",
                "timestamp":       time.time(),
            })

            save(results)

        except Exception as e:
            print(f"  ERROR: {e}")
            print(f"  Skipping and continuing...")
            time.sleep(3)
            continue

        time.sleep(RATE_LIMIT_S)

    print(f"\n[agent_a] Done — {len(results)} records saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()