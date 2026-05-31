import { j as jsxRuntimeExports } from "../_libs/react.mjs";
const colorMap = {
  blue: "border-google-blue/30 bg-google-blue/5 text-google-blue",
  red: "border-google-red/30 bg-google-red/5 text-google-red",
  yellow: "border-google-yellow/40 bg-google-yellow/10 text-foreground",
  green: "border-mongo-green/30 bg-mongo-green/5 text-mongo-green"
};
function MetricCard({ label, value, sub, color = "blue" }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `rounded-xl border-2 p-5 ${colorMap[color]}`, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs font-medium uppercase tracking-wider opacity-80", children: label }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-2 font-display text-3xl font-bold tabular-nums", children: value }),
    sub && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-1 text-xs text-muted-foreground", children: sub })
  ] });
}
export {
  MetricCard as M
};
