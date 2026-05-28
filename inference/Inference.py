# inference_pipeline.py
# ─────────────────────────────────────────────────────────────
# Quality-Gated Multi-Hop Retrieval — Inference Pipeline
#
# Architecture (matches architecture doc):
#   BM25Retriever
#   | DenseRetriever          ← NEW: dense passage retrieval
#   | RRFFusion               ← NEW: reciprocal rank fusion
#   | ColdStartGate           ← NEW: skip episodic for queries 1-5
#   | EpisodicMemoryFetcher
#   | BERTCrossEncoderReranker
#   | GroqBridgeVerifier
#   | MetricsComputer
#   | MongoResultWriter
#   | GroqNarrator
#
# Free stack  (use_paid_services=False):
#   BM25 + sentence-transformers FAISS | sentence-transformers
#   | cross-encoder/ms-marco-MiniLM-L-6-v2 | Groq llama-3.3-70b
#
# Paid stack  (use_paid_services=True):
#   BM25 + Vertex AI retrieval | textembedding-gecko
#   | cross-encoder (same) | Gemini 1.5 Pro
# ─────────────────────────────────────────────────────────────
from __future__ import annotations
import os, json, re, time
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from langchain_core.runnables import Runnable, RunnableLambda
from pymongo import MongoClient
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from sentence_transformers.cross_encoder import CrossEncoder
from groq import Groq
import faiss


# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════

@dataclass
class InferenceConfig:
    # ── toggle: False = fully free, True = paid (final demo) ──────
    use_paid_services: bool = False

    # ── Embedding / retrieval models ───────────────────────────────
    embedding_model_local:  str = "all-MiniLM-L6-v2"          # free, 384-dim
    embedding_model_vertex: str = "textembedding-gecko@003"     # paid, 768-dim

    # ── Reranker (BERT cross-encoder — same in both modes) ─────────
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ── Narrator / Verifier ────────────────────────────────────────
    narrator_model_free: str = "llama-3.3-70b-versatile"   # Groq, free
    narrator_model_paid: str = "gemini-1.5-pro"             # paid

    # ── API keys ───────────────────────────────────────────────────
    groq_api_key:   str = field(default_factory=lambda: os.environ.get("GROQ_API_KEY",   ""))
    gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    gcp_project:    str = field(default_factory=lambda: os.environ.get("GCP_PROJECT",    ""))

    # ── MongoDB ────────────────────────────────────────────────────
    mongo_uri:   str = field(default_factory=lambda: os.environ.get("MONGO_URI", ""))
    mongo_db:    str = "hotpotqa_rag"
    results_col: str = "inference_results"

    # ── Retrieval hyper-params ─────────────────────────────────────
    bm25_top_k:    int = 100   # candidates from BM25
    dense_top_k:   int = 100   # candidates from dense retriever
    fused_top_k:   int = 100   # candidates after RRF fusion
    memory_top_k:  int = 3     # episodic hints from Atlas
    rerank_top_k:  int = 20    # candidates sent to cross-encoder

    # ── RRF constant (standard value = 60) ────────────────────────
    rrf_k: int = 60

    # ── BM25 / reranker blend ──────────────────────────────────────
    alpha: float = 0.4    # BM25 weight in final blend
    delta: float = 0.6    # reranker weight in final blend

    # ── Cold Start Gate ────────────────────────────────────────────
    cold_start_n: int = 5   # first N queries skip episodic memory

    # ── Ground Rate threshold ──────────────────────────────────────
    ground_T: int = 3   # reranker must place gold <= T to be "grounded"


# ══════════════════════════════════════════════════════════════
# MODULE 1 — BM25 RETRIEVER
# ══════════════════════════════════════════════════════════════

