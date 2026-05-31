import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { MetricCard } from "@/components/MetricCard";

export const Route = createFileRoute("/training")({
  head: () => ({
    meta: [
      { title: "Training Pipeline — GREM" },
      { name: "description", content: "Step through the GREM offline training pipeline." },
    ],
  }),
  component: TrainingPage,
});

const STEPS = [
  {
    id: 1,
    title: "HotpotQA Distractor",
    color: "blue" as const,
    desc: "Load 97,852 bridge + comparison records. Multi-hop, retrieval-intensive.",
    detail: "Dataset is designed for hard negative mining and multi-hop reasoning research.",
  },
  {
    id: 2,
    title: "BM25 Baseline Run",
    color: "red" as const,
    desc: "Sparse retrieval over the full corpus to identify misses.",
    detail: "~30s on 4 CPU cores. Captures top-1 wrong predictions for failure mining.",
  },
  {
    id: 3,
    title: "Hard Failure Extraction",
    color: "yellow" as const,
    desc: "Mine 26,353 hard failures where BM25 top-1 ≠ gold.",
    detail: "Stored as structured JSON. Forms the seed of episodic memory.",
  },
  {
    id: 4,
    title: "Multi-Agent Reasoning",
    color: "blue" as const,
    desc: "Agents A/B/C: entity overlap, bridge chain, golden chunk.",
    detail: "Gemini Flash with compressed ~60–80 token summaries to bound context.",
  },
  {
    id: 5,
    title: "Verification Layer",
    color: "red" as const,
    desc: "@VERIFY_CHAIN, @VERIFY_ENTITY, @CROSS_CHECK gates.",
    detail: "Rejects weak reasoning traces before aggregation.",
  },
  {
    id: 6,
    title: "Gemini Pro Aggregation",
    color: "yellow" as const,
    desc: "Combine summaries, score Q_final, route to memory.",
    detail: "Output budget ~260 tokens. Groq 32B used as dev teacher.",
  },
  {
    id: 7,
    title: "Quality Gate → Atlas",
    color: "green" as const,
    desc: "Persist only traces with Q_final > 0.5 AND resolved.",
    detail: "Written to MongoDB Atlas vector index for future retrieval augmentation.",
  },
];

const AGENT_METRICS: Record<string, { tokens: number; pass: number }> = {
  "Agent A — Entity Overlap": { tokens: 60, pass: 0.81 },
  "Agent B — Bridge Chain": { tokens: 60, pass: 0.74 },
  "Agent C — Chunk Validator": { tokens: 80, pass: 0.86 },
};

function TrainingPage() {
  const [active, setActive] = useState(1);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => {
      setActive((a) => {
        if (a >= STEPS.length) {
          setPlaying(false);
          return a;
        }
        return a + 1;
      });
    }, 1100);
    return () => clearInterval(t);
  }, [playing]);

  const progress = (active / STEPS.length) * 100;

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="mx-auto max-w-6xl px-6 py-12">
        <div className="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-google-blue">
              Offline Pipeline
            </div>
            <h1 className="mt-1 font-display text-4xl font-bold tracking-tight">Training</h1>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              Click steps or press play to walk through the offline training pipeline.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                setActive(1);
                setPlaying(true);
              }}
              className="rounded-md bg-google-blue px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              {playing ? "Running…" : "▶ Play pipeline"}
            </button>
            <button
              onClick={() => {
                setPlaying(false);
                setActive(1);
              }}
              className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent"
            >
              Reset
            </button>
          </div>
        </div>

        {/* Progress */}
        <div className="mt-6 h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full bg-gradient-to-r from-google-blue via-google-red to-mongo-green transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Metrics */}
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Records Processed" value={fmt(active * 13979)} sub="of 97,852" color="blue" />
          <MetricCard label="Hard Failures Mined" value={active >= 3 ? "26,353" : "—"} color="red" />
          <MetricCard label="Avg Q_final" value={active >= 6 ? "0.71" : "—"} sub="threshold > 0.50" color="yellow" />
          <MetricCard
            label="Atlas Memories"
            value={active >= 7 ? "19,402" : "—"}
            sub="verified traces"
            color="green"
          />
        </div>

        {/* Steps */}
        <div className="mt-10 grid gap-3 lg:grid-cols-[1fr_1.2fr]">
          <ol className="space-y-2">
            {STEPS.map((s) => {
              const isActive = active === s.id;
              const done = active > s.id;
              return (
                <li key={s.id}>
                  <button
                    onClick={() => setActive(s.id)}
                    className={`flex w-full items-start gap-3 rounded-lg border p-3 text-left transition ${
                      isActive
                        ? "border-foreground bg-card shadow-sm"
                        : done
                          ? "border-mongo-green/30 bg-mongo-green/5"
                          : "border-border bg-card hover:bg-accent"
                    }`}
                  >
                    <span
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                        done
                          ? "bg-mongo-green text-white"
                          : isActive
                            ? "bg-foreground text-background"
                            : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {done ? "✓" : s.id}
                    </span>
                    <div>
                      <div className="font-medium">{s.title}</div>
                      <div className="text-xs text-muted-foreground">{s.desc}</div>
                    </div>
                  </button>
                </li>
              );
            })}
          </ol>

          <aside className="rounded-xl border bg-card p-6">
            {(() => {
              const s = STEPS[active - 1];
              return (
                <>
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Step {s.id} of {STEPS.length}
                  </div>
                  <h2 className="mt-1 text-2xl font-bold">{s.title}</h2>
                  <p className="mt-3 text-sm text-muted-foreground">{s.detail}</p>

                  {s.id === 4 && (
                    <div className="mt-6 space-y-3">
                      {Object.entries(AGENT_METRICS).map(([name, m]) => (
                        <div key={name}>
                          <div className="flex justify-between text-xs">
                            <span className="font-medium">{name}</span>
                            <span className="tabular-nums text-muted-foreground">
                              {m.tokens}t · pass {(m.pass * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
                            <div
                              className="h-full bg-google-blue transition-all"
                              style={{ width: `${m.pass * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {s.id === 5 && (
                    <div className="mt-6 grid grid-cols-3 gap-2 text-center text-xs">
                      {["@VERIFY_CHAIN", "@VERIFY_ENTITY", "@CROSS_CHECK"].map((v) => (
                        <div key={v} className="rounded-md border border-google-red/30 bg-google-red/5 px-2 py-3 font-mono text-google-red">
                          {v}
                        </div>
                      ))}
                    </div>
                  )}

                  {s.id === 7 && (
                    <div className="mt-6 rounded-lg border border-mongo-green/30 bg-mongo-green/5 p-4 font-mono text-xs">
                      <div className="text-mongo-green">→ MongoDB Atlas (M0)</div>
                      <div className="mt-1 text-muted-foreground">
                        {"{ q_final: 0.78, resolved: true, vector: [...] }"}
                      </div>
                    </div>
                  )}
                </>
              );
            })()}
          </aside>
        </div>
      </main>
    </div>
  );
}

function fmt(n: number) {
  return Math.min(n, 97852).toLocaleString();
}
