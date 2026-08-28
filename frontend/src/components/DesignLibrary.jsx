import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

const KIND_EMOJI = {
  generated: "🎨",
  uploaded: "📤",
  processed: "✂️",
  composed: "🧩",
};

export default function DesignLibrary({ refreshKey = 0, selectedId, onSelect, mode = "manage" }) {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(false);

  async function reload() {
    setLoading(true);
    try { setAssets(await api.design.assets()); }
    catch { /* silent */ }
    finally { setLoading(false); }
  }

  useEffect(() => { reload(); }, [refreshKey]);

  async function remove(a) {
    if (!confirm(`Supprimer « ${a.name} » ?`)) return;
    await api.design.del(a.id);
    reload();
  }

  if (!assets.length) {
    return <p className="muted small-text">{loading ? "Chargement…" : "Bibliothèque vide."}</p>;
  }

  return (
    <div className="design-grid">
      {assets.map((a) => {
        const sel = mode === "picker" && selectedId === a.id;
        return (
          <div
            key={a.id}
            className={`design-card ${sel ? "selected" : ""}`}
            onClick={mode === "picker" ? () => onSelect?.(a.id) : undefined}
            style={mode === "picker" ? { cursor: "pointer" } : undefined}
          >
            <div className="dc-thumb" style={{ aspectRatio: `${a.width}/${a.height}` }}>
              <img src={a.url} alt={a.name} loading="lazy" />
            </div>
            <div className="dc-meta">
              <div className="dc-title">
                <span>{KIND_EMOJI[a.kind]}</span>
                <b>{a.name}</b>
              </div>
              <div className="dc-details">
                <span>{a.width}×{a.height}</span>
                {a.format && <span>· {a.format}</span>}
                <span>· {Math.round(a.size_bytes / 1024)} Ko</span>
              </div>
              {mode === "manage" && (
                <div className="dc-actions">
                  <a href={a.url} download={a.name + ".png"} className="ghost small">↓</a>
                  <button className="ghost small" onClick={() => remove(a)} title="Supprimer">✕</button>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
