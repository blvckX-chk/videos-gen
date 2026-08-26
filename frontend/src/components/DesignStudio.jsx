import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";
import DesignLibrary from "./DesignLibrary.jsx";

const FORMAT_LABEL = {
  square: "Carré 1080×1080",
  story: "Story 1080×1920",
  landscape: "YouTube 1280×720",
  large_square: "Grand carré 2048×2048",
  a4: "A4 impression",
};

// Onglet Graphic Design — génération, upload, templates, opérations, bibliothèque.
export default function DesignStudio() {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [busy, setBusy] = useState(false);

  // Génération
  const [prompt, setPrompt] = useState("");
  const [format, setFormat] = useState("square");
  const [provider, setProvider] = useState("pollinations");
  const [tier, setTier] = useState("free");
  const [genJob, setGenJob] = useState(null);

  // Quote card
  const [quoteText, setQuoteText] = useState("La contrainte devient composition.");
  const [quoteAuthor, setQuoteAuthor] = useState("blvckUnlimited");
  const [quoteFormat, setQuoteFormat] = useState("square");
  const [quoteJob, setQuoteJob] = useState(null);

  // Opérations sur asset sélectionné
  const [pickedAsset, setPickedAsset] = useState(null);
  const [opJob, setOpJob] = useState(null);

  const uploadRef = useRef();

  useEffect(() => { api.design.info().then(setInfo).catch(() => {}); }, []);

  function bump() { setRefreshKey((k) => k + 1); }

  function pollJob(id, setter, onDone) {
    const t = setInterval(async () => {
      try {
        const j = await api.design.job(id);
        setter(j);
        if (j.status === "succeeded" || j.status === "failed") {
          clearInterval(t);
          onDone?.(j);
        }
      } catch { clearInterval(t); }
    }, 1500);
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); setError(null);
    try {
      await api.design.upload(file, file.name);
      bump();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); e.target.value = ""; }
  }

  async function generate() {
    if (!prompt.trim()) return;
    setError(null);
    try {
      const j = await api.design.generate({ prompt, format, provider, tier });
      setGenJob(j);
      pollJob(j.id, setGenJob, () => bump());
    } catch (err) { setError(err.message); }
  }

  async function makeQuote() {
    setError(null);
    try {
      const j = await api.design.quoteCard({
        text: quoteText, author: quoteAuthor, format: quoteFormat,
        watermark: "blvckUnlimited",
      });
      setQuoteJob(j);
      pollJob(j.id, setQuoteJob, () => bump());
    } catch (err) { setError(err.message); }
  }

  async function op(kind) {
    if (!pickedAsset) return;
    setError(null);
    try {
      let j;
      if (kind === "remove_bg") j = await api.design.removeBg(pickedAsset);
      else if (kind === "resize") j = await api.design.resize(pickedAsset,
        ["square", "story", "landscape"]);
      else return;
      setOpJob(j);
      pollJob(j.id, setOpJob, () => bump());
    } catch (err) { setError(err.message); }
  }

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>🎨 Graphic Design</h2>
      <p className="muted small-text">
        Visuels statiques — génération IA, templates (quote cards…), retrait de fond,
        déclinaison multi-format. Tier <code>free</code> par défaut ; providers premium
        activables via le champ <code>tier</code>.
      </p>

      {info && !info.rembg_available && (
        <div className="banner warn">
          <b>rembg</b> non installé — le retrait de fond sera indisponible tant que
          <code> pip install rembg[cpu]</code> n'aura pas été exécuté sur le serveur.
        </div>
      )}
      {error && <div className="banner error">{error}</div>}

      {/* -------------------------------------------------------- Génération */}
      <section className="ds-section">
        <h3>Générer une image</h3>
        <div className="ds-grid">
          <label className="field">
            <span>Prompt</span>
            <textarea rows={2} value={prompt} onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ex : bold flat-design illustration of a person reading a book, warm palette" />
          </label>
          <label className="field small">
            <span>Format</span>
            <select value={format} onChange={(e) => setFormat(e.target.value)}>
              {Object.entries(FORMAT_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="field small">
            <span>Provider</span>
            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
              {(info?.providers || []).map((p) => (
                <option key={p.id} value={p.id} disabled={!p.available}>
                  {p.name} {p.available ? (p.free ? "· gratuit" : "") : "· clé manquante"}
                </option>
              ))}
            </select>
          </label>
          <div className="tier-toggle">
            <button className={`chip ${tier === "free" ? "active" : ""}`} onClick={() => setTier("free")}>Free</button>
            <button className={`chip ${tier === "premium" ? "active" : ""}`} onClick={() => setTier("premium")}>Premium</button>
          </div>
        </div>
        <button className="primary" onClick={generate}
          disabled={!prompt.trim() || (genJob && genJob.status === "running")}>
          🎨 Générer
        </button>
        {genJob && <p className="muted small-text">Génération : <b>{genJob.status}</b>
          {genJob.error && <span className="err"> — {genJob.error}</span>}
        </p>}
      </section>

      {/* -------------------------------------------------------- Quote card */}
      <section className="ds-section">
        <h3>Template — carte de citation</h3>
        <p className="muted small-text">
          Alimenté par les points clés extraits d'un PDF (Slice 1). 100 % déterministe, aucun coût.
        </p>
        <div className="ds-grid">
          <label className="field">
            <span>Texte</span>
            <textarea rows={2} value={quoteText} onChange={(e) => setQuoteText(e.target.value)} />
          </label>
          <label className="field small">
            <span>Auteur</span>
            <input type="text" value={quoteAuthor} onChange={(e) => setQuoteAuthor(e.target.value)} />
          </label>
          <label className="field small">
            <span>Format</span>
            <select value={quoteFormat} onChange={(e) => setQuoteFormat(e.target.value)}>
              {["square", "story", "landscape"].map((f) => (
                <option key={f} value={f}>{FORMAT_LABEL[f]}</option>
              ))}
            </select>
          </label>
        </div>
        <button className="primary" onClick={makeQuote}
          disabled={!quoteText.trim() || (quoteJob && quoteJob.status === "running")}>
          🧩 Fabriquer la carte
        </button>
        {quoteJob && <p className="muted small-text">Composition : <b>{quoteJob.status}</b>
          {quoteJob.error && <span className="err"> — {quoteJob.error}</span>}
        </p>}
      </section>

      {/* -------------------------------------------------------- Upload */}
      <section className="ds-section">
        <h3>Uploader une image</h3>
        <button className="ghost" onClick={() => uploadRef.current?.click()} disabled={busy}>
          {busy ? "…" : "📎 Choisir un fichier"}
        </button>
        <input ref={uploadRef} type="file" accept="image/*" onChange={handleUpload}
          style={{ display: "none" }} />
      </section>

      {/* -------------------------------------------------------- Opérations */}
      <section className="ds-section">
        <h3>Traiter un asset</h3>
        <p className="muted small-text">Sélectionne un asset ci-dessous puis choisis une opération.</p>
        <div className="ops-row">
          <button className="ghost" disabled={!pickedAsset || !info?.rembg_available}
            onClick={() => op("remove_bg")}
            title={info?.rembg_available ? "Retirer le fond" : "rembg non installé"}>
            ✂️ Retirer le fond
          </button>
          <button className="ghost" disabled={!pickedAsset} onClick={() => op("resize")}>
            📐 Décliner en 3 formats
          </button>
        </div>
        {opJob && <p className="muted small-text" style={{ marginTop: 8 }}>
          Opération : <b>{opJob.status}</b>
          {opJob.error && <span className="err"> — {opJob.error}</span>}
        </p>}
        <div style={{ marginTop: 14 }}>
          <DesignLibrary mode="picker" selectedId={pickedAsset}
            onSelect={setPickedAsset} refreshKey={refreshKey} />
        </div>
      </section>

      {/* -------------------------------------------------------- Bibliothèque */}
      <section className="ds-section">
        <h3>Bibliothèque</h3>
        <DesignLibrary mode="manage" refreshKey={refreshKey} />
      </section>
    </div>
  );
}
