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
const STEPS = [{
  id: 1,
  title: "HotpotQA Distractor",
  color: "blue",
  desc: "Load 97,852 bridge + comparison records. Multi-hop, retrieval-intensive.",
  detail: "Dataset is designed for hard negative mining and multi-hop reasoning research."
}, {
  id: 2,
  title: "BM25 Baseline Run",
  color: "red",
  desc: "Sparse retrieval over the full corpus to identify misses.",
  detail: "~30s on 4 CPU cores. Captures top-1 wrong predictions for failure mining."
}, {
  id: 3,
  title: "Hard Failure Extraction",
  color: "yellow",
  desc: "Mine 26,353 hard failures where BM25 top-1 ≠ gold.",
  detail: "Stored as structured JSON. Forms the seed of episodic memory."
}, {
  id: 4,
  title: "Multi-Agent Reasoning",
  color: "blue",
  desc: "Agents A/B/C: entity overlap, bridge chain, golden chunk.",
  detail: "Gemini Flash with compressed ~60–80 token summaries to bound context."
}, {
  id: 5,
  title: "Verification Layer",
  color: "red",
  desc: "@VERIFY_CHAIN, @VERIFY_ENTITY, @CROSS_CHECK gates.",
  detail: "Rejects weak reasoning traces before aggregation."
}, {
  id: 6,
  title: "Gemini Pro Aggregation",
  color: "yellow",
  desc: "Combine summaries, score Q_final, route to memory.",
  detail: "Output budget ~260 tokens. Groq 32B used as dev teacher."
}, {
  id: 7,
  title: "Quality Gate → Atlas",
  color: "green",
  desc: "Persist only traces with Q_final > 0.5 AND resolved.",
  detail: "Written to MongoDB Atlas vector index for future retrieval augmentation."
}];
const AGENT_METRICS = {
  "Agent A — Entity Overlap": {
    tokens: 60,
    pass: 0.81
  },
  "Agent B — Bridge Chain": {
    tokens: 60,
    pass: 0.74
  },
  "Agent C — Chunk Validator": {
    tokens: 80,
    pass: 0.86
  }
};
function TrainingPage() {
  const [active, setActive] = reactExports.useState(1);
  const [playing, setPlaying] = reactExports.useState(false);
  reactExports.useEffect(() => {
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
  const progress = active / STEPS.length * 100;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "min-h-screen", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(Nav, {}),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("main", { className: "mx-auto max-w-6xl px-6 py-12", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-end justify-between gap-4 flex-wrap", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs font-semibold uppercase tracking-wider text-google-blue", children: "Offline Pipeline" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "mt-1 font-display text-4xl font-bold tracking-tight", children: "Training" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-2 max-w-2xl text-muted-foreground", children: "Click steps or press play to walk through the offline training pipeline." })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => {
            setActive(1);
            setPlaying(true);
          }, className: "rounded-md bg-google-blue px-4 py-2 text-sm font-medium text-white hover:opacity-90", children: playing ? "Running…" : "▶ Play pipeline" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => {
            setPlaying(false);
            setActive(1);
          }, className: "rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent", children: "Reset" })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-6 h-2 w-full overflow-hidden rounded-full bg-muted", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-full bg-gradient-to-r from-google-blue via-google-red to-mongo-green transition-all duration-500", style: {
        width: `${progress}%`
      } }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(MetricCard, { label: "Records Processed", value: fmt(active * 13979), sub: "of 97,852", color: "blue" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(MetricCard, { label: "Hard Failures Mined", value: active >= 3 ? "26,353" : "—", color: "red" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(MetricCard, { label: "Avg Q_final", value: active >= 6 ? "0.71" : "—", sub: "threshold > 0.50", color: "yellow" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(MetricCard, { label: "Atlas Memories", value: active >= 7 ? "19,402" : "—", sub: "verified traces", color: "green" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-10 grid gap-3 lg:grid-cols-[1fr_1.2fr]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("ol", { className: "space-y-2", children: STEPS.map((s) => {
          const isActive = active === s.id;
          const done = active > s.id;
          return /* @__PURE__ */ jsxRuntimeExports.jsx("li", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { onClick: () => setActive(s.id), className: `flex w-full items-start gap-3 rounded-lg border p-3 text-left transition ${isActive ? "border-foreground bg-card shadow-sm" : done ? "border-mongo-green/30 bg-mongo-green/5" : "border-border bg-card hover:bg-accent"}`, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${done ? "bg-mongo-green text-white" : isActive ? "bg-foreground text-background" : "bg-muted text-muted-foreground"}`, children: done ? "✓" : s.id }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "font-medium", children: s.title }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs text-muted-foreground", children: s.desc })
            ] })
          ] }) }, s.id);
        }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("aside", { className: "rounded-xl border bg-card p-6", children: (() => {
          const s = STEPS[active - 1];
          return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground", children: [
              "Step ",
              s.id,
              " of ",
              STEPS.length
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "mt-1 text-2xl font-bold", children: s.title }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-3 text-sm text-muted-foreground", children: s.detail }),
            s.id === 4 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-6 space-y-3", children: Object.entries(AGENT_METRICS).map(([name, m]) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-between text-xs", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-medium", children: name }),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "tabular-nums text-muted-foreground", children: [
                  m.tokens,
                  "t · pass ",
                  (m.pass * 100).toFixed(0),
                  "%"
                ] })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-1 h-2 overflow-hidden rounded-full bg-muted", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-full bg-google-blue transition-all", style: {
                width: `${m.pass * 100}%`
              } }) })
            ] }, name)) }),
            s.id === 5 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-6 grid grid-cols-3 gap-2 text-center text-xs", children: ["@VERIFY_CHAIN", "@VERIFY_ENTITY", "@CROSS_CHECK"].map((v) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "rounded-md border border-google-red/30 bg-google-red/5 px-2 py-3 font-mono text-google-red", children: v }, v)) }),
            s.id === 7 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-6 rounded-lg border border-mongo-green/30 bg-mongo-green/5 p-4 font-mono text-xs", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-mongo-green", children: "→ MongoDB Atlas (M0)" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-1 text-muted-foreground", children: "{ q_final: 0.78, resolved: true, vector: [...] }" })
            ] })
          ] });
        })() })
      ] })
    ] })
  ] });
}
function fmt(n) {
  return Math.min(n, 97852).toLocaleString();
}
export {
  TrainingPage as component
};
