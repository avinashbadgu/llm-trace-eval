import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
  BarChart, Bar, ResponsiveContainer, Legend,
} from "recharts";
import { format } from "date-fns";
import { useStats, useTraces, useEvals } from "../hooks/useApi";
import ScoreGauge from "../components/ScoreGauge";

function StatCard({ label, value, sub }) {
  return (
    <div className="stat-card">
      <p className="text-xs text-gray-400 uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-white">{value ?? "—"}</p>
      {sub && <p className="text-xs text-gray-500">{sub}</p>}
    </div>
  );
}

function LatencyCard({ lat }) {
  if (!lat) return <StatCard label="Latency" value="—" />;
  return (
    <div className="stat-card">
      <p className="text-xs text-gray-400 uppercase tracking-wider">Latency</p>
      <div className="flex gap-4 mt-1">
        {[["p50", lat.p50], ["p95", lat.p95], ["p99", lat.p99]].map(([k, v]) => (
          <div key={k} className="text-center">
            <p className="text-lg font-bold text-white">{Math.round(v)}ms</p>
            <p className="text-[10px] text-gray-500">{k}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [model, setModel] = useState("");
  const { data: stats, isLoading: statsLoading } = useStats(model || undefined);
  const { data: evals = [] } = useEvals({ limit: 100 });
  const { data: traces = [] } = useTraces({ limit: 200 });

  // Build time-series from traces: group by day, avg latency & cost
  const byDay = {};
  for (const t of traces) {
    const day = format(new Date(t.created_at), "MM/dd");
    if (!byDay[day]) byDay[day] = { day, latency: [], cost: 0, count: 0 };
    byDay[day].latency.push(t.latency_ms);
    byDay[day].cost += t.cost_usd;
    byDay[day].count++;
  }
  const timeData = Object.values(byDay).map((d) => ({
    day: d.day,
    avgLatency: Math.round(d.latency.reduce((a, b) => a + b, 0) / d.latency.length),
    cost: parseFloat(d.cost.toFixed(4)),
    count: d.count,
  }));

  // Build score trend from eval runs
  const scoreTrend = evals.slice(0, 50).reverse().map((e, i) => ({
    i,
    faithfulness: e.faithfulness != null ? parseFloat((e.faithfulness * 100).toFixed(1)) : null,
    relevancy: e.answer_relevancy != null ? parseFloat((e.answer_relevancy * 100).toFixed(1)) : null,
  }));

  // Model breakdown
  const modelData = stats
    ? Object.entries(stats.traces_by_model || {}).map(([m, count]) => ({ model: m, count }))
    : [];

  const models = [...new Set(traces.map((t) => t.model))];

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        Loading dashboard…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-gray-400 mt-0.5">Live evaluation metrics across all LLM traces</p>
        </div>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="bg-panel border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">All models</option>
          {models.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Traces"
          value={stats?.total_traces ?? 0}
          sub="lifetime"
        />
        <StatCard
          label="Total Cost"
          value={stats ? `$${stats.total_cost_usd.toFixed(4)}` : "—"}
          sub="USD"
        />
        <LatencyCard lat={stats?.latency} />
        <StatCard
          label="Evals Complete"
          value={evals.filter((e) => !e.error).length}
          sub={`of ${evals.length} total`}
        />
      </div>

      {/* RAGAS score gauges */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Avg RAGAS Scores
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <ScoreGauge label="Faithfulness" value={stats?.avg_faithfulness} />
          <ScoreGauge label="Answer Relevancy" value={stats?.avg_answer_relevancy} />
          <ScoreGauge label="Context Recall" value={stats?.avg_context_recall} />
          <ScoreGauge
            label="Evals w/ Error"
            value={
              evals.length
                ? 1 - evals.filter((e) => e.error).length / evals.length
                : null
            }
          />
        </div>
      </div>

      {/* Charts row */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Latency + cost over time */}
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Avg Latency & Cost / Day</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={timeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#9ca3af" }} />
              <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "#9ca3af" }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: "#9ca3af" }} />
              <Tooltip
                contentStyle={{ background: "#0f3460", border: "1px solid #ffffff20", borderRadius: 8 }}
                labelStyle={{ color: "#fff" }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: "#9ca3af" }} />
              <Line yAxisId="left" type="monotone" dataKey="avgLatency" name="Latency (ms)" stroke="#22c55e" strokeWidth={2} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="cost" name="Cost ($)" stroke="#60a5fa" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Score trend */}
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">RAGAS Score Trend (last 50)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={scoreTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
              <XAxis dataKey="i" tick={{ fontSize: 11, fill: "#9ca3af" }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#9ca3af" }} />
              <Tooltip
                contentStyle={{ background: "#0f3460", border: "1px solid #ffffff20", borderRadius: 8 }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: "#9ca3af" }} />
              <Line type="monotone" dataKey="faithfulness" name="Faithfulness" stroke="#a78bfa" strokeWidth={2} dot={false} connectNulls />
              <Line type="monotone" dataKey="relevancy" name="Relevancy" stroke="#34d399" strokeWidth={2} dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Model breakdown */}
      {modelData.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Traces by Model</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={modelData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: "#9ca3af" }} />
              <YAxis type="category" dataKey="model" tick={{ fontSize: 11, fill: "#9ca3af" }} width={140} />
              <Tooltip
                contentStyle={{ background: "#0f3460", border: "1px solid #ffffff20", borderRadius: 8 }}
              />
              <Bar dataKey="count" name="Traces" fill="#22c55e" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
