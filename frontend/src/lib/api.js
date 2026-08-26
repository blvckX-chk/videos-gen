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
  storyboard: (brief) =>
    fetch(`${BASE}/storyboard`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(brief),
    }).then(json),
  render: (storyboard, tier = "free", client_id = null) =>
    fetch(`${BASE}/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ storyboard, tier, client_id }),
    }).then(json),
  renderStatus: (id) => fetch(`${BASE}/render/${id}`).then(json),

  // Audio toolkit
  audio: {
    info: () => fetch(`${BASE}/audio/info`).then(json),
    library: () => fetch(`${BASE}/audio/library`).then(json),
    clip: (id) => fetch(`${BASE}/audio/clips/${id}`).then(json),
    del: (id) => fetch(`${BASE}/audio/clips/${id}`, { method: "DELETE" }).then(json),
    uploadVideo: (file, name) => {
      const fd = new FormData();
      fd.append("file", file);
      if (name) fd.append("name", name);
      return fetch(`${BASE}/audio/upload-video`, { method: "POST", body: fd }).then(json);
    },
    uploadAudio: (file, name) => {
      const fd = new FormData();
      fd.append("file", file);
      if (name) fd.append("name", name);
      return fetch(`${BASE}/audio/upload-audio`, { method: "POST", body: fd }).then(json);
    },
    separate: (clipId) =>
      fetch(`${BASE}/audio/clips/${clipId}/separate`, { method: "POST" }).then(json),
    apply: (payload) =>
      fetch(`${BASE}/audio/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).then(json),
    job: (id) => fetch(`${BASE}/audio/jobs/${id}`).then(json),
  },
  panels: (document_id, direction = "ltr", maxPages = 12) =>
    fetch(
      `${BASE}/documents/${document_id}/panels?direction=${direction}&max_pages=${maxPages}`,
      { method: "POST" }
    ).then(json),
};
