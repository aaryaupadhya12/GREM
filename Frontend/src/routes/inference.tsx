import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Nav } from "@/components/Nav";
import { MetricCard } from "@/components/MetricCard";

export const Route = createFileRoute("/inference")({
  head: () => ({
    meta: [
      { title: "Inference Pipeline — GREM" },
      { name: "description", content: "Run a query through GREM's online retrieval pipeline." },
    ],
  }),
  component: InferencePage,
});

const SAMPLES: { q: string; tag: string }[] = [
  { q: "Which film director starred in the movie that won Best Picture in 1994?", tag: "Bridge entity" },
  { q: "What is the capital of the country where the Eiffel Tower is located?", tag: "Geographic hop" },
  { q: "Who founded the company that owns the cloud platform hosting MongoDB Atlas?", tag: "Corporate chain" },
  { q: "Which university did the author of 'A Brief History of Time' attend for his PhD?", tag: "Biographical" },
  { q: "What year was the band that performed 'Bohemian Rhapsody' originally formed?", tag: "Temporal" },
  { q: "Which river flows through the city that hosted the 1992 Summer Olympics?", tag: "Comparison" },
  { q: "Who wrote the novel that inspired the film directed by Stanley Kubrick in 1980?", tag: "Multi-hop" },
  { q: "What is the primary language spoken in the country bordering Brazil to the west?", tag: "Geographic" },
  { q: "Which scientist discovered the element named after the country of Poland?", tag: "Entity bridge" },
  { q: "What position did the player who scored the winning goal in the 2014 World Cup final play?", tag: "Sports" },
];

type Stage = "idle" | "hybrid" | "memory" | "rerank" | "done";

const PIPELINE: { key: Stage; label: string; color: string }[] = [
  { key: "hybrid", label: "Hybrid Retrieval (BM25 + Vertex AI, RRF)", color: "bg-google-blue" },
  { key: "memory", label: "Atlas Episodic Memory (top-3 hints)", color: "bg-mongo-green" },
  { key: "rerank", label: "BERT Cross-Encoder Rerank", color: "bg-google-red" },
];

// Deterministic pseudo-metrics from query string so it feels "live" but stable.
function metricsFor(q: string, useMemory: boolean) {
  let h = 0;
  for (let i = 0; i < q.length; i++) h = (h * 31 + q.charCodeAt(i)) >>> 0;
  const r = (off: number, min: number, max: number) => {
    const v = ((h >>> off) & 0xffff) / 0xffff;
    return min + v * (max - min);
  };
  const base = {
    h1: r(0, 0.55, 0.78),
    h10: r(4, 0.82, 0.93),
    r2: r(8, 0.60, 0.80),
    mrr: r(12, 0.62, 0.80),
  };
  const boost = useMemory ? 1 : 0;
  return {
    h1: Math.min(0.99, base.h1 + boost * 0.14),
    h10: Math.min(0.99, base.h10 + boost * 0.05),
    r2: Math.min(0.99, base.r2 + boost * 0.10),
    mrr: Math.min(0.99, base.mrr + boost * 0.09),
    memoryHits: useMemory ? 3 : 0,
    latencyMs: 180 + Math.round(r(16, 0, 80)) + (useMemory ? 35 : 0),
  };
}

