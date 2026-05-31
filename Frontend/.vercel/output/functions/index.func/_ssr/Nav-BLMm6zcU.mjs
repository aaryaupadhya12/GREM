import { j as jsxRuntimeExports } from "../_libs/react.mjs";
import { L as Link } from "../_libs/tanstack__react-router.mjs";
function Nav() {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("header", { className: "sticky top-0 z-40 border-b bg-background/80 backdrop-blur", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mx-auto flex max-w-6xl items-center justify-between px-6 py-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(Link, { to: "/", className: "flex items-center gap-2 font-semibold tracking-tight", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-google-blue", children: "G" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-google-red", children: "R" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-google-yellow", children: "E" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-mongo-green", children: "M" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm font-normal text-muted-foreground hidden sm:inline", children: "Quality-Gated Multi-Hop Retrieval" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("nav", { className: "flex items-center gap-1 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        Link,
        {
          to: "/training",
          className: "rounded-md px-3 py-2 text-muted-foreground hover:bg-accent hover:text-foreground",
          activeProps: { className: "rounded-md px-3 py-2 bg-accent text-foreground font-medium" },
          children: "Training"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        Link,
        {
          to: "/inference",
          className: "rounded-md px-3 py-2 text-muted-foreground hover:bg-accent hover:text-foreground",
          activeProps: { className: "rounded-md px-3 py-2 bg-accent text-foreground font-medium" },
          children: "Inference"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-3 rounded-full bg-google-yellow/20 px-3 py-1 text-xs font-medium text-foreground", children: "Hackathon" })
    ] })
  ] }) });
}
export {
  Nav as N
};
