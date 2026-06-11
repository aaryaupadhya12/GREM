# mongo_writer.py
import json
import os
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()

def get_collection():
    client = MongoClient(os.environ.get("MONGO_URI"))
    db     = client["GREM"]
    return db["episodic_memory"]

def write_verified_chains(aggregator_output_path):
    with open(aggregator_output_path, "r") as f:
        records = json.load(f)

    mongo_records = [
        r for r in records
        if r["storage_route"] == "mongodb"
        and not r["parse_error"]
    ]

    if not mongo_records:
        print("No records to write")
        return

    col = get_collection()

    # Avoid duplicates on re-run
    existing_ids = set(
        doc["id"] for doc in col.find({}, {"id": 1})
    )

    new_records = [
        r for r in mongo_records
        if r["id"] not in existing_ids
    ]

    if new_records:
        col.insert_many(new_records)
        print(f"Written {len(new_records)} new records to Atlas")
        print(f"Skipped {len(mongo_records) - len(new_records)} duplicates")
    else:
        print("All records already in Atlas")

if __name__ == "__main__":
    write_verified_chains(r"C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Baseline_Test\Agents\outputs\aggregator_out.json")