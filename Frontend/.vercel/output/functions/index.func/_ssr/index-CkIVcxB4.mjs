import { j as jsxRuntimeExports } from "../_libs/react.mjs";
import { L as Link } from "../_libs/tanstack__react-router.mjs";
import { N as Nav } from "./Nav-BLMm6zcU.mjs";
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
function Index() {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "min-h-screen", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(Nav, {}),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("main", { className: "mx-auto max-w-6xl px-6 py-16", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap items-center gap-2 text-xs font-medium", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "rounded-full border border-google-blue/30 bg-google-blue/5 px-3 py-1 text-google-blue", children: "Google Cloud" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "rounded-full border border-mongo-green/30 bg-mongo-green/5 px-3 py-1 text-mongo-green", children: "MongoDB Atlas" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "rounded-full border border-google-yellow/40 bg-google-yellow/10 px-3 py-1", children: "HotpotQA" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h1", { className: "mt-6 max-w-3xl font-display text-5xl font-bold leading-tight tracking-tight sm:text-6xl", children: [
        "Quality-Gated",
        " ",
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-google-blue", children: "Multi-Hop" }),
        " ",
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-google-red", children: "Retrieval" }),
        " ",
        "with ",
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-mongo-green", children: "Episodic Memory" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-6 max-w-2xl text-lg text-muted-foreground", children: "GREM recovers BM25 hard failures using multi-agent reasoning, verification-aware aggregation, and distilled cross-encoder reranking — backed by MongoDB Atlas vector memory." }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Stat, { label: "New Hits@1", value: "0.8745", color: "blue" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Stat, { label: "nDCG@10", value: "0.8421", color: "yellow" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Stat, { label: "Recall@2", value: "0.7912", color: "red" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Stat, { label: "Recovery Rate", value: "93.4%", sub: "vs DCG & BM25", color: "green" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-12 grid gap-6 md:grid-cols-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(Link, { to: "/training", className: "group rounded-2xl border-2 border-google-blue/20 bg-google-blue/5 p-8 transition hover:border-google-blue hover:shadow-lg", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs font-semibold uppercase tracking-wider text-google-blue", children: "Pipeline 01" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "mt-2 text-2xl font-bold", children: "Training" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-2 text-sm text-muted-foreground", children: "Walk through BM25 mining, the 3-agent reasoning layer, verification gate, and how high-confidence traces become Atlas episodic memory." }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-4 text-sm font-medium text-google-blue group-hover:underline", children: "Explore training →" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(Link, { to: "/inference", className: "group rounded-2xl border-2 border-mongo-green/20 bg-mongo-green/5 p-8 transition hover:border-mongo-green hover:shadow-lg", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs font-semibold uppercase tracking-wider text-mongo-green", children: "Pipeline 02" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "mt-2 text-2xl font-bold", children: "Inference" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-2 text-sm text-muted-foreground", children: "Run a query through hybrid retrieval, Atlas memory fetch, and the distilled cross-encoder reranker. Watch metrics update live." }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-4 text-sm font-medium text-mongo-green group-hover:underline", children: "Try inference →" })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("footer", { className: "mt-20 border-t pt-6 text-xs text-muted-foreground", children: "Hackathon demo · Frontend only · Designed to deploy on Vercel + Google Cloud." })
    ] })
  ] });
}
function Stat({
  label,
  value,
  sub,
  color
}) {
  const c = {
    blue: "text-google-blue",
    red: "text-google-red",
    yellow: "text-google-yellow",
    green: "text-mongo-green"
  }[color];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl border bg-card p-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs uppercase tracking-wider text-muted-foreground", children: label }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `mt-1 text-2xl font-bold tabular-nums ${c}`, children: value }),
    sub && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-1 text-[10px] text-muted-foreground", children: sub })
  ] });
}
export {
  Index as component
};
