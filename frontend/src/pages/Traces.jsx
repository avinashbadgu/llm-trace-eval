import { useState } from "react";
import { format } from "date-fns";
import { useTraces } from "../hooks/useApi";
import StatusBadge from "../components/StatusBadge";

function ScoreCell({ value }) {
  if (value == null) return <span className="text-gray-600">—</span>;
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "text-green-400" : pct >= 60 ? "text-yellow-400" : "text-red-400";
  return <span className={color}>{pct}%</span>;
}

function TraceRow({ trace, onClick, selected }) {
  const e = trace.eval_run;
  return (
    <tr
      onClick={() => onClick(trace)}
      className={`cursor-pointer border-b border-white/5 hover:bg-white/5 transition-colors ${
        selected ? "bg-brand-900/30" : ""
      }`}
    >
      <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">
        {format(new Date(trace.created_at), "MM/dd HH:mm:ss")}
      </td>
      <td className="px-4 py-3 text-sm font-mono text-gray-300 max-w-[120px] truncate">
        {trace.model}
      </td>
      <td className="px-4 py-3 text-sm text-gray-200 max-w-[240px] truncate">
        {trace.question || trace.prompt}
      </td>
      <td className="px-4 py-3 text-sm text-right font-mono">
        {Math.round(trace.latency_ms)}ms
      </td>
      <td className="px-4 py-3 text-sm text-right font-mono text-gray-400">
        ${trace.cost_usd.toFixed(5)}
      </td>
      <td className="px-4 py-3"><ScoreCell value={e?.faithfulness} /></td>
      <td className="px-4 py-3"><ScoreCell value={e?.answer_relevancy} /></td>
      <td className="px-4 py-3"><StatusBadge status={trace.status} /></td>
    </tr>
  );
}

function TraceDetail({ trace }) {
  const e = trace.eval_run;
  return (
    <div className="card space-y-4 text-sm">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-white">Trace Detail</h3>
        <StatusBadge status={trace.status} />
      </div>

      <div className="grid grid-cols-3 gap-3 text-xs">
        {[
          ["Model", trace.model],
          ["Latency", `${Math.round(trace.latency_ms)}ms`],
          ["Cost", `$${trace.cost_usd.toFixed(6)}`],
          ["Prompt tokens", trace.prompt_tokens],
          ["Completion tokens", trace.completion_tokens],
          ["ID", trace.id.slice(0, 8) + "…"],
        ].map(([k, v]) => (
          <div key={k}>
            <p className="text-gray-500">{k}</p>
            <p className="text-gray-200 font-mono">{v}</p>
          </div>
        ))}
      </div>

      <div>
        <p className="text-gray-500 text-xs mb-1">Question / Prompt</p>
        <p className="bg-surface rounded p-3 text-gray-200 text-xs leading-relaxed whitespace-pre-wrap max-h-32 overflow-y-auto">
          {trace.question || trace.prompt}
        </p>
      </div>

      {trace.context && (
        <div>
          <p className="text-gray-500 text-xs mb-1">Retrieved Context</p>
          <p className="bg-surface rounded p-3 text-gray-300 text-xs leading-relaxed whitespace-pre-wrap max-h-32 overflow-y-auto">
            {trace.context}
          </p>
        </div>
      )}

      <div>
        <p className="text-gray-500 text-xs mb-1">Response</p>
        <p className="bg-surface rounded p-3 text-gray-200 text-xs leading-relaxed whitespace-pre-wrap max-h-40 overflow-y-auto">
          {trace.response}
        </p>
      </div>

      {e && (
        <div>
          <p className="text-gray-500 text-xs mb-2">RAGAS Scores</p>
          <div className="grid grid-cols-2 gap-2">
            {[
              ["Faithfulness", e.faithfulness],
              ["Answer Relevancy", e.answer_relevancy],
              ["Context Recall", e.context_recall],
              ["Context Precision", e.context_precision],
            ].map(([k, v]) => (
              <div key={k} className="bg-surface rounded p-2">
                <p className="text-[10px] text-gray-500">{k}</p>
                <ScoreCell value={v} />
              </div>
            ))}
          </div>
          {e.error && (
            <p className="mt-2 text-xs text-red-400 bg-red-950/40 rounded p-2">{e.error}</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function Traces() {
  const [model, setModel]   = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage]     = useState(0);
  const [selected, setSelected] = useState(null);

  const limit = 30;
  const { data: traces = [], isLoading } = useTraces({ model, status, limit, offset: page * limit });

  const models  = [...new Set(traces.map((t) => t.model))];
  const statuses = ["pending", "evaluating", "done", "error"];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Traces</h1>
        <div className="flex gap-2">
          <select
            value={model}
            onChange={(e) => { setModel(e.target.value); setPage(0); }}
            className="bg-panel border border-white/10 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">All models</option>
            {models.map((m) => <option key={m}>{m}</option>)}
          </select>
          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(0); }}
            className="bg-panel border border-white/10 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">All statuses</option>
            {statuses.map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
      </div>

      <div className={`grid gap-4 ${selected ? "md:grid-cols-[1fr_380px]" : ""}`}>
        <div className="card overflow-hidden p-0">
          {isLoading ? (
            <div className="flex items-center justify-center h-40 text-gray-500">Loading…</div>
          ) : traces.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-gray-500 gap-2">
              <span className="text-3xl">◎</span>
              <p className="text-sm">No traces yet. Send a request through the proxy.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-xs text-gray-500 uppercase tracking-wider">
                    {["Time", "Model", "Question", "Latency", "Cost", "Faithful", "Relevancy", "Status"].map((h) => (
                      <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {traces.map((t) => (
                    <TraceRow
                      key={t.id}
                      trace={t}
                      selected={selected?.id === t.id}
                      onClick={setSelected}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {selected && <TraceDetail trace={selected} />}
      </div>

      {/* Pagination */}
      <div className="flex items-center gap-2 justify-end">
        <button
          disabled={page === 0}
          onClick={() => setPage((p) => p - 1)}
          className="btn-ghost disabled:opacity-40"
        >
          ← Prev
        </button>
        <span className="text-sm text-gray-400">Page {page + 1}</span>
        <button
          disabled={traces.length < limit}
          onClick={() => setPage((p) => p + 1)}
          className="btn-ghost disabled:opacity-40"
        >
          Next →
        </button>
      </div>
    </div>
  );
}