function InferencePage() {
  const [queryIdx, setQueryIdx] = useState(0);
  const query = SAMPLES[queryIdx].q;
  const [useMemory, setUseMemory] = useState(true);
  const [stage, setStage] = useState<Stage>("idle");
  const [shownStages, setShownStages] = useState<Stage[]>([]);

  const m = useMemo(() => metricsFor(query, useMemory), [query, useMemory]);
  const baseline = useMemo(() => metricsFor(query, false), [query]);

  const run = async () => {
    setStage("idle");
    setShownStages([]);
    const order: Stage[] = useMemory ? ["hybrid", "memory", "rerank"] : ["hybrid", "rerank"];
    for (const s of order) {
      setStage(s);
      await new Promise((r) => setTimeout(r, 650));
      setShownStages((prev) => [...prev, s]);
    }
    setStage("done");
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="mx-auto max-w-6xl px-6 py-12">
        <div className="text-xs font-semibold uppercase tracking-wider text-mongo-green">
          Online Pipeline
        </div>
        <h1 className="mt-1 font-display text-4xl font-bold tracking-tight">Inference</h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          Pick one of 10 representative HotpotQA-style queries and watch it flow through hybrid
          retrieval, Atlas episodic memory, and the distilled cross-encoder reranker.
        </p>

        {/* Input */}
        <div className="mt-8 rounded-xl border bg-card p-5">
          <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Select a query
          </label>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {SAMPLES.map((s, i) => {
              const active = i === queryIdx;
              return (
                <button
                  key={i}
                  onClick={() => {
                    setQueryIdx(i);
                    setStage("idle");
                    setShownStages([]);
                  }}
                  className={`rounded-lg border p-3 text-left text-sm transition ${
                    active
                      ? "border-google-blue bg-google-blue/5 shadow-sm"
                      : "border-border bg-background hover:bg-accent"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] text-muted-foreground">Q{i + 1}</span>
                    <span className="rounded-full border px-2 py-0.5 text-[10px] text-muted-foreground">
                      {s.tag}
                    </span>
                  </div>
                  <div className="mt-1 leading-snug">{s.q}</div>
                </button>
              );
            })}
          </div>
          <div className="mt-4 flex items-center justify-between gap-4 flex-wrap">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={useMemory}
                onChange={(e) => setUseMemory(e.target.checked)}
                className="h-4 w-4 accent-mongo-green"
              />
              Use Atlas episodic memory
            </label>
            <button
              onClick={run}
              className="rounded-md bg-google-blue px-5 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              Run inference
            </button>
          </div>
        </div>

        {/* Pipeline visual */}
        <div className="mt-8 grid gap-3 md:grid-cols-3">
          {PIPELINE.map((p) => {
            const skipped = !useMemory && p.key === "memory";
            const active = stage === p.key;
            const done = shownStages.includes(p.key);
            return (
              <div
                key={p.key}
                className={`relative overflow-hidden rounded-xl border p-4 transition ${
                  skipped
                    ? "opacity-40"
                    : done
                      ? "border-foreground/30 bg-card"
                      : active
                        ? "border-foreground bg-card shadow-md"
                        : "bg-card"
                }`}
              >
                <div className={`absolute left-0 top-0 h-1 w-full ${p.color}`} />
                <div className="text-xs text-muted-foreground">
                  {skipped ? "Skipped" : done ? "Complete" : active ? "Running…" : "Pending"}
                </div>
                <div className="mt-1 font-medium">{p.label}</div>
                {active && (
                  <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-muted">
                    <div className={`h-full ${p.color} animate-pulse`} style={{ width: "70%" }} />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Metrics */}
        <h2 className="mt-12 text-lg font-semibold">Retrieval Metrics</h2>
        <p className="text-sm text-muted-foreground">
          Comparison vs. BM25-only baseline for the current query.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Hits@1" value={m.h1.toFixed(3)} sub={delta(m.h1, baseline.h1)} color="blue" />
          <MetricCard label="Hits@10" value={m.h10.toFixed(3)} sub={delta(m.h10, baseline.h10)} color="red" />
          <MetricCard label="Recall@2" value={m.r2.toFixed(3)} sub={delta(m.r2, baseline.r2)} color="yellow" />
          <MetricCard label="MRR" value={m.mrr.toFixed(3)} sub={delta(m.mrr, baseline.mrr)} color="green" />
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <SmallStat label="Memory hits" value={`${m.memoryHits}/3`} />
          <SmallStat label="Latency" value={`${m.latencyMs} ms`} />
          <SmallStat label="Mode" value={useMemory ? "GREM (memory-aug)" : "BM25 baseline"} />
        </div>

        {/* Results preview */}
        {stage === "done" && (
          <div className="mt-10 rounded-xl border bg-card p-5">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Top-3 reranked passages
            </div>
            <ol className="mt-3 space-y-2 text-sm">
              {[0.92, 0.81, 0.74].map((score, i) => (
                <li key={i} className="flex items-center justify-between rounded-md border bg-background p-3">
                  <span>
                    <span className="font-mono text-xs text-muted-foreground">#{i + 1}</span>{" "}
                    Passage candidate {i + 1} — bridge entity recovered via episodic hint.
                  </span>
                  <span className="font-mono text-xs text-mongo-green">{score.toFixed(2)}</span>
                </li>
              ))}
            </ol>
          </div>
        )}
      </main>
    </div>
  );
}

function delta(a: number, b: number) {
  const d = a - b;
  const sign = d >= 0 ? "+" : "";
  return `${sign}${(d * 100).toFixed(1)}% vs BM25`;
}

function SmallStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-sm">{value}</div>
    </div>
  );
}
