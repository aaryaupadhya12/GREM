"""
mongo_writer.py — Write verified reasoning chains to Atlas via MCP

Uses MongoDB MCP Server for:
  - checking existing IDs (find)
  - inserting new records (insertMany)

PyMongo is NOT used here — all Atlas operations go through MCP.
"""

import json
import os
from dotenv import load_dotenv
load_dotenv()

from Mongodb_mcp_integration import mcp_find, mcp_insert_many, mcp_count

DB         = "GREM"
COLLECTION = "episodic_memeory"


def write_verified_chains(aggregator_output_path: str):
    """
    Read aggregator_out.json, filter to storage_route=mongodb records,
    deduplicate against Atlas, insert new ones via MCP.
    """

    with open(aggregator_output_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Filter: only records routed to MongoDB and cleanly parsed
    mongo_records = [
        r for r in records
        if r.get("storage_route") == "mongodb" and not r.get("parse_error")
    ]

    if not mongo_records:
        print("[writer] No records to write")
        return

    print(f"[writer] {len(mongo_records)} candidates from aggregator")

    # ── Duplicate check via MCP ─────────────────────────────────
    # Pull all existing IDs through MCP find
    existing_docs = mcp_find(
        database   = DB,
        collection = COLLECTION,
        filter     = {},
        projection = {"id": 1, "_id": 0},
        limit      = 100_000,   # effectively unbounded
    )
    existing_ids = {doc["id"] for doc in existing_docs if "id" in doc}
    print(f"[writer] {len(existing_ids)} existing IDs in Atlas (via MCP)")

    new_records = [r for r in mongo_records if r["id"] not in existing_ids]
    skipped     = len(mongo_records) - len(new_records)

    if not new_records:
        print(f"[writer] All {skipped} records already in Atlas — nothing to insert")
        return

    # ── Insert via MCP ──────────────────────────────────────────
    print(f"[writer] Inserting {len(new_records)} new records via MCP...")
    result = mcp_insert_many(DB, COLLECTION, new_records)

    if "error" not in result:
        import time 
        time.sleep(2)
        n_after = mcp_count(DB, COLLECTION)
        print(f"[writer] ✓ Insert complete")
        print(f"[writer]   inserted : {len(new_records)}")
        print(f"[writer]   skipped  : {skipped} duplicates")
        print(f"[writer]   total    : {n_after} docs in {DB}.{COLLECTION}")
    else:
        print(f"[writer] ✗ MCP insert failed: {result['error']}")
        print(f"[writer]   falling back to PyMongo...")
        _pymongo_fallback(new_records)


def _pymongo_fallback(records: list):
    """Last-resort direct insert if MCP fails."""
    from pymongo import MongoClient
    col = MongoClient(os.environ["MONGO_URI"])[DB][COLLECTION]
    col.insert_many(records)
    print(f"[writer] PyMongo fallback: inserted {len(records)} records")


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else (
        r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L"
        r"\GREM\Gemini\Agents\outputs\aggregator_out.json"
    )
    write_verified_chains(path)