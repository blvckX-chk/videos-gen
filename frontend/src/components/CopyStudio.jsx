import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

const DEFAULT_PLATFORMS = ["tiktok", "instagram", "linkedin", "meta_ad"];

// Onglet Copywriting : accroche + corps + CTA + hashtags, natif par plateforme, A/B.
export default function CopyStudio() {
  const [platforms, setPlatforms] = useState([]);
  const [selected, setSelected] = useState(DEFAULT_PLATFORMS);
  const [documents, setDocuments] = useState([]);
  const [docId, setDocId] = useState("");
  const [intent, setIntent] = useState("");
  const [tone, setTone] = useState("");
  const [variants, setVariants] = useState(2);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState("");

  useEffect(() => {
    api.copy.platforms().then(setPlatforms).catch(() => {});
    fetch("/api/documents").then((r) => r.json()).then(setDocuments).catch(() => {});
  }, []);

  function toggle(p) {
    setSelected((s) => (s.includes(p) ? s.filter((x) => x !== p) : [...s, p]));
  }

  async function generate() {
    if (!intent.trim() && !docId) {
      setError("Donne une intention ou choisis un document.");
      return;
    }
    setBusy(true); setError(null); setResult(null);
    try {
      setResult(await api.copy.generate({
        intent: intent || null, document_id: docId || null,
        platforms: selected, tone: tone || null, variants: Number(variants),
      }));
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  function copyText(v, key) {
    const text = `${v.hook}\n\n${v.body}\n\n${v.cta}\n${(v.hashtags || []).join(" ")}`;
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(key); setTimeout(() => setCopied(""), 1500);
    });
  }

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>✍️ Copywriting</h2>
      <p className="muted small-text">
        Accroche, corps, CTA et hashtags <b>natifs par plateforme</b>, en variantes A/B.
        Depuis une intention ou un document. Ton de marque respecté.
      </p>
      {error && <div className="banner error">{error}</div>}

      <div className="ds-grid">
        <label className="field">
          <span>Intention</span>
          <textarea rows={2} value={intent} onChange={(e) => setIntent(e.target.value)}
            placeholder="Ex : lancement d'un cahier premium fabriqué au Bénin" />
        </label>
        <label className="field small">
          <span>Document (option)</span>
          <select value={docId} onChange={(e) => setDocId(e.target.value)}>
            <option value="">— aucun —</option>
            {documents.map((d) => <option key={d.id} value={d.id}>{d.title_guess || d.filename}</option>)}
          </select>
        </label>
        <label className="field small">
          <span>Ton</span>
          <input type="text" value={tone} onChange={(e) => setTone(e.target.value)} placeholder="chaleureux, premium" />
        </label>
        <label className="field small">
          <span>Variantes</span>
          <select value={variants} onChange={(e) => setVariants(e.target.value)}>
            <option value={1}>1</option><option value={2}>2</option><option value={3}>3</option>
          </select>
        </label>
      </div>

      <div className="platforms-pick">
        {platforms.map((p) => (
          <button key={p.id} type="button"
            className={`chip ${selected.includes(p.id) ? "active" : ""}`}
            onClick={() => toggle(p.id)} title={p.tone}>
            {p.label}
          </button>
        ))}
      </div>

      <button className="primary" onClick={generate} disabled={busy || !selected.length}>
        {busy ? "Rédaction…" : "✍️ Générer le copy"}
      </button>

      {result && (
        <div className="copy-result">
          <p className="muted small-text">Générateur : {result.generator}</p>
          {result.platforms.map((pc) => (
            <div key={pc.platform} className="copy-platform">
              <h3>{(platforms.find((p) => p.id === pc.platform) || {}).label || pc.platform}</h3>
              <div className="copy-variants">
                {pc.variants.map((v) => {
                  const key = `${pc.platform}-${v.label}`;
                  return (
                    <div key={v.label} className="copy-card">
                      <div className="copy-head">
                        <span className="copy-label">Variante {v.label}</span>
                        <button className="ghost small" onClick={() => copyText(v, key)}>
                          {copied === key ? "copié ✓" : "copier"}
                        </button>
                      </div>
                      <p className="copy-hook">{v.hook}</p>
                      <p className="copy-body">{v.body}</p>
                      <p className="copy-cta">{v.cta}</p>
                      {v.hashtags?.length > 0 && (
                        <p className="copy-tags">{v.hashtags.join(" ")}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
