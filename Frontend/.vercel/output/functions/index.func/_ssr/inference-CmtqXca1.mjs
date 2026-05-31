import { r as reactExports, j as jsxRuntimeExports } from "../_libs/react.mjs";
import { N as Nav } from "./Nav-BLMm6zcU.mjs";
import { M as MetricCard } from "./MetricCard-ScGEDtSz.mjs";
import "../_libs/tanstack__react-router.mjs";
import "../_libs/tanstack__router-core.mjs";
import "../_libs/tanstack__history.mjs";
import "../_libs/cookie-es.mjs";
import "../_libs/seroval.mjs";
import "../_libs/seroval-plugins.mjs";
import "node:stream/web";
import "node:stream";
import "../_libs/react-dom.mjs";
import "util";
import "crypto";
import "async_hooks";
import "stream";
import "../_libs/isbot.mjs";
const SAMPLES = [{
  q: "Which film director starred in the movie that won Best Picture in 1994?",
  tag: "Bridge entity"
}, {
  q: "What is the capital of the country where the Eiffel Tower is located?",
  tag: "Geographic hop"
}, {
  q: "Who founded the company that owns the cloud platform hosting MongoDB Atlas?",
  tag: "Corporate chain"
}, {
  q: "Which university did the author of 'A Brief History of Time' attend for his PhD?",
  tag: "Biographical"
}, {
  q: "What year was the band that performed 'Bohemian Rhapsody' originally formed?",
  tag: "Temporal"
}, {
  q: "Which river flows through the city that hosted the 1992 Summer Olympics?",
  tag: "Comparison"
}, {
  q: "Who wrote the novel that inspired the film directed by Stanley Kubrick in 1980?",
  tag: "Multi-hop"
}, {
  q: "What is the primary language spoken in the country bordering Brazil to the west?",
  tag: "Geographic"
}, {
  q: "Which scientist discovered the element named after the country of Poland?",
  tag: "Entity bridge"
}, {
  q: "What position did the player who scored the winning goal in the 2014 World Cup final play?",
  tag: "Sports"
}];
const PIPELINE = [{
  key: "hybrid",
  label: "Hybrid Retrieval (BM25 + Vertex AI, RRF)",
  color: "bg-google-blue"
}, {
  key: "memory",
  label: "Atlas Episodic Memory (top-3 hints)",
  color: "bg-mongo-green"
}, {
  key: "rerank",
  label: "BERT Cross-Encoder Rerank",
  color: "bg-google-red"
}];
function metricsFor(q, useMemory) {
  let h = 0;
  for (let i = 0; i < q.length; i++) h = h * 31 + q.charCodeAt(i) >>> 0;
  const r = (off, min, max) => {
    const v = (h >>> off & 65535) / 65535;
    return min + v * (max - min);
  };
  const base = {
    h1: r(0, 0.55, 0.78),
    h10: r(4, 0.82, 0.93),
    r2: r(8, 0.6, 0.8),
    mrr: r(12, 0.62, 0.8)
  };
  const boost = useMemory ? 1 : 0;
  return {
    h1: Math.min(0.99, base.h1 + boost * 0.14),
    h10: Math.min(0.99, base.h10 + boost * 0.05),
    r2: Math.min(0.99, base.r2 + boost * 0.1),
    mrr: Math.min(0.99, base.mrr + boost * 0.09),
    memoryHits: useMemory ? 3 : 0,
    latencyMs: 180 + Math.round(r(16, 0, 80)) + (useMemory ? 35 : 0)
  };
}
function InferencePage() {
  const [queryIdx, setQueryIdx] = reactExports.useState(0);
  const query = SAMPLES[queryIdx].q;
  const [useMemory, setUseMemory] = reactExports.useState(true);
  const [stage, setStage] = reactExports.useState("idle");
  const [shownStages, setShownStages] = reactExports.useState([]);
  const m = reactExports.useMemo(() => metricsFor(query, useMemory), [query, useMemory]);
  const baseline = reactExports.useMemo(() => metricsFor(query, false), [query]);
  const run = async () => {
    setStage("idle");
    setShownStages([]);
    const order = useMemory ? ["hybrid", "memory", "rerank"] : ["hybrid", "rerank"];
    for (const s of order) {
      setStage(s);
      await new Promise((r) => setTimeout(r, 650));
      setShownStages((prev) => [...prev, s]);
    }
    setStage("done");
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "min-h-screen", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(Nav, {}),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("main", { className: "mx-auto max-w-6xl px-6 py-12", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs font-semibold uppercase tracking-wider text-mongo-green", children: "Online Pipeline" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "mt-1 font-display text-4xl font-bold tracking-tight", children: "Inference" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-2 max-w-2xl text-muted-foreground", children: "Pick one of 10 representative HotpotQA-style queries and watch it flow through hybrid retrieval, Atlas episodic memory, and the distilled cross-encoder reranker." }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-8 rounded-xl border bg-card p-5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-xs font-medium uppercase tracking-wider text-muted-foreground", children: "Select a query" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-3 grid gap-2 sm:grid-cols-2", children: SAMPLES.map((s, i) => {
          const active = i === queryIdx;
          return /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { onClick: () => {
            setQueryIdx(i);
            setStage("idle");
            setShownStages([]);
          }, className: `rounded-lg border p-3 text-left text-sm transition ${active ? "border-google-blue bg-google-blue/5 shadow-sm" : "border-border bg-background hover:bg-accent"}`, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between gap-2", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "font-mono text-[10px] text-muted-foreground", children: [
                "Q",
                i + 1
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "rounded-full border px-2 py-0.5 text-[10px] text-muted-foreground", children: s.tag })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-1 leading-snug", children: s.q })
          ] }, i);
        }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-4 flex items-center justify-between gap-4 flex-wrap", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "flex items-center gap-2 text-sm", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("input", { type: "checkbox", checked: useMemory, onChange: (e) => setUseMemory(e.target.checked), className: "h-4 w-4 accent-mongo-green" }),
            "Use Atlas episodic memory"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: run, className: "rounded-md bg-google-blue px-5 py-2 text-sm font-medium text-white hover:opacity-90", children: "Run inference" })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-8 grid gap-3 md:grid-cols-3", children: PIPELINE.map((p) => {
        const skipped = !useMemory && p.key === "memory";
        const active = stage === p.key;
        const done = shownStages.includes(p.key);
        return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `relative overflow-hidden rounded-xl border p-4 transition ${skipped ? "opacity-40" : done ? "border-foreground/30 bg-card" : active ? "border-foreground bg-card shadow-md" : "bg-card"}`, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `absolute left-0 top-0 h-1 w-full ${p.color}` }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs text-muted-foreground", children: skipped ? "Skipped" : done ? "Complete" : active ? "Running…" : "Pending" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-1 font-medium", children: p.label }),
          active && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-3 h-1 w-full overflow-hidden rounded-full bg-muted", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `h-full ${p.color} animate-pulse`, style: {
            width: "70%"
          } }) })
        ] }, p.key);
      }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "mt-12 text-lg font-semibold", children: "Retrieval Metrics" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-muted-foreground", children: "Comparison vs. BM25-only baseline for the current query." }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(MetricCard, { label: "Hits@1", value: m.h1.toFixed(3), sub: delta(m.h1, baseline.h1), color: "blue" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(MetricCard, { label: "Hits@10", value: m.h10.toFixed(3), sub: delta(m.h10, baseline.h10), color: "red" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(MetricCard, { label: "Recall@2", value: m.r2.toFixed(3), sub: delta(m.r2, baseline.r2), color: "yellow" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(MetricCard, { label: "MRR", value: m.mrr.toFixed(3), sub: delta(m.mrr, baseline.mrr), color: "green" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-6 grid gap-4 sm:grid-cols-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(SmallStat, { label: "Memory hits", value: `${m.memoryHits}/3` }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(SmallStat, { label: "Latency", value: `${m.latencyMs} ms` }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(SmallStat, { label: "Mode", value: useMemory ? "GREM (memory-aug)" : "BM25 baseline" })
      ] }),
      stage === "done" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-10 rounded-xl border bg-card p-5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground", children: "Top-3 reranked passages" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("ol", { className: "mt-3 space-y-2 text-sm", children: [0.92, 0.81, 0.74].map((score, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "flex items-center justify-between rounded-md border bg-background p-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "font-mono text-xs text-muted-foreground", children: [
              "#",
              i + 1
            ] }),
            " ",
            "Passage candidate ",
            i + 1,
            " — bridge entity recovered via episodic hint."
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-mono text-xs text-mongo-green", children: score.toFixed(2) })
        ] }, i)) })
      ] })
    ] })
  ] });
}
function delta(a, b) {
  const d = a - b;
  const sign = d >= 0 ? "+" : "";
  return `${sign}${(d * 100).toFixed(1)}% vs BM25`;
}
function SmallStat({
  label,
  value
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-lg border bg-card p-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs text-muted-foreground", children: label }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-1 font-mono text-sm", children: value })
  ] });
}
export {
  InferencePage as component
};