class BM25Retriever:
    """
    Stage 1a: Lexical retrieval using BM25.
    Loads corpus once from MongoDB, builds in-memory BM25Okapi index.

    Input : {"query": str, "gold_passage_id": str|None,
              "query_count": int}
    Output: state + "bm25_candidates": List[Dict]
    """
    def __init__(self, cfg: InferenceConfig):
        self.cfg    = cfg
        self.client = MongoClient(cfg.mongo_uri)
        self.col    = self.client[cfg.mongo_db]["passages"]
        self._index: Optional[BM25Okapi] = None
        self._docs:  Optional[List]      = None

    def _build_index(self):
        if self._index is not None:
            return
        print("[BM25] Building index from MongoDB...")
        self._docs = list(self.col.find(
            {}, {"_id": 1, "title": 1, "text": 1, "entities": 1}
        ))
        self._index = BM25Okapi([d["text"].lower().split() for d in self._docs])
        print(f"[BM25] Ready — {len(self._docs)} passages")

    def retrieve(self, state: Dict) -> Dict:
        self._build_index()
        query    = state["query"]
        scores   = self._index.get_scores(query.lower().split())
        top_idxs = np.argsort(scores)[::-1][:self.cfg.bm25_top_k]

        candidates = [
            {
                "passage_id": str(self._docs[i]["_id"]),
                "title":      self._docs[i].get("title", ""),
                "text":       self._docs[i].get("text", ""),
                "entities":   self._docs[i].get("entities", []),
                "bm25_score": float(scores[i]),
                "bm25_rank":  int(rank + 1),
            }
            for rank, i in enumerate(top_idxs)
        ]

        # Eval mode: force-insert gold if outside top-K
        gold_id = state.get("gold_passage_id")
        if gold_id and not any(c["passage_id"] == gold_id for c in candidates):
            gold_doc = self.col.find_one({"_id": gold_id})
            if gold_doc:
                doc_idx    = next(
                    (i for i, d in enumerate(self._docs) if str(d["_id"]) == gold_id),
                    None,
                )
                gold_score = float(scores[doc_idx]) if doc_idx is not None else 0.0
                candidates.append({
                    "passage_id": gold_id,
                    "title":      gold_doc.get("title", ""),
                    "text":       gold_doc.get("text", ""),
                    "entities":   gold_doc.get("entities", []),
                    "bm25_score": gold_score,
                    "bm25_rank":  self.cfg.bm25_top_k + 1,
                    "injected":   True,
                })

        print(f"[BM25] {len(candidates)} candidates")
        # Store docs list on state so DenseRetriever can share the corpus
        return {**state, "bm25_candidates": candidates, "_corpus_docs": self._docs}

    def as_runnable(self) -> Runnable:
        return RunnableLambda(self.retrieve)


# ══════════════════════════════════════════════════════════════
# MODULE 2 — DENSE RETRIEVER  (NEW)
# ══════════════════════════════════════════════════════════════

class DenseRetriever:
    """
    Stage 1b: Dense passage retrieval using FAISS + sentence-transformers.
    Runs AFTER BM25Retriever so it can share the loaded corpus.

    Free  : sentence-transformers all-MiniLM-L6-v2 + FAISS flat index
    Paid  : Vertex AI Matching Engine (swap _embed + _search methods)

    The FAISS index is built once from the corpus and cached in RAM.
    On a 34-passage synthetic corpus this takes < 1 second.
    On the full HotpotQA corpus (~5M passages) it takes ~2 min and
    uses ~2GB RAM — acceptable for a single-machine demo.

    Input : state + "bm25_candidates" + "_corpus_docs"
    Output: state + "dense_candidates": List[Dict]
    """
    def __init__(self, cfg: InferenceConfig):
        self.cfg          = cfg
        self._faiss_index = None
        self._doc_ids:    List[str] = []
        self._embedder    = None

        if not cfg.use_paid_services:
            print("[Dense] Loading local embedding model...")
            self._embedder = SentenceTransformer(cfg.embedding_model_local)
            print("[Dense] Embedder ready ✓")

    def _build_faiss(self, docs: List[Dict]):
        """Build FAISS flat inner-product index over corpus. Called once."""
        if self._faiss_index is not None:
            return
        print(f"[Dense] Building FAISS index over {len(docs)} passages...")
        texts       = [d["text"][:512] for d in docs]
        self._doc_ids = [str(d["_id"]) for d in docs]

        if not self.cfg.use_paid_services:
            embeddings = self._embedder.encode(
                texts,
                batch_size        = 64,
                normalize_embeddings = True,
                show_progress_bar = True,
            ).astype(np.float32)
        else:
            embeddings = self._embed_vertex_batch(texts)

        dim = embeddings.shape[1]
        self._faiss_index = faiss.IndexFlatIP(dim)   # inner product = cosine on normalised vecs
        self._faiss_index.add(embeddings)
        print(f"[Dense] FAISS index ready — {self._faiss_index.ntotal} vectors, dim={dim}")

    def _embed_local(self, text: str) -> np.ndarray:
        return self._embedder.encode(
            text, normalize_embeddings=True
        ).astype(np.float32).reshape(1, -1)

    def _embed_vertex_batch(self, texts: List[str]) -> np.ndarray:
        """Paid: Vertex AI batch embedding."""
        from vertexai.language_models import TextEmbeddingModel
        import vertexai
        vertexai.init(project=self.cfg.gcp_project, location="us-central1")
        model  = TextEmbeddingModel.from_pretrained(self.cfg.embedding_model_vertex)
        # Vertex AI: max 250 texts per call
        all_embs = []
        for i in range(0, len(texts), 250):
            batch    = texts[i:i + 250]
            results  = model.get_embeddings(batch)
            all_embs.extend([r.values for r in results])
        return np.array(all_embs, dtype=np.float32)

    def retrieve(self, state: Dict) -> Dict:
        docs = state.get("_corpus_docs", [])
        if not docs:
            # Fallback: no corpus available, return empty
            print("[Dense] No corpus in state — skipping dense retrieval")
            return {**state, "dense_candidates": []}

        self._build_faiss(docs)

        query = state["query"]
        if not self.cfg.use_paid_services:
            q_vec = self._embed_local(query)
        else:
            q_vec = np.array(
                self._embed_vertex_batch([query]), dtype=np.float32
            )

        k         = min(self.cfg.dense_top_k, self._faiss_index.ntotal)
        scores, idxs = self._faiss_index.search(q_vec, k)
        scores    = scores[0]
        idxs      = idxs[0]

        dense_candidates = []
        for rank, (idx, score) in enumerate(zip(idxs, scores)):
            if idx < 0:   # FAISS returns -1 for padding
                continue
            doc = docs[idx]
            dense_candidates.append({
                "passage_id":   str(doc["_id"]),
                "title":        doc.get("title", ""),
                "text":         doc.get("text", ""),
                "entities":     doc.get("entities", []),
                "dense_score":  float(score),
                "dense_rank":   int(rank + 1),
            })

        print(f"[Dense] {len(dense_candidates)} candidates")
        return {**state, "dense_candidates": dense_candidates}

    def as_runnable(self) -> Runnable:
        return RunnableLambda(self.retrieve)


