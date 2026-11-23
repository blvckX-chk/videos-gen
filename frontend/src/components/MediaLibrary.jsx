import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";

const KIND_LABEL = { photo: "Photo", video: "Vidéo", audio: "Audio" };

function fmtDuration(s) {
  if (!s) return null;
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60);
  return m > 0 ? `${m}:${String(sec).padStart(2, "0")}` : `${sec}s`;
}
function fmtSize(b) {
  if (!b) return "";
  return b > 1048576 ? `${(b / 1048576).toFixed(1)} Mo` : `${Math.round(b / 1024)} Ko`;
}

/**
 * Médiathèque : photos, rushes vidéo et audio au même endroit.
 * `pickable` transforme les cartes en sélecteur (utilisé par le montage).
 */
export default function MediaLibrary({ pickable = false, kindFilter = null, onPick }) {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState(kindFilter || "");
  const [uploading, setUploading] = useState([]);   // noms en cours
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  // `visual` = photo + vidéo (tout ce qui peut devenir un plan de montage) :
  // l'API filtre par type unique, on écarte donc l'audio côté client.
  const refresh = useCallback(async () => {
    try {
      const visualOnly = kindFilter === "visual";
      const data = await api.media.list(visualOnly ? undefined : (filter || undefined));
      setItems(visualOnly ? data.filter((m) => m.kind !== "audio") : data);
    } catch (e) { setError(e.message); }
  }, [filter, kindFilter]);

  useEffect(() => { refresh(); }, [refresh]);

  async function uploadFiles(files) {
    const list = Array.from(files || []);
    if (!list.length) return;
    setError(null);
    setUploading((u) => [...u, ...list.map((f) => f.name)]);
    for (const f of list) {
      try { await api.media.upload(f); }
      catch (e) { setError(`${f.name} : ${e.message}`); }
      finally { setUploading((u) => u.filter((n) => n !== f.name)); }
    }
    refresh();
  }

  function onDrop(e) {
    e.preventDefault(); setDragging(false);
    uploadFiles(e.dataTransfer.files);
  }

  async function remove(id) {
    if (!confirm("Supprimer ce média ?")) return;
    try { await api.media.del(id); refresh(); }
    catch (e) { setError(e.message); }
  }

  const kinds = kindFilter ? [kindFilter] : ["", "photo", "video", "audio"];

  return (
    <div className={pickable ? "" : "card"}>
      {!pickable && <h2 style={{ marginTop: 0 }}>🎬 Médiathèque</h2>}
      {!pickable && (
        <p className="muted small-text">
          Tes <strong>rushes vidéo</strong>, photos produit et pistes audio — la matière
          première du montage. Glisse tes fichiers ici (jusqu'à 1 Go par fichier).
        </p>
      )}

      {!kindFilter && (
        <div className="seg" style={{ margin: "10px 0" }}>
          {kinds.map((k) => (
            <button key={k || "all"} type="button" className={filter === k ? "on" : ""}
              onClick={() => setFilter(k)}>
              {k ? KIND_LABEL[k] : "Tout"}
            </button>
          ))}
        </div>
      )}

      <div className={`dropzone ${dragging ? "over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}>
        <strong>Glisse des fichiers ici</strong>
        <span className="muted small-text">ou clique pour parcourir — vidéo, photo, audio</span>
        <input ref={inputRef} type="file" multiple hidden
          accept="video/*,image/*,audio/*"
          onChange={(e) => uploadFiles(e.target.files)} />
      </div>

      {uploading.length > 0 && (
        <p className="muted small-text">Import en cours : {uploading.join(", ")}…</p>
      )}
      {error && <div className="banner error" style={{ marginTop: 10 }}>{error}</div>}

      {items.length === 0 ? (
        <p className="empty">Médiathèque vide. Importe tes premiers rushes ci-dessus.</p>
      ) : (
        <div className="media-grid">
          {items.map((m) => (
            <div key={m.id} className={`media-item ${pickable ? "pickable" : ""}`}
              onClick={pickable ? () => onPick?.(m) : undefined}
              title={pickable ? "Ajouter au montage" : m.name}>
              <div className="media-thumb"
                style={m.thumb_url ? { backgroundImage: `url(${m.thumb_url})` } : undefined}>
                {!m.thumb_url && <span className="media-noimg">♪</span>}
                <span className="media-kind">{KIND_LABEL[m.kind]}</span>
                {m.duration && <span className="media-dur">{fmtDuration(m.duration)}</span>}
              </div>
              <div className="media-foot">
                <span className="media-name" title={m.name}>{m.name}</span>
                {!pickable && (
                  <button className="ghost small" onClick={(e) => { e.stopPropagation(); remove(m.id); }}>
                    ✕
                  </button>
                )}
              </div>
              {!pickable && (
                <span className="media-meta">
                  {m.width > 0 && `${m.width}×${m.height} · `}{fmtSize(m.size_bytes)}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
