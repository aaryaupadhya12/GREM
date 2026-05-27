"""
agent_a.py — Entity Overlap Reasoner

Usage:
    python agent_a.py

Reads:  outputs/subset.json
Writes: outputs/agent_a_out.json  (saves after every record)

Set your API key:
    export GROQ_API_KEY_A="gsk_..."
"""

import json
import os
import time
from groq import Groq

from dotenv import load_dotenv

load_dotenv()


# ── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY  = os.environ.get("GROQ_API_KEY_A")
MODEL         = "llama-3.3-70b-versatile"
MAX_TOKENS    = 80        # slightly over 60 to allow natural sentence completion
TEMPERATURE   = 0.0       # deterministic
RATE_LIMIT_S  = 1.0       # seconds between calls — adjust per account tier
INPUT_PATH    = os.environ.get("INPUT_PATH", "outputs/subset_bridge_full.json")
OUTPUT_PATH   = "outputs/agent_a_out.json"
# ─────────────────────────────────────────────────────────────────────────────



def load_system_prompt():
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Groq_Baseline\Context\Context.md", "r") as f:
        context = f.read()
    with open(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Groq_Baseline\Agents\Agent_A.py", "r") as f:
        agent = f.read()
    return context + "\n\n" + agent


def build_user_prompt(record):
    titles_block = "\n".join([
        f"  Rank {t['rank']} {'[GOLD]' if t['is_gold'] else '      '} "
        f"{t['title']} — {t['first_sentence']}"
        for t in record["titles_and_first_sentence"]
    ])

    bridge = ", ".join(record["bridge_candidates"]) or "None detected"
    answer_only = ", ".join(record["only_answer_has"]) or "None"
    wrong_only  = ", ".join(record["only_wrong_has"]) or "None"

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


def main():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY_A environment variable not set")

    client        = Groq(api_key=GROQ_API_KEY)
    system_prompt = load_system_prompt()

    with open(INPUT_PATH, "r") as f:
        records = json.load(f)
    print(f"[agent_a] Loaded {len(records)} records from {INPUT_PATH}")

    results, done_ids = load_checkpoint()

    for i, record in enumerate(records):
        if record["id"] in done_ids:
            continue

        print(f"\n[{i+1}/{len(records)}] {record['id']}")
        print(f"  Query      : {record['query'][:90]}")
        print(f"  Gold titles: {record['gold_titles']}")
        print(f"  Top-1 wrong: {record['top1_wrong_title']}")

        user_prompt = build_user_prompt(record)

        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )

            entity_summary = resp.choices[0].message.content.strip()
            tokens_used    = resp.usage.total_tokens

            print(f"  EntitySummary ({tokens_used} tok): {entity_summary}")

            results.append({
                "id":             record["id"],
                "query":          record["query"],
                "gold_titles":    record["gold_titles"],
                "top1_wrong":     record["top1_wrong_title"],
                "first_gold_rank":record["first_gold_rank"],
                "entity_summary": entity_summary,
                "tokens_used":    tokens_used,
                "model":          MODEL,
                "agent":          "A",
                "timestamp":      time.time(),
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