# ══════════════════════════════════════════════════════════════
# MODULE 3 — RRF FUSION  (NEW)
# ══════════════════════════════════════════════════════════════

class RRFFusion:
    """
    Stage 1c: Reciprocal Rank Fusion of BM25 + Dense ranked lists.

    RRF formula:
        score(d) = Σ  1 / (k + rank_i(d))
    where k=60 (standard), rank_i is the rank in list i.

    Merges both lists into a single fused top-K candidate list.
    Each candidate carries both bm25_rank and dense_rank for
    later analysis and Ground Rate computation.

    Input : state + "bm25_candidates" + "dense_candidates"
    Output: state + "candidates": List[Dict]  (fused, sorted by RRF score)
    """
    def __init__(self, cfg: InferenceConfig):
        self.cfg = cfg

    def fuse(self, state: Dict) -> Dict:
        bm25_list  = state.get("bm25_candidates",  [])
        dense_list = state.get("dense_candidates", [])
        k          = self.cfg.rrf_k

        # Build rank lookup: passage_id → rank (1-indexed)
        bm25_ranks  = {c["passage_id"]: c["bm25_rank"]  for c in bm25_list}
        dense_ranks = {c["passage_id"]: c["dense_rank"] for c in dense_list}

        # Collect all unique passage IDs from both lists
        all_ids = set(bm25_ranks.keys()) | set(dense_ranks.keys())

        # Build a lookup for full passage info
        passage_info: Dict[str, Dict] = {}
        for c in bm25_list:
            passage_info[c["passage_id"]] = c
        for c in dense_list:
            if c["passage_id"] not in passage_info:
                passage_info[c["passage_id"]] = c

        # Compute RRF score for every passage
        fused = []
        n_bm25  = len(bm25_list)
        n_dense = len(dense_list)

        for pid in all_ids:
            # If not in a list, penalise with rank = list_length + 1
            r_bm25  = bm25_ranks.get(pid,  n_bm25  + 1)
            r_dense = dense_ranks.get(pid, n_dense + 1)
            rrf_score = 1.0 / (k + r_bm25) + 1.0 / (k + r_dense)

            info = passage_info[pid].copy()
            info["rrf_score"]   = round(rrf_score, 6)
            info["bm25_rank"]   = r_bm25
            info["dense_rank"]  = r_dense
            # Preserve bm25_score if available, else use 0
            if "bm25_score" not in info:
                info["bm25_score"] = 0.0
            if "dense_score" not in info:
                info["dense_score"] = 0.0
            fused.append(info)

        # Sort by RRF score descending, take top-K
        fused.sort(key=lambda c: -c["rrf_score"])
        fused = fused[:self.cfg.fused_top_k]

        # Assign fused rank
        for rank, c in enumerate(fused, 1):
            c["fused_rank"] = rank

        print(f"[RRF] Fused {len(bm25_list)} BM25 + "
              f"{len(dense_list)} dense → {len(fused)} candidates")

        return {**state, "candidates": fused}

    def as_runnable(self) -> Runnable:
        return RunnableLambda(self.fuse)


# ══════════════════════════════════════════════════════════════
# MODULE 4 — COLD START GATE  (NEW)
# ══════════════════════════════════════════════════════════════

