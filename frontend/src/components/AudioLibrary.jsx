import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

const KIND_LABEL = {
  original: "extrait vidéo",
  vocals: "voix isolée",
  instrumental: "musique (sans voix)",
  custom: "upload",
};

const KIND_EMOJI = {
  original: "🎬",
  vocals: "🗣️",
  instrumental: "🎵",
  custom: "🎧",
};

// Bibliothèque partagée de clips audio réutilisables.
// Mode "picker" (compact, sélectionnable) ou "manage" (avec suppression).
export default function AudioLibrary({ mode = "manage", selectedId = null, onSelect, refreshKey = 0 }) {
  const [clips, setClips] = useState([]);
  const [loading, setLoading] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      setClips(await api.audio.library());
    } catch {
      /* silencieux, banner géré ailleurs */
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); }, [refreshKey]);

  async function remove(clip) {
    if (!confirm(`Supprimer « ${clip.name} » ?`)) return;
    await api.audio.del(clip.id);
    reload();
  }

  if (!clips.length) {
    return <p className="muted small-text">{loading ? "Chargement…" : "Bibliothèque vide."}</p>;
  }

  return (
    <div className="audio-lib">
      {mode === "picker" && (
        <button
          type="button"
          className={`chip ${selectedId === null ? "active" : ""}`}
          onClick={() => onSelect?.(null)}
        >
          Aucun audio
        </button>
      )}
      {clips.map((c) => {
        const isSel = mode === "picker" && selectedId === c.id;
        return (
          <div
            key={c.id}
            className={`audio-card ${isSel ? "selected" : ""}`}
            onClick={mode === "picker" ? () => onSelect?.(c.id) : undefined}
            style={mode === "picker" ? { cursor: "pointer" } : undefined}
          >
            <div className="ac-head">
              <span className="ac-emoji">{KIND_EMOJI[c.kind]}</span>
              <div className="ac-title">
                <b>{c.name}</b>
                <span className="ac-kind">{KIND_LABEL[c.kind]} · {c.duration_seconds}s</span>
              </div>
              {mode === "manage" && (
                <button className="ghost small" onClick={() => remove(c)} title="Supprimer">✕</button>
              )}
            </div>
            <audio controls preload="none" src={c.url} style={{ width: "100%" }} />
          </div>
        );
      })}
    </div>
  );
}
