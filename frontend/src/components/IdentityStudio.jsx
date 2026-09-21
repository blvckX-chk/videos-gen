import { useEffect, useState } from "react";
import { api, getRole, setRole, getAdminSecret, setAdminSecret } from "../lib/api.js";

const AMBIANCES = ["moderne", "chaleureux", "luxe", "dynamique", "nature", "sobre"];

// Onglet Identité & Marque : rôle courant + gestion des chartes (fournie ou proposée).
export default function IdentityStudio() {
  const [role, setRoleState] = useState(getRole());
  const [me, setMe] = useState(null);
  const [chartes, setChartes] = useState([]);
  const [error, setError] = useState(null);

  // Proposition de charte
  const [sector, setSector] = useState("");
  const [ambiance, setAmbiance] = useState("moderne");
  const [nameHint, setNameHint] = useState("");
  const [proposals, setProposals] = useState([]);
  const [busy, setBusy] = useState(false);

  // Secret admin (baseline solo-prod)
  const [secret, setSecretState] = useState(getAdminSecret());

  useEffect(() => { refresh(); }, [role]);

  async function refresh() {
    try {
      setMe(await api.identity.me());
      setChartes(await api.identity.chartes());
    } catch (e) { setError(e.message); }
  }

  function changeRole(r) {
    setRole(r); setRoleState(r);
  }

  async function saveSecret() {
    setAdminSecret(secret.trim());
    setError(null);
    try {
      const m = await api.identity.me();
      setMe(m);
      if (m.role === "admin") setError(null);
      else setError("Secret non reconnu — rôle actuel : " + m.role);
    } catch (e) { setError(e.message); }
  }

  async function propose() {
    setBusy(true); setError(null); setProposals([]);
    try {
      setProposals(await api.identity.proposeChartes({
        sector, ambiance, name_hint: nameHint,
      }));
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function saveCharte(c) {
    await api.identity.createCharte(c);
    setProposals([]);
    refresh();
  }

  async function removeCharte(id) {
    if (!confirm("Supprimer cette charte ?")) return;
    await api.identity.deleteCharte(id);
    refresh();
  }

  const swatch = (c) => (
    <div className="pal-swatches">
      {["bg1", "bg2", "accent", "accent2", "fg"].map((k) =>
        c.palette[k] ? <span key={k} title={k} style={{ background: c.palette[k] }} /> : null
      )}
    </div>
  );

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>🎛️ Identité &amp; Marque</h2>
      <p className="muted small-text">
        Ton rôle définit tes droits (filigrane, providers). Les chartes définissent
        l'apparence des livrables. En <b>admin</b>, tu as accès à tout.
      </p>
      {error && <div className="banner error">{error}</div>}

      {/* -------------------------------------------------------- Rôle */}
      <section className="ds-section" style={{ borderTop: "none", paddingTop: 0 }}>
        <h3>Rôle courant</h3>
        <div className="tier-toggle">
          {["admin", "premium", "free"].map((r) => (
            <button key={r} className={`chip ${role === r ? "active" : ""}`}
              onClick={() => changeRole(r)}>{r}</button>
          ))}
        </div>
        {me && (
          <ul className="doc-stats" style={{ marginTop: 12 }}>
            <li>filigrane {me.watermark_forced ? <b>forcé</b> : <b>retirable</b>}</li>
            <li>tier max <b>{me.allowed_tier}</b></li>
            <li>quota/jour <b>{me.daily_quota ?? "∞"}</b></li>
            <li>batch <b>{me.batch_allowed ? "oui" : "non"}</b></li>
          </ul>
        )}
        <p className="muted small-text">
          (Le sélecteur simule un rôle pour tester. En production, seul le secret
          admin ci-dessous déverrouille le rôle admin ; sans lui, le rôle retombe
          à <b>free</b> — filigrane forcé, quotas.)
        </p>

        <div className="field small" style={{ marginTop: 12, maxWidth: 420 }}>
          <span>Secret admin (production)</span>
          <div style={{ display: "flex", gap: 8 }}>
            <input type="password" value={secret} autoComplete="off"
              onChange={(e) => setSecretState(e.target.value)}
              placeholder="ADMIN_SECRET défini côté serveur" style={{ flex: 1 }} />
            <button className="ghost" onClick={saveSecret}>Valider</button>
            {secret && (
              <button className="ghost small" onClick={() => { setSecretState(""); setAdminSecret(""); refresh(); }}>
                Effacer
              </button>
            )}
          </div>
          <span className="muted small-text">
            Stocké localement dans ce navigateur, envoyé en en-tête X-Admin-Secret.
            En dev (aucun secret serveur), tu es admin par défaut.
          </span>
        </div>
      </section>

      {/* -------------------------------------------------------- Proposer une charte */}
      <section className="ds-section">
        <h3>Proposer une charte</h3>
        <p className="muted small-text">Le client n'a pas de charte ? Réponds à ces questions et le système en propose 3.</p>
        <div className="ds-grid">
          <label className="field small"><span>Marque / client</span>
            <input type="text" value={nameHint} onChange={(e) => setNameHint(e.target.value)} placeholder="Chez Fatou" />
          </label>
          <label className="field small"><span>Secteur</span>
            <input type="text" value={sector} onChange={(e) => setSector(e.target.value)} placeholder="restaurant" />
          </label>
          <label className="field small"><span>Ambiance</span>
            <select value={ambiance} onChange={(e) => setAmbiance(e.target.value)}>
              {AMBIANCES.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </label>
        </div>
        <button className="ghost" onClick={propose} disabled={busy}>
          {busy ? "…" : "✨ Proposer 3 chartes"}
        </button>

        {proposals.length > 0 && (
          <div className="charte-grid">
            {proposals.map((c, i) => (
              <div key={i} className="charte-card" style={{ background: c.palette.bg1 }}>
                <div className="charte-name" style={{ color: c.palette.fg }}>{c.name}</div>
                {swatch(c)}
                <div className="charte-tone" style={{ color: c.palette.muted }}>{c.tone}</div>
                <button className="primary" onClick={() => saveCharte(c)}>Choisir</button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* -------------------------------------------------------- Chartes enregistrées */}
      <section className="ds-section">
        <h3>Chartes enregistrées</h3>
        {chartes.length === 0 ? (
          <p className="muted small-text">Aucune charte. Propose-en une ci-dessus.</p>
        ) : (
          <div className="charte-grid">
            {chartes.map((c) => (
              <div key={c.id} className="charte-card" style={{ background: c.palette.bg1 }}>
                <div className="charte-name" style={{ color: c.palette.fg }}>{c.name}</div>
                {swatch(c)}
                <div className="charte-tone" style={{ color: c.palette.muted }}>{c.tone}</div>
                <button className="ghost small" onClick={() => removeCharte(c.id)}>Supprimer</button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
