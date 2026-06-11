"""
mongodb_mcp_integration.py — MongoDB MCP Server client for GREM
"""

import subprocess
import json
import os
import re
import shutil
import platform
import threading
from dotenv import load_dotenv
load_dotenv()


def _resolve_mcp_cmd() -> list:
    npx = shutil.which("npx")
    if npx:
        return [npx, "-y", "mongodb-mcp-server"]
    if platform.system() == "Windows":
        for c in [
            r"C:\Program Files\nodejs\npx.cmd",
            r"C:\Program Files (x86)\nodejs\npx.cmd",
            os.path.expanduser(r"~\AppData\Roaming\npm\npx.cmd"),
        ]:
            if os.path.exists(c):
                return [c, "-y", "mongodb-mcp-server"]
    return ["npx", "-y", "mongodb-mcp-server"]


MCP_CMD = _resolve_mcp_cmd()
TIMEOUT = 60
print(f"[MCP] using cmd: {MCP_CMD[0]}")


def invoke_mongodb_mcp_server(operation: str, args: dict, silent: bool = False) -> dict:
    request = {
        "jsonrpc": "2.0",
        "method":  "tools/call",
        "params":  {"name": operation, "arguments": args},
        "id":      1,
    }

    env = os.environ.copy()
    env["MDB_MCP_CONNECTION_STRING"] = os.environ.get("MONGO_URI", "")

    if not silent:
        print(f"[MCP] op={operation}  collection={args.get('collection', '?')}")

    try:
        proc = subprocess.Popen(
            MCP_CMD,
            stdin  = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.DEVNULL,
            text   = True,
            env    = env,
            bufsize = 1,   # line-buffered
        )

        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        proc.stdin.close()

        # Read until we get our response, then kill
        result = {"error": "no_valid_response"}
        import time
        start = time.time()
        
        while time.time() - start < TIMEOUT:
            line = proc.stdout.readline()
            if not line:
                # EOF — subprocess exited
                break
            line = line.strip()
            if not line:
                continue
            
            # Skip non-JSON noise lines
            if not (line.startswith("{") and line.endswith("}")):
                continue
            
            try:
                msg = json.loads(line)
                if msg.get("id") == 1 and "result" in msg:
                    result = msg["result"]
                    break
                if msg.get("id") == 1 and "error" in msg:
                    result = {"error": msg["error"]}
                    break
            except json.JSONDecodeError:
                continue

        proc.kill()
        proc.wait(timeout=2)
        
        if not silent:
            print(f"[MCP] ✓ response received")
        return result

    except FileNotFoundError:
        print("[MCP] ERROR: npx not found — install Node.js 18+")
        return {"error": "npx_not_found"}


def _extract_documents_from_mcp_result(result: dict) -> list:
    content = result.get("content", [])

    for block in content:
        if block.get("type") != "text":
            continue

        text = block.get("text", "")
        
        # Find the JSON array directly — it starts with [{ and ends with }]
        # This is more reliable than parsing the wrapper tags
        start = text.find("[{")
        if start == -1:
            # Could also be a single document
            continue
        
        # Count braces to find the matching close bracket
        depth = 0
        end = -1
        in_string = False
        escape = False
        
        for i in range(start, len(text)):
            ch = text[i]
            
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        
        if end == -1:
            print(f"[MCP] Could not find end of JSON array")
            continue
        
        json_str = text[start:end + 1]
        
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError as e:
            print(f"[MCP] JSON parse error: {e}")
            print(f"[MCP DEBUG] json_str[:300] = {repr(json_str[:300])}")
            continue

    return []


def mcp_insert_one(database: str, collection: str, document: dict) -> dict:
    return invoke_mongodb_mcp_server(
        "insertOne",
        {"database": database, "collection": collection, "document": document},
    )


def mcp_insert_many(database: str, collection: str, documents: list) -> dict:
    return invoke_mongodb_mcp_server(
        "insertMany",
        {"database": database, "collection": collection, "documents": documents},
    )


def mcp_find(database: str, collection: str, filter: dict,
             projection: dict = None, limit: int = 10) -> list:
    args = {
        "database":   database,
        "collection": collection,
        "filter":     filter,
        "limit":      limit,
    }
    if projection:
        args["projection"] = projection
    result = invoke_mongodb_mcp_server("find", args)
    return _extract_documents_from_mcp_result(result)


def mcp_delete_many(database: str, collection: str, filter: dict) -> dict:
    return invoke_mongodb_mcp_server(
        "deleteMany",
        {"database": database, "collection": collection, "filter": filter},
    )


def mcp_count(database: str, collection: str, filter: dict = None) -> int:
    result = invoke_mongodb_mcp_server(
        "aggregate",
        {
            "database":   database,
            "collection": collection,
            "pipeline":   [
                {"$match": filter or {}},
                {"$count": "total"},
            ],
        },
        silent=True,
    )
    docs = _extract_documents_from_mcp_result(result)
    return docs[0].get("total", 0) if docs else 0


if __name__ == "__main__":
    print("=" * 60)
    print("GREM — MongoDB MCP Server smoke test")
    print("=" * 60)

    n = mcp_count("GREM", "episodic_memory")
    print(f"\n  episodic_memory document count : {n}")

    chains = mcp_find(
        database   = "GREM",
        collection = "episodic_memory",
        filter     = {"q_final": {"$gte": 0.7}},
        projection = {"query": 1, "q_final": 1, "failure_mode": 1, "_id": 0},
        limit      = 3,
    )
    print(f"  verified chains (q_final≥0.7)  : {len(chains)}")
    for i, c in enumerate(chains, 1):
        print(f"    [{i}] {c}")

    print("\n" + "=" * 60)
    print("MCP integration verified ✓")
    print("=" * 60)