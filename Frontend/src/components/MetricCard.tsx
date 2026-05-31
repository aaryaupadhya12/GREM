interface Props {
  label: string;
  value: string;
  sub?: string;
  color?: "blue" | "red" | "yellow" | "green";
}

const colorMap = {
  blue: "border-google-blue/30 bg-google-blue/5 text-google-blue",
  red: "border-google-red/30 bg-google-red/5 text-google-red",
  yellow: "border-google-yellow/40 bg-google-yellow/10 text-foreground",
  green: "border-mongo-green/30 bg-mongo-green/5 text-mongo-green",
};

export function MetricCard({ label, value, sub, color = "blue" }: Props) {
  return (
    <div className={`rounded-xl border-2 p-5 ${colorMap[color]}`}>
      <div className="text-xs font-medium uppercase tracking-wider opacity-80">{label}</div>
      <div className="mt-2 font-display text-3xl font-bold tabular-nums">{value}</div>
      {sub && <div className="mt-1 text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}