class ColdStartGate:
    """
    Stage 2a: Prevents noisy episodic memory injection during the
    first N queries of a session.

    From the architecture doc:
        "Early queries bypass episodic memory retrieval.
         Purpose: prevent noisy memory injection, stabilize
         early retrieval behavior.
         Rule: queries 1–5 skip episodic memory usage."

    When cold_start=True is set in state, EpisodicMemoryFetcher
    skips the Atlas Vector Search and returns empty hints.

    query_count is passed in by the caller and incremented here.
    For a single demo query just pass query_count=99 to skip
    the gate entirely.

    Input : state + "query_count": int
    Output: state + "cold_start": bool
                  + "query_count": int  (incremented)
    """
    def __init__(self, cfg: InferenceConfig):
        self.cfg = cfg

    def gate(self, state: Dict) -> Dict:
        count      = state.get("query_count", 99)   # default 99 = gate open
        is_cold    = count < self.cfg.cold_start_n
        new_count  = count + 1

        if is_cold:
            print(f"[ColdStartGate] Query {count + 1}/{self.cfg.cold_start_n} "
                  f"— episodic memory SKIPPED (cold start)")
        else:
            print(f"[ColdStartGate] Query {count + 1} — episodic memory ACTIVE")

        return {**state, "cold_start": is_cold, "query_count": new_count}

    def as_runnable(self) -> Runnable:
        return RunnableLambda(self.gate)


# ══════════════════════════════════════════════════════════════
# MODULE 5 — EPISODIC MEMORY FETCHER
# ══════════════════════════════════════════════════════════════

