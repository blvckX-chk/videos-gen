import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

// Onglet Stock : recherche de médias libres (Pexels / Pixabay) + import.
export default function StockStudio() {
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("photo");
  const [source, setSource] = useState("");
  const [sources, setSources] = useState([]);
  const [results, setResults] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [imported, setImported] = useState({});   // id -> "ok" | "busy" | "err"

  useEffect(() => {
    api.stock.sources().then((r) => setSources(r.sources || [])).catch(() => {});
  }, []);

  async function run(e) {
    e?.preventDefault();
    if (!q.trim() || busy) return;
    setBusy(true); setError(null); setResults([]);
    try {
      setResults(await api.stock.search(q.trim(), kind, source));
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  async function importItem(item) {
    setImported((m) => ({ ...m, [item.id]: "busy" }));
    try {
      await api.stock.import(item, q.trim());
      setImported((m) => ({ ...m, [item.id]: "ok" }));
    } catch {
      setImported((m) => ({ ...m, [item.id]: "err" }));
    }
  }

  const noKey = sources.length === 0;

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>🎞️ Stock — médias libres</h2>
      <p className="muted small-text">
        Cherche des <strong>photos</strong> et <strong>vidéos</strong> libres de droits
        (Pexels, Pixabay). Les photos vont dans ta bibliothèque Design ; les vidéos
        servent de b-roll.
      </p>

      {noKey && (
        <div className="banner" style={{ margin: "12px 0" }}>
          Aucune banque configurée. Ajoute <code>PEXELS_API_KEY</code> et/ou
          <code> PIXABAY_API_KEY</code> dans <code>backend/.env</code> (clés gratuites),
          puis redémarre le backend.
        </div>
      )}

      <form className="stock-bar" onSubmit={run}>
        <input type="text" value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Ex : coucher de soleil, café, ville la nuit…" />
        <div className="seg">
          <button type="button" className={kind === "photo" ? "on" : ""} onClick={() => setKind("photo")}>Photos</button>
          <button type="button" className={kind === "video" ? "on" : ""} onClick={() => setKind("video")}>Vidéos</button>
        </div>
        <select value={source} onChange={(e) => setSource(e.target.value)}>
          <option value="">Toutes sources</option>
          {sources.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <button className="primary" type="submit" disabled={busy || !q.trim()}>
          {busy ? "…" : "Rechercher"}
        </button>
      </form>

      {error && <div className="banner error" style={{ marginTop: 12 }}>{error}</div>}

      <div className="stock-grid">
        {results.map((it) => (
          <div key={it.id} className="stock-item">
            <div className="stock-thumb" style={{ backgroundImage: `url(${it.thumb})` }}>
              {it.kind === "video" && <span className="stock-badge">▶ {it.duration ? Math.round(it.duration) + "s" : "vidéo"}</span>}
              <span className="stock-src">{it.source}</span>
            </div>
            <div className="stock-foot">
              <span className="stock-author" title={it.author}>{it.author || "—"}</span>
              <button className="ghost small"
                disabled={imported[it.id] === "busy" || imported[it.id] === "ok"}
                onClick={() => importItem(it)}>
                {imported[it.id] === "ok" ? "✓ importé"
                  : imported[it.id] === "busy" ? "…"
                  : imported[it.id] === "err" ? "échec — réessayer"
                  : "Importer"}
              </button>
            </div>
          </div>
        ))}
      </div>

      {!busy && results.length === 0 && q && !error && (
        <p className="empty">Aucun résultat. Essaie d'autres mots-clés.</p>
      )}
    </div>
  );
}
