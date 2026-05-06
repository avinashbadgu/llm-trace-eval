import { useQuery } from "@tanstack/react-query";

const BASE = "/api/v1";

async function fetchJson(path) {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export function useStats(model) {
  const qs = model ? `?model=${encodeURIComponent(model)}` : "";
  return useQuery({
    queryKey: ["stats", model],
    queryFn: () => fetchJson(`/evals/stats${qs}`),
  });
}

export function useTraces({ model, status, limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams();
  if (model)  params.set("model", model);
  if (status) params.set("status", status);
  params.set("limit", limit);
  params.set("offset", offset);
  return useQuery({
    queryKey: ["traces", model, status, limit, offset],
    queryFn: () => fetchJson(`/traces?${params}`),
  });
}

export function useEvals({ limit = 50 } = {}) {
  return useQuery({
    queryKey: ["evals", limit],
    queryFn: () => fetchJson(`/evals?limit=${limit}`),
  });
}

export function useTrace(id) {
  return useQuery({
    queryKey: ["trace", id],
    queryFn: () => fetchJson(`/traces/${id}`),
    enabled: !!id,
  });
}
