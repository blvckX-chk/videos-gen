import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

// Super-agent graphique : intention → plan → exécution.
// Le plan reste éditable avant exécution (validation humaine, blueprint v1.1).
export default function DesignAgent({ onDone }) {
  const [intent, setIntent] = useState("");
  const [documents, setDocuments] = useState([]);
  const [docId, setDocId] = useState("");
  const [tier, setTier] = useState("free");
  const [format, setFormat] = useState("square");
  const [plan, setPlan] = useState(null);
  const [planning, setPlanning] = useState(false);
  const [runJob, setRunJob] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/api/documents").then((r) => r.json()).then(setDocuments).catch(() => {});
  }, []);

  async function propose() {
    if (!intent.trim()) return;
    setError(null); setPlanning(true); setPlan(null); setRunJob(null);
    try {
      const p = await api.design.agentPlan({
        intent, document_id: docId || null, tier, format,
      });
      setPlan(p);
    } catch (e) { setError(e.message); }
    finally { setPlanning(false); }
  }

  async function execute() {
    if (!plan?.steps?.length) return;
    setError(null); setRunning(true);
    try {
      const j = await api.design.agentRun({ plan });
      setRunJob(j);
      const t = setInterval(async () => {
        try {
          const upd = await api.design.job(j.id);
          setRunJob(upd);
          if (upd.status === "succeeded" || upd.status === "failed") {
            clearInterval(t);
            setRunning(false);
            onDone?.();
          }
        } catch { clearInterval(t); setRunning(false); }
      }, 1500);
    } catch (e) { setError(e.message); setRunning(false); }
  }

  function removeStep(i) {
    setPlan({ ...plan, steps: plan.steps.filter((_, k) => k !== i) });
  }

  return (
    <div className="agent-panel">
      <h3>🤖 Super-agent graphique</h3>
      <p className="muted small-text">
        Dis ce que tu veux, choisis éventuellement un document ingéré, et l'agent
        propose un plan de visuels. Tu <b>valides</b> avant exécution (v1.1).
      </p>

      <div className="ds-grid">
        <label className="field">
          <span>Intention</span>
          <textarea rows={2} value={intent} onChange={(e) => setIntent(e.target.value)}
            placeholder="Ex : prépare une série de visuels pour promouvoir le rapport" />
        </label>
        <label className="field small">
          <span>Document</span>
          <select value={docId} onChange={(e) => setDocId(e.target.value)}>
            <option value="">— aucun —</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>{d.title_guess || d.filename}</option>
            ))}
          </select>
        </label>
        <label className="field small">
          <span>Format</span>
          <select value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="square">Carré</option>
            <option value="story">Story</option>
            <option value="landscape">Paysage</option>
          </select>
        </label>
        <div className="tier-toggle">
          <button className={`chip ${tier === "free" ? "active" : ""}`} onClick={() => setTier("free")}>Free</button>
          <button className={`chip ${tier === "premium" ? "active" : ""}`} onClick={() => setTier("premium")}>Premium</button>
        </div>
      </div>

      <button className="ghost" onClick={propose} disabled={planning || !intent.trim()}>
        {planning ? "…" : "🧠 Proposer un plan"}
      </button>

      {error && <div className="banner error" style={{ marginTop: 10 }}>{error}</div>}

      {plan && (
        <div className="agent-plan">
          <div className="agent-plan-head">
            <b>{plan.steps.length}</b> étape{plan.steps.length > 1 ? "s" : ""}
            <span className="muted"> · générateur : {plan.generator}</span>
          </div>
          <ol className="agent-steps">
            {plan.steps.map((s, i) => (
              <li key={i} className={`agent-step t-${s.type}`}>
                <div className="step-head">
                  <span className="step-kind">{s.type === "template" ? s.template : `gen · ${s.provider}`}</span>
                  <button className="ghost small" onClick={() => removeStep(i)} title="Retirer">✕</button>
                </div>
                <div className="step-rationale">{s.rationale}</div>
                <details className="raw">
                  <summary>params</summary>
                  <pre>{JSON.stringify(s.type === "template" ? s.params : { prompt: s.prompt, provider: s.provider }, null, 2)}</pre>
                </details>
              </li>
            ))}
          </ol>
          <button className="primary" onClick={execute}
            disabled={running || !plan.steps.length}>
            {running ? "Exécution…" : `🚀 Exécuter (${plan.steps.length} visuel${plan.steps.length > 1 ? "s" : ""})`}
          </button>
          {runJob && (
            <p className="muted small-text" style={{ marginTop: 8 }}>
              Job : <b>{runJob.status}</b>
              {runJob.error && <span className="err"> — {runJob.error}</span>}
              {runJob.status === "succeeded" && ` · ${runJob.output_asset_ids.length} asset(s) créé(s) — voir la bibliothèque ↓`}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
