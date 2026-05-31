import { createFileRoute, Link } from "@tanstack/react-router";
import { Nav } from "@/components/Nav";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "GREM — Quality-Gated Multi-Hop Retrieval" },
      { name: "description", content: "Episodic Distillation for Verified RAG using Google Cloud + MongoDB Atlas." },
    ],
  }),
  component: Index,
});

function Index() {
  return (
    <div className="min-h-screen">
      <Nav />
      <main className="mx-auto max-w-6xl px-6 py-16">
        <div className="flex flex-wrap items-center gap-2 text-xs font-medium">
          <span className="rounded-full border border-google-blue/30 bg-google-blue/5 px-3 py-1 text-google-blue">Google Cloud</span>
          <span className="rounded-full border border-mongo-green/30 bg-mongo-green/5 px-3 py-1 text-mongo-green">MongoDB Atlas</span>
          <span className="rounded-full border border-google-yellow/40 bg-google-yellow/10 px-3 py-1">HotpotQA</span>
        </div>
        <h1 className="mt-6 max-w-3xl font-display text-5xl font-bold leading-tight tracking-tight sm:text-6xl">
          Quality-Gated{" "}
          <span className="text-google-blue">Multi-Hop</span>{" "}
          <span className="text-google-red">Retrieval</span>{" "}
          with <span className="text-mongo-green">Episodic Memory</span>
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
          GREM recovers BM25 hard failures using multi-agent reasoning, verification-aware
          aggregation, and distilled cross-encoder reranking — backed by MongoDB Atlas vector memory.
        </p>

        <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="New Hits@1" value="0.8745" color="blue" />
          <Stat label="nDCG@10" value="0.8421" color="yellow" />
          <Stat label="Recall@2" value="0.7912" color="red" />
          <Stat label="Recovery Rate" value="93.4%" sub="vs DCG & BM25" color="green" />
        </div>

        <div className="mt-12 grid gap-6 md:grid-cols-2">
          <Link
            to="/training"
            className="group rounded-2xl border-2 border-google-blue/20 bg-google-blue/5 p-8 transition hover:border-google-blue hover:shadow-lg"
          >
            <div className="text-xs font-semibold uppercase tracking-wider text-google-blue">Pipeline 01</div>
            <h2 className="mt-2 text-2xl font-bold">Training</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Walk through BM25 mining, the 3-agent reasoning layer, verification gate, and how
              high-confidence traces become Atlas episodic memory.
            </p>
            <div className="mt-4 text-sm font-medium text-google-blue group-hover:underline">Explore training →</div>
          </Link>
          <Link
            to="/inference"
            className="group rounded-2xl border-2 border-mongo-green/20 bg-mongo-green/5 p-8 transition hover:border-mongo-green hover:shadow-lg"
          >
            <div className="text-xs font-semibold uppercase tracking-wider text-mongo-green">Pipeline 02</div>
            <h2 className="mt-2 text-2xl font-bold">Inference</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Run a query through hybrid retrieval, Atlas memory fetch, and the distilled cross-encoder
              reranker. Watch metrics update live.
            </p>
            <div className="mt-4 text-sm font-medium text-mongo-green group-hover:underline">Try inference →</div>
          </Link>
        </div>

        <footer className="mt-20 border-t pt-6 text-xs text-muted-foreground">
          Hackathon demo · Frontend only · Designed to deploy on Vercel + Google Cloud.
        </footer>
      </main>
    </div>
  );
}

function Stat({ label, value, sub, color }: { label: string; value: string; sub?: string; color: "blue" | "red" | "yellow" | "green" }) {
  const c = {
    blue: "text-google-blue",
    red: "text-google-red",
    yellow: "text-google-yellow",
    green: "text-mongo-green",
  }[color];
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${c}`}>{value}</div>
      {sub && <div className="mt-1 text-[10px] text-muted-foreground">{sub}</div>}
    </div>
  );
}