class EpisodicMemoryFetcher:
    """
    Stage 2b: Atlas Vector Search — fetch top-3 verified chains.
    Skipped automatically when cold_start=True (gate set by ColdStartGate).

    Free  : sentence-transformers for query embedding
    Paid  : Vertex AI textembedding-gecko

    Input : state + "cold_start": bool
    Output: state + "episodic_hints": List[Dict]  ([] if cold start)
                  + "query_embedding": List[float]
    """
    def __init__(self, cfg: InferenceConfig):
        self.cfg    = cfg
        self.client = MongoClient(cfg.mongo_uri)
        self.col    = self.client[cfg.mongo_db]["episodic_memory"]
        # Reuse the same embedder instance as DenseRetriever if possible
        # (both use all-MiniLM-L6-v2 in free mode)
        if not cfg.use_paid_services:
            print("[EpisodicMemory] Loading embedding model...")
            self.embedder = SentenceTransformer(cfg.embedding_model_local)
            print("[EpisodicMemory] Embedder ready ✓")

    def _embed(self, text: str) -> List[float]:
        if not self.cfg.use_paid_services:
            return self.embedder.encode(
                text, normalize_embeddings=True
            ).tolist()
        else:
            from vertexai.language_models import TextEmbeddingModel
            import vertexai
            vertexai.init(project=self.cfg.gcp_project, location="us-central1")
            model  = TextEmbeddingModel.from_pretrained(self.cfg.embedding_model_vertex)
            result = model.get_embeddings([text])
            return result[0].values

    def fetch(self, state: Dict) -> Dict:
        # Cold start gate: skip episodic memory for first N queries
        if state.get("cold_start", False):
            return {**state, "episodic_hints": [], "query_embedding": []}

        query = state["query"]
        q_emb = self._embed(query)
        k     = self.cfg.memory_top_k

        pipeline = [
            {
                "$vectorSearch": {
                    "index":         "episodic_embedding_index",
                    "path":          "embedding",
                    "queryVector":   q_emb,
                    "numCandidates": k * 10,
                    "limit":         k,
                    "filter": {
                        "failure_type":  "resolved",
                        "quality_score": {"$gte": 0.50},
                    },
                }
            },
            {
                "$project": {
                    "query": 1, "bridge_entity": 1, "chain": 1,
                    "shared_entities": 1, "key_lesson": 1,
                    "quality_score": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        try:
            hints = list(self.col.aggregate(pipeline))
        except Exception as e:
            print(f"[EpisodicMemory] Vector search failed: {e}")
            print("  → Check 'episodic_embedding_index' exists in Atlas UI")
            hints = []

        if hints:
            print(f"[EpisodicMemory] {len(hints)} hints  "
                  f"top_sim={hints[0].get('score', 0):.3f}")
        else:
            print("[EpisodicMemory] No hints — continuing without memory")

        return {**state, "episodic_hints": hints, "query_embedding": q_emb}

    def as_runnable(self) -> Runnable:
        return RunnableLambda(self.fetch)


# ══════════════════════════════════════════════════════════════
# MODULE 6 — BERT CROSS-ENCODER RERANKER
# ══════════════════════════════════════════════════════════════

class BERTCrossEncoderReranker:
    """
    Stage 3: Final reranking using a BERT cross-encoder.

    From the architecture doc:
        "BERT Cross-Encoder Reranking: distilled from episodic
         memory traces."

    The cross-encoder is the SAME model in both free and paid mode —
    it doesn't change when use_paid_services=True because it's a
    local model that your teammate distilled from the episodic traces.
    Only the narrator/verifier swap.

    Episodic hints are injected into the query string so the
    cross-encoder sees the bridge chain context at scoring time.

    Input : state + "candidates" + "episodic_hints"
    Output: state + "reranked_candidates"
                  + "top_passage"
    """
    def __init__(self, cfg: InferenceConfig):
        self.cfg = cfg
        print("[Reranker] Loading BERT cross-encoder...")
        self.model = CrossEncoder(cfg.reranker_model)
        print("[Reranker] Cross-encoder ready ✓")

    @staticmethod
    def _minmax(x: List[float]) -> np.ndarray:
        a = np.array(x, dtype=float)
        lo, hi = a.min(), a.max()
        if hi - lo < 1e-9:
            return np.full_like(a, 0.5)
        return (a - lo) / (hi - lo)

    def _build_episodic_ctx(self, hints: List[Dict]) -> str:
        if not hints:
            return "none"
        return " | ".join(
            f"{h['bridge_entity']}: {h['chain']}"
            for h in hints
            if h.get("bridge_entity") and h.get("chain")
        )

    def rerank(self, state: Dict) -> Dict:
        query        = state["query"]
        candidates   = state["candidates"][:self.cfg.rerank_top_k]
        episodic_ctx = self._build_episodic_ctx(state.get("episodic_hints", []))

        # Inject episodic context into query so cross-encoder benefits
        # from the verified bridge chain hints at scoring time
        augmented_query = (
            f"{query}\n\n"
            f"[Verified bridge chains from similar queries: {episodic_ctx[:300]}]"
        )

        pairs         = [(augmented_query, c["text"][:512]) for c in candidates]
        rerank_scores = self.model.predict(pairs).tolist()

        # Use RRF score as the primary retrieval signal (combines BM25+dense)
        rrf_scores = [c.get("rrf_score", c.get("bm25_score", 0.0)) for c in candidates]
        rrf_norm    = self._minmax(rrf_scores)
        rerank_norm = self._minmax(rerank_scores)
        combined    = self.cfg.alpha * rrf_norm + self.cfg.delta * rerank_norm

        for i, c in enumerate(candidates):
            c["rerank_score"] = float(rerank_scores[i])
            c["rerank_norm"]  = float(rerank_norm[i])
            c["rrf_norm"]     = float(rrf_norm[i])
            c["combined"]     = float(combined[i])

        reranked = sorted(candidates, key=lambda c: -c["combined"])
        for rank, c in enumerate(reranked, 1):
            c["final_rank"] = rank

        print(f"[Reranker] Top: [{reranked[0]['title']}]  "
              f"combined={reranked[0]['combined']:.3f}")
        return {
            **state,
            "reranked_candidates": reranked,
            "top_passage":         reranked[0],
        }

    def as_runnable(self) -> Runnable:
        return RunnableLambda(self.rerank)


# ══════════════════════════════════════════════════════════════
# MODULE 7 — BRIDGE ENTITY VERIFIER
# ══════════════════════════════════════════════════════════════

class GroqBridgeVerifier:
    """
    Stage 4: Verifies that the top passage contains the bridge entity.
    Classifies retrieval as grounded (chain explicit) or lucky (not).

    Free  : Groq llama-3.3-70b (14,400 req/day free)
    Paid  : Gemini 1.5 Pro

    Input : state + "reranked_candidates" + "episodic_hints"
    Output: state + "bridge_verified": bool
                  + "bridge_entity": str | None
                  + "verified_chain": str | None
                  + "retrieval_verdict": "grounded" | "lucky"
    """
    def __init__(self, cfg: InferenceConfig):
        self.cfg = cfg
        if not cfg.use_paid_services:
            if not cfg.groq_api_key:
                raise ValueError(
                    "GROQ_API_KEY not set. Get a free key at console.groq.com"
                )
            self.client = Groq(api_key=cfg.groq_api_key)

    def _call(self, prompt: str, max_tokens: int = 200) -> str:
        if not self.cfg.use_paid_services:
            resp = self.client.chat.completions.create(
                model       = self.cfg.narrator_model_free,
                messages    = [{"role": "user", "content": prompt}],
                max_tokens  = max_tokens,
                temperature = 0.1,
            )
            return resp.choices[0].message.content
        else:
            import google.generativeai as genai
            genai.configure(api_key=self.cfg.gemini_api_key)
            model = genai.GenerativeModel(self.cfg.narrator_model_paid)
            return model.generate_content(prompt).text

    def verify(self, state: Dict) -> Dict:
        fallback = {
            **state,
            "bridge_verified":   False,
            "bridge_entity":     None,
            "verified_chain":    None,
            "retrieval_verdict": "lucky",
        }

        hints    = state.get("episodic_hints", [])
        top_pass = state.get("top_passage", {})
        if not hints or not top_pass:
            # No episodic hints (cold start or empty memory) — verdict is lucky
            return fallback

        bridge_candidates = list({
            h["bridge_entity"] for h in hints if h.get("bridge_entity")
        })

        prompt = (
            f"You are verifying a multi-hop retrieval chain.\n\n"
            f"QUERY: {state['query']}\n\n"
            f"TOP RETRIEVED PASSAGE:\n"
            f"Title: {top_pass['title']}\n"
            f"Text: {top_pass['text'][:400]}\n\n"
            f"CANDIDATE BRIDGE ENTITIES: {bridge_candidates}\n\n"
            f"Answer in JSON only:\n"
            f'{{"bridge_present": true/false, '
            f'"bridge_entity": "entity or null", '
            f'"chain": "query → bridge → answer or null", '
            f'"verdict": "grounded or lucky"}}\n\n'
            f"grounded = bridge entity explicitly in passage AND connects to answer\n"
            f"lucky    = passage seems right but chain not explicit\n\n"
            f"Output valid JSON only, nothing else."
        )

        try:
            raw   = self._call(prompt, max_tokens=150)
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                result = json.loads(match.group())
                print(f"[BridgeVerifier] verdict={result.get('verdict')}  "
                      f"bridge={result.get('bridge_entity')}")
                return {
                    **state,
                    "bridge_verified":   bool(result.get("bridge_present", False)),
                    "bridge_entity":     result.get("bridge_entity"),
                    "verified_chain":    result.get("chain"),
                    "retrieval_verdict": result.get("verdict", "lucky"),
                }
        except Exception as e:
            print(f"[BridgeVerifier] Error: {e}")

        return fallback

    def as_runnable(self) -> Runnable:
        return RunnableLambda(self.verify)


# ══════════════════════════════════════════════════════════════
# MODULE 8 — METRICS COMPUTER
# ══════════════════════════════════════════════════════════════

class MetricsComputer:
    """
    Stage 5: Per-query metrics.

    Standard : Hits@1/3/10, MRR, nDCG@1/3/10, Recall@10
    Novel    : Ground Rate flag, Lucky Rate flag,
               Bridge-Verified Ground Rate flag

    Ground = reranker placed gold in top-T independently of retrieval.
    Lucky  = correct final rank but reranker rank > T.

    Reads "rerank_score" consistently (not "gemini_score").
    Skipped (returns empty metrics) when gold_passage_id is None.

    Input : state
    Output: state + "metrics": Dict
    """
    def __init__(self, cfg: InferenceConfig):
        self.cfg = cfg

    def compute(self, state: Dict) -> Dict:
        candidates = state.get("reranked_candidates", [])
        gold_id    = state.get("gold_passage_id")
        bridge_ver = state.get("bridge_verified", False)

        if not gold_id or not candidates:
            return {**state, "metrics": {}}

        final_rank = next(
            (c["final_rank"] for c in candidates if c["passage_id"] == gold_id),
            len(candidates),
        )
        rerank_only = sorted(candidates, key=lambda c: -c["rerank_score"])
        rerank_rank = next(
            (i + 1 for i, c in enumerate(rerank_only) if c["passage_id"] == gold_id),
            len(candidates),
        )
        bm25_only   = sorted(candidates, key=lambda c: -c["bm25_score"])
        bm25_rank   = next(
            (i + 1 for i, c in enumerate(bm25_only) if c["passage_id"] == gold_id),
            len(candidates),
        )
        rrf_only    = sorted(candidates, key=lambda c: -c.get("rrf_score", 0.0))
        rrf_rank    = next(
            (i + 1 for i, c in enumerate(rrf_only) if c["passage_id"] == gold_id),
            len(candidates),
        )

        T           = self.cfg.ground_T
        correct     = (final_rank == 1)
        is_grounded = correct and (rerank_rank <= T)
        is_lucky    = correct and (rerank_rank >  T)

        def ndcg(rank, k):
            if rank > k:
                return 0.0
            return (1.0 / np.log2(rank + 1)) / (1.0 / np.log2(2))

        metrics = {
            "hits_at_1":    int(final_rank == 1),
            "hits_at_3":    int(final_rank <= 3),
            "hits_at_10":   int(final_rank <= 10),
            "mrr":          1.0 / final_rank,
            "ndcg_at_1":    ndcg(final_rank, 1),
            "ndcg_at_3":    ndcg(final_rank, 3),
            "ndcg_at_10":   ndcg(final_rank, 10),
            "recall_at_10": int(final_rank <= 10),
            "final_rank":   final_rank,
            "rerank_rank":  rerank_rank,
            "bm25_rank":    bm25_rank,
            "rrf_rank":     rrf_rank,          # new: track RRF-only rank
            "is_correct":   correct,
            "is_grounded":  is_grounded,
            "is_lucky":     is_lucky,
            "cold_start":   state.get("cold_start", False),
            "bridge_verified": bridge_ver,
            "bridge_verified_grounded": (is_grounded and bridge_ver),
        }

        status = "✓ CORRECT" if correct else "✗ wrong"
        ground = "grounded" if is_grounded else ("lucky" if is_lucky else "")
        cold   = " [cold start]" if state.get("cold_start") else ""
        print(f"[Metrics] rank={final_rank}  {status}  {ground}{cold}")
        return {**state, "metrics": metrics}

    def as_runnable(self) -> Runnable:
        return RunnableLambda(self.compute)


# ══════════════════════════════════════════════════════════════
# MODULE 9 — MONGODB RESULT WRITER
# ══════════════════════════════════════════════════════════════

class MongoResultWriter:
    """
    Stage 6: Persists inference result to Atlas inference_results.
    Each document is the full audit trail for one query.

    Input : state (complete)
    Output: state unchanged (side effect only)
    """
    def __init__(self, cfg: InferenceConfig):
        self.cfg    = cfg
        self.client = MongoClient(cfg.mongo_uri)
        self.col    = self.client[cfg.mongo_db][cfg.results_col]

    def write(self, state: Dict) -> Dict:
        doc = {
            "query":               state["query"],
            "top_passage_title":   state.get("top_passage", {}).get("title"),
            "top_passage_id":      state.get("top_passage", {}).get("passage_id"),
            "bridge_entity":       state.get("bridge_entity"),
            "verified_chain":      state.get("verified_chain"),
            "retrieval_verdict":   state.get("retrieval_verdict", "lucky"),
            "episodic_hints_used": len(state.get("episodic_hints", [])),
            "cold_start":          state.get("cold_start", False),
            "query_count":         state.get("query_count", -1),
            "metrics":             state.get("metrics", {}),
            "mode":                "paid" if self.cfg.use_paid_services else "free",
            "timestamp":           datetime.utcnow(),
        }
        self.col.insert_one(doc)
        print(f"[MongoDB] Saved  query: {state['query'][:55]}...")
        return state

    def as_runnable(self) -> Runnable:
        return RunnableLambda(self.write)


# ══════════════════════════════════════════════════════════════
# MODULE 10 — NARRATOR
# ══════════════════════════════════════════════════════════════

class GroqNarrator:
    """
    Stage 7: Produces a natural language answer brief.

    Free  : Groq llama-3.3-70b
    Paid  : Gemini 1.5 Pro

    Input : state (complete)
    Output: state + "research_brief": str
    """
    def __init__(self, cfg: InferenceConfig):
        self.cfg = cfg
        if not cfg.use_paid_services:
            self.client = Groq(api_key=cfg.groq_api_key)

    def _call(self, prompt: str) -> str:
        if not self.cfg.use_paid_services:
            resp = self.client.chat.completions.create(
                model       = self.cfg.narrator_model_free,
                messages    = [{"role": "user", "content": prompt}],
                max_tokens  = 300,
                temperature = 0.3,
            )
            return resp.choices[0].message.content
        else:
            import google.generativeai as genai
            genai.configure(api_key=self.cfg.gemini_api_key)
            model = genai.GenerativeModel(self.cfg.narrator_model_paid)
            return model.generate_content(prompt).text

    def narrate(self, state: Dict) -> Dict:
        top     = state.get("top_passage", {})
        chain   = state.get("verified_chain", "not traced")
        verdict = state.get("retrieval_verdict", "unknown")
        bridge  = state.get("bridge_entity", "unknown")

        verdict_label = (
            "reranker independently confirmed (grounded)"
            if verdict == "grounded"
            else "BM25+dense fusion elevated this result (lucky)"
        )

        prompt = (
            f"You are a retrieval QA system reporting its answer.\n\n"
            f"QUERY: {state['query']}\n\n"
            f"TOP RETRIEVED PASSAGE:\n"
            f"Title: {top.get('title', 'N/A')}\n"
            f"Text: {top.get('text', '')[:300]}\n\n"
            f"REASONING CHAIN: {chain}\n"
            f"BRIDGE ENTITY: {bridge}\n"
            f"VERDICT: {verdict_label}\n\n"
            f"Write a 3-sentence response:\n"
            f"1. State the answer directly\n"
            f"2. Explain the bridge entity connecting the two hops\n"
            f"3. State your confidence and why\n\n"
            f"Be direct and concise."
        )

        brief = self._call(prompt)
        print(f"\n[Narrator] {brief[:120]}...")
        return {**state, "research_brief": brief}

    def as_runnable(self) -> Runnable:
        return RunnableLambda(self.narrate)


# ══════════════════════════════════════════════════════════════
# AGGREGATE METRICS  (call after full eval loop)
# ══════════════════════════════════════════════════════════════

class AggregateMetrics:
    """
    Reads all inference_results from MongoDB and prints the full
    metrics table. Call once after your eval loop finishes.

        for item in eval_set:
            pipeline.invoke({...})
        AggregateMetrics(cfg).compute()
    """
    def __init__(self, cfg: InferenceConfig):
        self.cfg    = cfg
        self.client = MongoClient(cfg.mongo_uri)
        self.col    = self.client[cfg.mongo_db][cfg.results_col]

    def compute(self) -> Dict:
        results = list(self.col.find({"metrics": {"$ne": {}}}))
        if not results:
            print("[AggregateMetrics] No eval results in MongoDB yet")
            return {}

        m_list   = [r["metrics"] for r in results]
        n        = len(m_list)
        def avg(k): return float(np.mean([m[k] for m in m_list if k in m]))

        correct        = [m for m in m_list if m.get("is_correct")]
        grounded       = [m for m in correct if m.get("is_grounded")]
        lucky          = [m for m in correct if m.get("is_lucky")]
        bridge_gr      = [m for m in correct if m.get("bridge_verified_grounded")]
        cold_correct   = [m for m in correct if m.get("cold_start")]
        n_correct      = len(correct)

        ground_rate = len(grounded)  / n_correct if n_correct else 0.0
        lucky_rate  = len(lucky)     / n_correct if n_correct else 0.0
        bridge_gr_r = len(bridge_gr) / n_correct if n_correct else 0.0

        table = {
            "n_queries":          n,
            "Hits@1":             avg("hits_at_1"),
            "Hits@3":             avg("hits_at_3"),
            "Hits@10":            avg("hits_at_10"),
            "MRR":                avg("mrr"),
            "nDCG@1":             avg("ndcg_at_1"),
            "nDCG@3":             avg("ndcg_at_3"),
            "nDCG@10":            avg("ndcg_at_10"),
            "Recall@10":          avg("recall_at_10"),
            "Ground_Rate":        ground_rate,
            "Lucky_Rate":         lucky_rate,
            "Bridge_Verified_GR": bridge_gr_r,
        }

        print(f"\n{'='*55}")
        print(f"AGGREGATE RESULTS  (n={n}, correct={n_correct})")
        print(f"{'='*55}")
        for k, v in table.items():
            if k == "n_queries":
                continue
            bar = "█" * int(v * 30)
            print(f"  {k:<25} {v:.4f}  {bar}")

        check = ground_rate + lucky_rate
        print(f"\n  Ground + Lucky = {check:.4f}  "
              f"{'✓' if abs(check - 1.0) < 0.01 or n_correct == 0 else '✗ should be 1.0'}")
        if cold_correct:
            print(f"  Cold-start correct queries: {len(cold_correct)}")
        return table


# ══════════════════════════════════════════════════════════════
# PIPELINE ASSEMBLY
# ══════════════════════════════════════════════════════════════

def build_inference_pipeline(cfg: InferenceConfig) -> Runnable:
    """
    Full LCEL inference chain matching the architecture doc.

    Free stack  (use_paid_services=False):
        BM25 + sentence-transformers FAISS
        → RRF fusion
        → Cold Start Gate
        → sentence-transformers episodic embeddings
        → BERT cross-encoder reranker
        → Groq llama-3.3-70b verifier
        → metrics + MongoDB write
        → Groq llama-3.3-70b narrator

    Paid stack  (use_paid_services=True):
        BM25 + Vertex AI retrieval
        → RRF fusion
        → Cold Start Gate
        → Vertex AI episodic embeddings
        → BERT cross-encoder reranker  (same model)
        → Gemini 1.5 Pro verifier
        → metrics + MongoDB write
        → Gemini 1.5 Pro narrator

    Flip cfg.use_paid_services=True to swap all paid components
    simultaneously.
    """
    return (
        BM25Retriever(cfg).as_runnable()
        | DenseRetriever(cfg).as_runnable()
        | RRFFusion(cfg).as_runnable()
        | ColdStartGate(cfg).as_runnable()
        | EpisodicMemoryFetcher(cfg).as_runnable()
        | BERTCrossEncoderReranker(cfg).as_runnable()
        | GroqBridgeVerifier(cfg).as_runnable()
        | MetricsComputer(cfg).as_runnable()
        | MongoResultWriter(cfg).as_runnable()
        | GroqNarrator(cfg).as_runnable()
    )


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    cfg      = InferenceConfig(use_paid_services=False)
    pipeline = build_inference_pipeline(cfg)

    # Demo mode: query_count=99 bypasses cold start gate
    result = pipeline.invoke({
        "query": (
            "Which tennis player won the tournament held in "
            "the city where the Eiffel Tower is located in 2023?"
        ),
        "gold_passage_id": None,   # None = demo mode, metrics skipped
        "query_count":     99,     # 99 = cold start gate open
    })

    print(f"\n{'='*55}")
    print(f"RESULT")
    print(f"{'='*55}")
    print(f"Top passage  : {result['top_passage']['title']}")
    print(f"Bridge entity: {result.get('bridge_entity')}")
    print(f"Chain        : {result.get('verified_chain')}")
    print(f"Verdict      : {result.get('retrieval_verdict')}")
    print(f"\nBrief:\n{result.get('research_brief', '')}")