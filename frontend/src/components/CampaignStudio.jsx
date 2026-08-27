import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";

const KIND_EMOJI = { image: "🖼️", video: "🎬", audio: "🎧" };
const TYPE_LABEL = {
  image_template: "template",
  image_generate: "génération IA",
  video_storyboard: "vidéo (Remotion)",
};

// Le super-agent unifié : intention → plan multi-modalités → livrables.
// C'est le sommet du système : orchestre design / storyboard / rendu / audio.
export default function CampaignStudio() {
  const [documents, setDocuments] = useState([]);
  const [intent, setIntent] = useState("Prépare une campagne complète pour promouvoir ce document sur les réseaux sociaux");
  const [docId, setDocId] = useState("");
  const [tier, setTier] = useState("free");
  const [includeVideo, setIncludeVideo] = useState(false);
  const [plan, setPlan] = useState(null);
  const [planning, setPlanning] = useState(false);
  const [job, setJob] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const poller = useRef(null);

  useEffect(() => {
    fetch("/api/documents").then((r) => r.json()).then(setDocuments).catch(() => {});
    return () => poller.current && clearInterval(poller.current);
  }, []);

  async function propose() {
    if (!intent.trim()) return;
    setError(null); setPlanning(true); setPlan(null); setJob(null);
    try {
      const p = await api.campaign.plan({
        intent, document_id: docId || null, tier,
      });
      setPlan(p);
    } catch (e) { setError(e.message); }
    finally { setPlanning(false); }
  }

  async function execute() {
    if (!plan?.steps?.length) return;
    // Applique le filtre vidéo côté client si demandé
    const toRun = includeVideo
      ? plan
      : { ...plan, steps: plan.steps.filter((s) => s.type !== "video_storyboard") };
    if (!toRun.steps.length) {
      setError("Aucune étape à exécuter après filtrage.");
      return;
    }
    setError(null); setRunning(true);
    try {
      const j = await api.campaign.run({ campaign: toRun });
      setJob(j);
      poller.current && clearInterval(poller.current);
      poller.current = setInterval(async () => {
        try {
          const upd = await api.campaign.job(j.id);
          setJob(upd);
          if (["succeeded", "failed", "partial"].includes(upd.status)) {
            clearInterval(poller.current);
            setRunning(false);
          }
        } catch { clearInterval(poller.current); setRunning(false); }
      }, 2000);
    } catch (e) { setError(e.message); setRunning(false); }
  }

  function removeStep(i) {
    setPlan({ ...plan, steps: plan.steps.filter((_, k) => k !== i) });
  }

  const nbVideo = plan?.steps?.filter((s) => s.type === "video_storyboard").length || 0;

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>🚀 Super-agent · Campagne complète</h2>
      <p className="muted small-text">
        Une intention → un plan multi-modalités (Reel + posts + stories + thumbnails)
        → tous les livrables produits dans la même charte. Le plan est
        <b> éditable</b> avant exécution (validation humaine, v1.1).
      </p>

      <div className="ds-grid">
        <label className="field">
          <span>Intention</span>
          <textarea rows={2} value={intent} onChange={(e) => setIntent(e.target.value)}
            placeholder="Ex : prépare une campagne complète pour promouvoir ce rapport" />
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
        <div className="tier-toggle">
          <button className={`chip ${tier === "free" ? "active" : ""}`} onClick={() => setTier("free")}>Free</button>
          <button className={`chip ${tier === "premium" ? "active" : ""}`} onClick={() => setTier("premium")}>Premium</button>
        </div>
      </div>

      <button className="ghost" onClick={propose} disabled={planning || !intent.trim()}>
        {planning ? "…" : "🧠 Proposer une campagne"}
      </button>

      {error && <div className="banner error" style={{ marginTop: 10 }}>{error}</div>}

      {plan && (
        <div className="campaign-plan">
          <div className="cp-head">
            <b>{plan.steps.length}</b> étape{plan.steps.length > 1 ? "s" : ""}
            <span className="muted"> · générateur {plan.generator}</span>
            <span className="muted"> · tier {plan.tier}</span>
          </div>

          <ol className="cp-steps">
            {plan.steps.map((s, i) => (
              <li key={i} className={`cp-step k-${s.kind}`}>
                <div className="cps-head">
                  <span className="cps-emoji">{KIND_EMOJI[s.kind]}</span>
                  <div className="cps-title">
                    <b>{s.label}</b>
                    <span className="cps-meta">
                      {TYPE_LABEL[s.type]}
                      {s.template && ` · ${s.template}`}
                      {s.provider && ` · ${s.provider}`}
                      {s.image_format && s.kind === "image" && ` · ${s.image_format}`}
                      {s.video_aspect && s.kind === "video" && ` · ${s.video_aspect} · ${s.duration_seconds}s`}
                    </span>
                  </div>
                  <button className="ghost small" onClick={() => removeStep(i)} title="Retirer">✕</button>
                </div>
                {s.rationale && <div className="cps-rationale">{s.rationale}</div>}
              </li>
            ))}
          </ol>

          {nbVideo > 0 && (
            <label className="checkbox-line" title="Le rendu vidéo prend plusieurs minutes par Reel">
              <input type="checkbox" checked={includeVideo}
                onChange={(e) => setIncludeVideo(e.target.checked)} />
              <span>Inclure les {nbVideo} étape{nbVideo > 1 ? "s" : ""} vidéo
                <span className="muted"> (plusieurs minutes de rendu par Reel)</span>
              </span>
            </label>
          )}

          <button className="primary" onClick={execute}
            disabled={running || !plan.steps.length}>
            {running ? "Exécution…" : `🚀 Lancer la campagne`}
          </button>

          {job && (
            <div className="cp-job">
              <div className="cp-job-head">
                <span className={`badge ${job.status}`}>{job.status}</span>
                <span className="muted">
                  {" "}· {job.steps_completed}/{job.steps_total} étapes
                  {job.errors?.length > 0 && ` · ${job.errors.length} erreur(s)`}
                </span>
              </div>

              {job.deliverables?.length > 0 && (
                <div className="deliv-grid">
                  {job.deliverables.map((d) => (
                    <div key={d.step_index} className={`deliv k-${d.kind}`}>
                      <div className="deliv-thumb">
                        {d.kind === "video" ? (
                          <video src={d.url} controls playsInline muted />
                        ) : (
                          <img src={d.thumbnail_url || d.url} alt={d.label} loading="lazy" />
                        )}
                      </div>
                      <div className="deliv-meta">
                        <b>{KIND_EMOJI[d.kind]} {d.label}</b>
                        <span className="muted">
                          {d.width > 0 ? `${d.width}×${d.height}` : ""}
                          {d.duration_seconds > 0 ? ` · ${Math.round(d.duration_seconds)}s` : ""}
                        </span>
                        <a href={d.url} download className="ghost small">↓ Télécharger</a>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {job.errors?.length > 0 && (
                <details className="cp-errors">
                  <summary>{job.errors.length} erreur(s) partielle(s)</summary>
                  <ul>
                    {job.errors.map((e) => (
                      <li key={e.step_index}>
                        <b>#{e.step_index + 1} {e.step_label}</b> — {e.message}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
