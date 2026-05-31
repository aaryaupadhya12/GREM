import { Link } from "@tanstack/react-router";

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="text-google-blue">G</span>
          <span className="text-google-red">R</span>
          <span className="text-google-yellow">E</span>
          <span className="text-mongo-green">M</span>
          <span className="ml-2 text-sm font-normal text-muted-foreground hidden sm:inline">
            Quality-Gated Multi-Hop Retrieval
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          <Link
            to="/training"
            className="rounded-md px-3 py-2 text-muted-foreground hover:bg-accent hover:text-foreground"
            activeProps={{ className: "rounded-md px-3 py-2 bg-accent text-foreground font-medium" }}
          >
            Training
          </Link>
          <Link
            to="/inference"
            className="rounded-md px-3 py-2 text-muted-foreground hover:bg-accent hover:text-foreground"
            activeProps={{ className: "rounded-md px-3 py-2 bg-accent text-foreground font-medium" }}
          >
            Inference
          </Link>
          <span className="ml-3 rounded-full bg-google-yellow/20 px-3 py-1 text-xs font-medium text-foreground">
            Hackathon
          </span>
        </nav>
      </div>
    </header>
  );
}
