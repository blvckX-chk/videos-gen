import { useState } from "react";
import { api } from "../lib/api.js";

// Affiche les planches d'une BD avec les cases détectées, numérotées dans
// l'ordre de lecture, superposées sur la miniature de chaque page.
export default function PanelViewer({ documentId }) {
  const [pages, setPages] = useState(null);
  const [direction, setDirection] = useState("ltr");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function run(dir) {
    setLoading(true);
    setError(null);
    setDirection(dir);
    try {
      const res = await api.panels(documentId, dir);
      setPages(res.pages);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panels">
      <h3>Cases de la BD</h3>
      <p className="muted small-text">
        Détection des cases (segmentation par gouttières) et calcul de l'ordre de
        lecture. Choisis le sens : BD occidentale ou manga.
      </p>
      <div className="options" style={{ marginBottom: 14 }}>
        <button className={`chip ${direction === "ltr" ? "active" : ""}`} onClick={() => run("ltr")} disabled={loading}>
          BD occidentale (→)
        </button>
        <button className={`chip ${direction === "rtl" ? "active" : ""}`} onClick={() => run("rtl")} disabled={loading}>
          Manga (←)
        </button>
      </div>

      {loading && <p className="muted">Segmentation en cours…</p>}
      {error && <div className="banner error">{error}</div>}

      {pages && (
        <div className="pages-grid">
          {pages.map((pg) => (
            <div key={pg.page_index} className="page-card">
              <div className="page-head">
                Planche {pg.page_index + 1} · <b>{pg.panel_count}</b> cases
              </div>
              <div
                className="page-canvas"
                style={{ aspectRatio: `${pg.thumb_width} / ${pg.thumb_height}` }}
              >
                {pg.thumbnail && (
                  <img src={`data:image/jpeg;base64,${pg.thumbnail}`} alt={`planche ${pg.page_index + 1}`} />
                )}
                {pg.panels.map((p) => (
                  <div
                    key={p.index}
                    className="panel-box"
                    style={{
                      left: `${p.x * 100}%`,
                      top: `${p.y * 100}%`,
                      width: `${p.w * 100}%`,
                      height: `${p.h * 100}%`,
                    }}
                  >
                    <span className="panel-num">{p.index + 1}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
