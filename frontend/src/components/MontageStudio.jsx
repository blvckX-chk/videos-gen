import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";
import MediaLibrary from "./MediaLibrary.jsx";

const FORMATS = [
  { id: "9:16", label: "Vertical", hint: "TikTok · Reels" },
  { id: "1:1", label: "Carré", hint: "Feed" },
  { id: "16:9", label: "Paysage", hint: "YouTube" },
];

const newTimeline = () => ({
  name: "Montage",
  format: "9:16",
  fps: 30,
  fit_mode: "blur",              // image entiere sur fond floute
  transition_style: "dissolve",  // fondus enchaînés entre les plans
  clips: [],
  music_media_id: null,
  narration: "",
});

export default function MontageStudio() {
  const [tl, setTl] = useState(newTimeline);
  const [media, setMedia] = useState([]);
  const [picking, setPicking] = useState(false);
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [perPhoto, setPerPhoto] = useState(2.5);   // durée par photo (albums)
  const [theme, setTheme] = useState("");
  const [curation, setCuration] = useState(null);  // {engine, rationale, rejected}
  const [sorting, setSorting] = useState(false);
  const [role, setRole] = useState(null);
  const [noWatermark, setNoWatermark] = useState(false);
  const poller = useRef(null);

  useEffect(() => {
    api.media.list().then(setMedia).catch(() => {});
    api.identity.me().then((m) => setRole(m.role)).catch(() => {});
    return () => clearInterval(poller.current);
  }, []);

  const byId = (id) => media.find((m) => m.id === id);
  const visual = media.filter((m) => m.kind !== "audio");
  const audio = media.filter((m) => m.kind === "audio");
  const total = tl.clips.reduce((s, c) => s + (Number(c.duration) || 0), 0);

  // ---- édition des plans ----
  function addClip(m) {
    const isVideo = m.kind === "video";
    setTl((t) => ({
      ...t,
      clips: [...t.clips, {
        media_id: m.id,
        in_point: 0,
        duration: isVideo ? Math.min(4, Math.max(1, Math.round(m.duration || 4))) : 3,
        transition: t.clips.length === 0 ? "cut" : "fade",
        ken_burns: !isVideo,
        text: null,
      }],
    }));
    setPicking(false);
  }
  const patchClip = (i, patch) =>
    setTl((t) => ({ ...t, clips: t.clips.map((c, k) => (k === i ? { ...c, ...patch } : c)) }));
  const removeClip = (i) =>
    setTl((t) => ({ ...t, clips: t.clips.filter((_, k) => k !== i) }));
  function moveClip(i, dir) {
    const j = i + dir;
    setTl((t) => {
      if (j < 0 || j >= t.clips.length) return t;
      const clips = [...t.clips];
      [clips[i], clips[j]] = [clips[j], clips[i]];
      return { ...t, clips };
    });
  }

  // Proposition de départ : tous les visuels dans l'ordre d'import (ordre de
  // l'album), et non du plus récent au plus ancien comme la médiathèque.
  function proposeFromLibrary() {
    if (!visual.length) { setError("Importe d'abord des médias dans la médiathèque."); return; }
    setError(null);
    const chrono = [...visual].sort(
      (a, b) => new Date(a.created_at) - new Date(b.created_at));
    setTl((t) => ({
      ...t,
      clips: chrono.map((m) => ({
        media_id: m.id,
        in_point: 0,
        duration: m.kind === "video"
          ? Math.min(5, Math.max(1, Math.round(m.duration || 4)))
          : perPhoto,
        transition: "cut",
        ken_burns: m.kind !== "video",
        text: null,
      })),
    }));
  }

  // Chaîne complète : tri déterministe (flou, doublons…) puis scénario.
  async function sortAndPropose() {
    setError(null); setSorting(true); setCuration(null);
    try {
      const sc = await api.curation.scenario({
        theme: theme || null, per_photo: perPhoto,
      });
      if (!sc.clips.length) {
        setError(sc.rationale || "Aucune photo exploitable.");
      } else {
        setTl((t) => ({
          ...t,
          name: sc.title || t.name,
          clips: sc.clips.map((c) => ({
            media_id: c.media_id,
            in_point: 0,
            duration: c.duration,
            transition: "cut",
            ken_burns: c.ken_burns,
            text: c.text || null,
          })),
        }));
      }
      setCuration({ engine: sc.engine, rationale: sc.rationale, rejected: sc.rejected });
    } catch (e) { setError(e.message); }
    finally { setSorting(false); }
  }

  // Régler la durée de toutes les photos d'un coup (un album en compte beaucoup).
  function applyPhotoDuration(v) {
    setPerPhoto(v);
    setTl((t) => ({
      ...t,
      clips: t.clips.map((c) => {
        const m = media.find((x) => x.id === c.media_id);
        return m && m.kind !== "video" ? { ...c, duration: v } : c;
      }),
    }));
  }

  // ---- rendu ----
  async function render() {
    if (!tl.clips.length) { setError("Ajoute au moins un plan."); return; }
    setError(null); setBusy(true); setJob(null);
    try {
      const payload = {
        timeline: { ...tl, narration: tl.narration || null },
        remove_watermark: noWatermark,
      };
      const j = await api.montage.render(payload);
      setJob(j);
      poller.current = setInterval(async () => {
        try {
          const up = await api.montage.job(j.id);
          setJob(up);
          if (up.status === "succeeded" || up.status === "failed") {
            clearInterval(poller.current); setBusy(false);
          }
        } catch { clearInterval(poller.current); setBusy(false); }
      }, 1500);
    } catch (e) { setError(e.message); setBusy(false); }
  }

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>✂️ Montage vidéo</h2>
      <p className="muted small-text">
        Assemble tes <strong>rushes</strong> et tes <strong>photos produit</strong> en une
        vidéo. KORA propose, tu ajustes chaque plan, puis tu rends.
      </p>

      {/* ----- Réglages généraux ----- */}
      <div className="mt-row">
        <label className="field small">
          <span>Nom</span>
          <input type="text" value={tl.name}
            onChange={(e) => setTl({ ...tl, name: e.target.value })} />
        </label>
        <div className="field small">
          <span>Format</span>
          <div className="seg">
            {FORMATS.map((f) => (
              <button key={f.id} type="button" title={f.hint}
                className={tl.format === f.id ? "on" : ""}
                onClick={() => setTl({ ...tl, format: f.id })}>{f.label}</button>
            ))}
          </div>
        </div>
        <div className="field small">
          <span>Enchaînements</span>
          <div className="seg">
            <button type="button" className={tl.transition_style === "varied" ? "on" : ""}
              title="Alterne fondus, glissements, volets — évite la monotonie"
              onClick={() => setTl({ ...tl, transition_style: "varied" })}>Variées</button>
            <button type="button" className={tl.transition_style === "dissolve" ? "on" : ""}
              title="Uniquement des fondus enchaînés"
              onClick={() => setTl({ ...tl, transition_style: "dissolve" })}>Fondu</button>
            <button type="button" className={tl.transition_style === "cut" ? "on" : ""}
              title="Coupes franches (rendu plus rapide)"
              onClick={() => setTl({ ...tl, transition_style: "cut" })}>Coupe</button>
          </div>
        </div>
        <div className="field small">
          <span>Cadrage</span>
          <div className="seg">
            <button type="button" className={tl.fit_mode === "blur" ? "on" : ""}
              title="Image entière sur fond flouté — rien n'est coupé, pas de bandes noires"
              onClick={() => setTl({ ...tl, fit_mode: "blur" })}>Fond flouté</button>
            <button type="button" className={tl.fit_mode === "cover" ? "on" : ""}
              title="Remplit le cadre en recadrant, centré sur les visages"
              onClick={() => setTl({ ...tl, fit_mode: "cover" })}>Remplir</button>
            <button type="button" className={tl.fit_mode === "contain" ? "on" : ""}
              title="Conserve toute l'image, ajoute des bandes noires"
              onClick={() => setTl({ ...tl, fit_mode: "contain" })}>Bandes</button>
          </div>
        </div>
      </div>
      <p className="muted small-text" style={{ marginTop: -4 }}>
        Le son de tes rushes est conservé et mixé avec la musique et la voix off,
        puis normalisé au niveau des plateformes (−14 LUFS).
      </p>

      {/* ----- Plans ----- */}
      <div className="mt-head">
        <h3>Plans <span className="count">{tl.clips.length}</span></h3>
        <span className="mt-total">durée totale <b>{total.toFixed(1)}s</b></span>
      </div>

      <div className="mt-actions">
        <button className="ghost" onClick={() => setPicking((p) => !p)}>
          {picking ? "Fermer" : "＋ Ajouter un plan"}
        </button>
        <button className="ghost" onClick={proposeFromLibrary}>
          ✨ Proposer un montage ({visual.length} média{visual.length > 1 ? "s" : ""})
        </button>
        <button className="primary" onClick={sortAndPropose} disabled={sorting}>
          {sorting ? "Tri en cours…" : "🧠 Trier et proposer un scénario"}
        </button>
        <label className="field small inline">
          <span>Thème</span>
          <input type="text" value={theme} style={{ width: 170 }}
            placeholder="récap de bootcamp"
            onChange={(e) => setTheme(e.target.value)} />
        </label>
        <label className="field small inline">
          <span>Durée par photo</span>
          <input type="number" min="0.5" max="15" step="0.5" value={perPhoto}
            onChange={(e) => applyPhotoDuration(Number(e.target.value))} />
        </label>
      </div>

      {curation && (
        <div className="curation-note">
          <p>
            <span className={`badge ${curation.engine === "tchavi" ? "succeeded" : ""}`}>
              {curation.engine === "tchavi" ? "curation IA" : "tri automatique"}
            </span>{" "}
            {curation.rationale}
          </p>
          {curation.rejected?.length > 0 && (
            <details>
              <summary>{curation.rejected.length} photo(s) écartée(s)</summary>
              <ul className="rejected-list">
                {curation.rejected.map((r) => (
                  <li key={r.media_id}>
                    {(media.find((m) => m.id === r.media_id)?.name) || r.media_id}
                    {" — "}{r.issues.join(", ") || "qualité insuffisante"}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {picking && (
        <div className="mt-picker">
          <p className="muted small-text">Choisis un média (photo ou vidéo) :</p>
          <MediaLibrary pickable kindFilter="visual" onPick={addClip} />
        </div>
      )}

      {tl.clips.length === 0 ? (
        <p className="empty">
          Aucun plan. Clique « Proposer un montage » pour partir de ta médiathèque,
          ou ajoute les plans un par un.
        </p>
      ) : (
        <ol className="clip-list">
          {tl.clips.map((c, i) => {
            const m = byId(c.media_id);
            return (
              <li key={`${c.media_id}-${i}`} className="clip-card">
                <span className="clip-num">{i + 1}</span>
                <div className="clip-thumb"
                  style={m?.thumb_url ? { backgroundImage: `url(${m.thumb_url})` } : undefined} />
                <div className="clip-body">
                  <span className="clip-name">{m?.name || "média supprimé"}</span>
                  <div className="clip-controls">
                    <label>durée
                      <input type="number" min="0.5" max="60" step="0.5" value={c.duration}
                        onChange={(e) => patchClip(i, { duration: Number(e.target.value) })} />
                      s
                    </label>
                    {m?.kind === "video" && (
                      <label>début à
                        <input type="number" min="0" step="0.5" value={c.in_point}
                          onChange={(e) => patchClip(i, { in_point: Number(e.target.value) })} />
                        s
                      </label>
                    )}
                    {m?.kind === "photo" && (
                      <label className="clip-check">
                        <input type="checkbox" checked={c.ken_burns}
                          onChange={(e) => patchClip(i, { ken_burns: e.target.checked })} />
                        zoom lent
                      </label>
                    )}
                    {i === 0 && (
                      <label className="clip-check" title="Ouvrir la vidéo en fondu depuis le noir">
                        <input type="checkbox" checked={c.transition === "fade"}
                          onChange={(e) => patchClip(i, { transition: e.target.checked ? "fade" : "cut" })} />
                        ouvrir en fondu
                      </label>
                    )}
                  </div>
                  <input className="clip-text" type="text" value={c.text || ""}
                    placeholder="Titre incrusté sur ce plan (optionnel)"
                    onChange={(e) => patchClip(i, { text: e.target.value || null })} />
                </div>
                <div className="clip-ops">
                  <button className="ghost small" onClick={() => moveClip(i, -1)} disabled={i === 0} title="Monter">↑</button>
                  <button className="ghost small" onClick={() => moveClip(i, 1)} disabled={i === tl.clips.length - 1} title="Descendre">↓</button>
                  <button className="ghost small" onClick={() => removeClip(i)} title="Retirer">✕</button>
                </div>
              </li>
            );
          })}
        </ol>
      )}

      {/* ----- Son ----- */}
      <div className="mt-row" style={{ marginTop: 16 }}>
        <label className="field small">
          <span>Musique de fond</span>
          <select value={tl.music_media_id || ""}
            onChange={(e) => setTl({ ...tl, music_media_id: e.target.value || null })}>
            <option value="">— aucune —</option>
            {audio.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        </label>
      </div>
      <label className="field small">
        <span>Voix off (laisse vide pour aucune)</span>
        <textarea rows={2} value={tl.narration}
          onChange={(e) => setTl({ ...tl, narration: e.target.value })}
          placeholder="Texte lu par la voix de synthèse…" />
      </label>

      {error && <div className="banner error" style={{ marginTop: 12 }}>{error}</div>}

      {(role === "admin" || role === "premium") && (
        <label className="clip-check" style={{ marginTop: 10 }}>
          <input type="checkbox" checked={noWatermark}
            onChange={(e) => setNoWatermark(e.target.checked)} />
          Retirer le filigrane blvckUnlimited
        </label>
      )}

      <button className="primary" onClick={render} disabled={busy || !tl.clips.length}
        style={{ marginTop: 14 }}>
        {busy ? "Montage en cours…" : "🎬 Monter la vidéo"}
      </button>

      {/* ----- Suivi du job ----- */}
      {job && (
        <div className="mt-job">
          <div className="mt-job-head">
            <span className={`badge ${job.status}`}>{job.status}</span>
            <span className="muted small-text">{job.step}</span>
            {job.clips_total > 0 && job.status === "running" && (
              <span className="muted small-text">
                {job.clips_done}/{job.clips_total} plans
              </span>
            )}
          </div>
          {job.error && <div className="banner error">{job.error}</div>}
          {job.video_url && (
            <>
              <video className="mt-preview" src={job.video_url} controls playsInline />
              <a className="ghost small" href={job.video_url} download>⬇ Télécharger</a>
            </>
          )}
        </div>
      )}
    </div>
  );
}
