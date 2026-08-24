// Petit client pour l'API backend.
const BASE = "/api";

async function json(res) {
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Erreur ${res.status}`);
  }
  return res.json();
}

export const api = {
  providers: () => fetch(`${BASE}/providers`).then(json),
  enhance: (prompt) =>
    fetch(`${BASE}/enhance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    }).then(json),
  generate: (payload) =>
    fetch(`${BASE}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(json),
  job: (id) => fetch(`${BASE}/jobs/${id}`).then(json),
  jobs: () => fetch(`${BASE}/jobs`).then(json),

  // Slice 1 — ingestion PDF + clarification
  ingest: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch(`${BASE}/ingest`, { method: "POST", body: fd }).then(json);
  },
  brief: (document_id, answers) =>
    fetch(`${BASE}/brief`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id, answers }),
    }).then(json),
  panels: (document_id, direction = "ltr", maxPages = 12) =>
    fetch(
      `${BASE}/documents/${document_id}/panels?direction=${direction}&max_pages=${maxPages}`,
      { method: "POST" }
    ).then(json),
};
