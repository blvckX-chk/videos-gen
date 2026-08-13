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
};
