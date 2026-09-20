import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";

// Rendu d'un résultat KORA selon son type.
function ResultBlock({ result, onRunCampaign }) {
  const [img, setImg] = useState(null);

  // image_job : on poll le job design jusqu'à obtenir l'asset
  useEffect(() => {
    if (result?.type !== "image_job" || !result.data?.job_id) return;
    let stop = false;
    const t = setInterval(async () => {
      try {
        const j = await api.design.job(result.data.job_id);
        if (j.status === "succeeded" && j.output_asset_ids?.length) {
          const a = await api.design.asset(j.output_asset_ids[0]);
          if (!stop) { setImg(a); clearInterval(t); }
        } else if (j.status === "failed") { clearInterval(t); }
      } catch { clearInterval(t); }
    }, 2000);
    return () => { stop = true; clearInterval(t); };
  }, [result]);

  if (!result) return null;
  if (result.type === "image")
    return <img className="chat-img" src={result.data.url} alt="résultat" />;
  if (result.type === "image_job")
    return img ? <img className="chat-img" src={img.url} alt="généré" />
               : <div className="chat-loading">Génération en cours…</div>;
  if (result.type === "copy")
    return (
      <div className="chat-copy">
        {result.data.platforms.map((pc) => (
          <div key={pc.platform} className="chat-copy-plat">
            <b>{pc.platform}</b>
            {pc.variants.map((v) => (
              <div key={v.label} className="chat-copy-var">
                <span className="cv-hook">{v.hook}</span>
                <span className="cv-body">{v.body}</span>
                <span className="cv-cta">{v.cta} {(v.hashtags || []).join(" ")}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  if (result.type === "campaign_plan") {
    const plan = result.data;
    return (
      <div className="chat-plan">
        <ol>
          {plan.steps.map((s, i) => (
            <li key={i}><b>{s.label}</b> <span className="muted">· {s.type}</span></li>
          ))}
        </ol>
        <button className="primary" onClick={() => onRunCampaign(plan)}>🚀 Lancer la campagne</button>
      </div>
    );
  }
  return null;
}

// Onglet 💬 KORA — console conversationnelle (hybride : gratuit + LLM si clé).
export default function ChatStudio() {
  const [messages, setMessages] = useState([
    { role: "kora", text: "Salut 👋 Je suis KORA. Dis-moi ce que tu veux créer — une campagne, du copy, une carte, une affiche…" },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [docId, setDocId] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    fetch("/api/documents").then((r) => r.json()).then(setDocuments).catch(() => {});
  }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "me", text }]);
    setBusy(true);
    try {
      const r = await api.chat(text, { document_id: docId || null });
      setMessages((m) => [...m, { role: "kora", text: r.reply, result: r.result, engine: r.engine }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "kora", text: "Erreur : " + e.message }]);
    } finally { setBusy(false); }
  }

  async function runCampaign(plan) {
    setMessages((m) => [...m, { role: "kora", text: "Je lance la campagne… (suis l'avancement dans l'onglet Campagne)" }]);
    try { await api.campaign.run({ campaign: plan }); }
    catch (e) { setMessages((m) => [...m, { role: "kora", text: "Erreur au lancement : " + e.message }]); }
  }

  return (
    <div className="card chat-card">
      <h2 style={{ marginTop: 0 }}>💬 KORA</h2>
      <div className="chat-context">
        <label className="field small">
          <span>Document lié (option)</span>
          <select value={docId} onChange={(e) => setDocId(e.target.value)}>
            <option value="">— aucun —</option>
            {documents.map((d) => <option key={d.id} value={d.id}>{d.title_guess || d.filename}</option>)}
          </select>
        </label>
      </div>

      <div className="chat-log">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            <div className="chat-bubble">
              <div className="chat-text">{m.text}</div>
              {m.result && <ResultBlock result={m.result} onRunCampaign={runCampaign} />}
            </div>
          </div>
        ))}
        {busy && <div className="chat-msg kora"><div className="chat-bubble"><div className="chat-loading">KORA réfléchit…</div></div></div>}
        <div ref={endRef} />
      </div>

      <div className="chat-input">
        <textarea rows={2} value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
          placeholder="Ex : prépare une campagne pour promouvoir mon restaurant…" />
        <button className="primary" onClick={send} disabled={busy || !input.trim()}>Envoyer</button>
      </div>
    </div>
  );
}
