# test_vector_search.py
import os
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
load_dotenv()

encoder = SentenceTransformer("all-MiniLM-L6-v2")
col = MongoClient(os.environ["MONGO_URI"])["GREM"]["episodic_memory"]

query = "Which indian actress acted in Kabhi kishi khabi gam?"
q_emb = encoder.encode(query, normalize_embeddings=True).tolist()

results = list(col.aggregate([{
    "$vectorSearch": {
        "index":         "episodic_embedding_index",
        "path":          "query_embedding",
        "queryVector":   q_emb,
        "numCandidates": 50,
        "limit":         3,
    }
}]))

print(f"Found {len(results)} similar queries:")
for r in results:
    print(f"  - {r.get('query', 'no query field')[:80]}")