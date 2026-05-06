import { useState, useMemo } from "react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import { useTraces, useEvals } from "../hooks/useApi";

const COLORS = ["#22c55e", "#60a5fa", "#f472b6", "#fb923c", "#a78bfa"];

function avg(arr) {
  const filtered = arr.filter((v) => v != null);
  return filtered.length ? filtered.reduce((a, b) => a + b, 0) / filtered.length : null;
}

function pct(v) {
  return v != null ? parseFloat((v * 100).toFixed(1)) : null;
}

export default function Compare() {
  const { data: traces = [] } = useTraces({ limit: 200 });
  const { data: evals = [] }  = useEvals({ limit: 200 });

  const models = useMemo(() => [...new Set(traces.map((t) => t.model))], [traces]);

  const [selected, setSelected] = useState([]);

  const toggle = (m) =>
    setSelected((prev) =>
      prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m].slice(-4)
    );

  // Build per-model stats
  const modelStats = useMemo(() => {
    const evalByTrace = Object.fromEntries(evals.map((e) => [e.trace_id, e]));

    return models.map((model, i) => {
      const modelTraces = traces.filter((t) => t.model === model);
      const modelEvals  = modelTraces.map((t) => evalByTrace[t.id]).filter(Boolean);

      const latencies = modelTraces.map((t) => t.latency_ms);
      const costs     = modelTraces.map((t) => t.cost_usd);

      return {
        model,
        color: COLORS[i % COLORS.length],
        count: modelTraces.length,
        avgLatency: latencies.length ? avg(latencies) : null,
        avgCost: costs.length ? avg(costs) : null,
        faithfulness:    pct(avg(modelEvals.map((e) => e.faithfulness))),
        answerRelevancy: pct(avg(modelEvals.map((e) => e.answer_relevancy))),
        contextRecall:   pct(avg(modelEvals.map((e) => e.context_recall))),
        errorRate: modelTraces.length
          ? (modelTraces.filter((t) => t.status === "error").length / modelTraces.length) * 100
          : 0,
      };
    });
  }, [models, traces, evals]);

  const filteredStats = selected.length
    ? modelStats.filter((s) => selected.includes(s.model))
    : modelStats;

  // Radar data
  const radarData = [
    { metric: "Faithfulness",  ...Object.fromEntries(filteredStats.map((s) => [s.model, s.faithfulness])) },
    { metric: "Relevancy",     ...Object.fromEntries(filteredStats.map((s) => [s.model, s.answerRelevancy])) },
    { metric: "Context Recall",...Object.fromEntries(filteredStats.map((s) => [s.model, s.contextRecall])) },
    { metric: "Latency Score", ...Object.fromEntries(filteredStats.map((s) => [s.model, s.avgLatency != null ? Math.max(0, 100 - s.avgLatency / 50) : null])) },
  ];

  // Bar comparison
  const barData = filteredStats.map((s) => ({
    model: s.model.length > 18 ? s.model.slice(0, 18) + "…" : s.model,
    Faithfulness: s.faithfulness,
    Relevancy: s.answerRelevancy,
    "Context Recall": s.contextRecall,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Model Comparison</h1>
        <p className="text-sm text-gray-400 mt-0.5">Select up to 4 models to compare side-by-side</p>
      </div>

      {/* Model selector */}
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">Select Models</h3>
        <div className="flex flex-wrap gap-2">
          {models.map((m, i) => (
            <button
              key={m}
              onClick={() => toggle(m)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                selected.includes(m)
                  ? "border-transparent text-white"
                  : "border-white/10 text-gray-400 hover:border-white/30"
              }`}
              style={selected.includes(m) ? { backgroundColor: COLORS[i % COLORS.length] + "33", borderColor: COLORS[i % COLORS.length] } : {}}
            >
              {m}
            </button>
          ))}
          {models.length === 0 && (
            <p className="text-sm text-gray-500">No models tracked yet.</p>
          )}
        </div>
      </div>

      {filteredStats.length > 0 && (
        <>
          {/* Summary table */}
          <div className="card overflow-hidden p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-xs text-gray-500 uppercase tracking-wider">
                  {["Model", "Traces", "Avg Latency", "Avg Cost", "Faithfulness", "Relevancy", "Error Rate"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredStats.map((s, i) => (
                  <tr key={s.model} className="border-b border-white/5">
                    <td className="px-4 py-3 flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} />
                      <span className="font-mono text-xs text-gray-200">{s.model}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-300">{s.count}</td>
                    <td className="px-4 py-3 text-gray-300">{s.avgLatency ? `${Math.round(s.avgLatency)}ms` : "—"}</td>
                    <td className="px-4 py-3 text-gray-300">{s.avgCost ? `$${s.avgCost.toFixed(5)}` : "—"}</td>
                    <td className="px-4 py-3 font-medium">
                      {s.faithfulness != null ? (
                        <span className={s.faithfulness >= 80 ? "text-green-400" : s.faithfulness >= 60 ? "text-yellow-400" : "text-red-400"}>
                          {s.faithfulness}%
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3 font-medium">
                      {s.answerRelevancy != null ? (
                        <span className={s.answerRelevancy >= 80 ? "text-green-400" : s.answerRelevancy >= 60 ? "text-yellow-400" : "text-red-400"}>
                          {s.answerRelevancy}%
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-300">{s.errorRate.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Charts */}
          <div className="grid md:grid-cols-2 gap-4">
            {/* Radar */}
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-300 mb-4">Quality Radar</h3>
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#ffffff15" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: "#9ca3af" }} />
                  {filteredStats.map((s) => (
                    <Radar
                      key={s.model}
                      name={s.model}
                      dataKey={s.model}
                      stroke={s.color}
                      fill={s.color}
                      fillOpacity={0.15}
                      strokeWidth={2}
                    />
                  ))}
                  <Legend wrapperStyle={{ fontSize: 11, color: "#9ca3af" }} />
                  <Tooltip
                    contentStyle={{ background: "#0f3460", border: "1px solid #ffffff20", borderRadius: 8 }}
                    formatter={(v) => v != null ? `${v}%` : "—"}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* Grouped bar */}
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-300 mb-4">Score Breakdown by Model</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                  <XAxis dataKey="model" tick={{ fontSize: 10, fill: "#9ca3af" }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#9ca3af" }} />
                  <Tooltip
                    contentStyle={{ background: "#0f3460", border: "1px solid #ffffff20", borderRadius: 8 }}
                    formatter={(v) => v != null ? `${v}%` : "—"}
                  />
                  <Legend wrapperStyle={{ fontSize: 11, color: "#9ca3af" }} />
                  <Bar dataKey="Faithfulness" fill="#a78bfa" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Relevancy" fill="#34d399" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Context Recall" fill="#60a5fa" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
