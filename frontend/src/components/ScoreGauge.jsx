import { RadialBarChart, RadialBar, ResponsiveContainer } from "recharts";
import clsx from "clsx";

function scoreColor(v) {
  if (v == null) return "text-gray-500";
  if (v >= 0.8) return "text-green-400";
  if (v >= 0.6) return "text-yellow-400";
  return "text-red-400";
}

export default function ScoreGauge({ label, value }) {
  const pct = value != null ? Math.round(value * 100) : null;
  const data = [{ value: pct ?? 0, fill: pct == null ? "#374151" : pct >= 80 ? "#4ade80" : pct >= 60 ? "#facc15" : "#f87171" }];

  return (
    <div className="stat-card items-center text-center">
      <div className="relative w-28 h-28">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="70%"
            outerRadius="100%"
            barSize={8}
            data={data}
            startAngle={90}
            endAngle={-270}
          >
            <RadialBar dataKey="value" cornerRadius={4} background={{ fill: "#1e293b" }} />
          </RadialBarChart>
        </ResponsiveContainer>
        <span className={clsx("absolute inset-0 flex items-center justify-center text-xl font-bold", scoreColor(value))}>
          {pct != null ? `${pct}%` : "—"}
        </span>
      </div>
      <p className="text-xs text-gray-400 mt-1 leading-tight">{label}</p>
    </div>
  );
}
