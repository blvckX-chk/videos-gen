import { useRef, useState } from "react";
import { api } from "../lib/api.js";
import PanelViewer from "./PanelViewer.jsx";

const TYPE_LABELS = {
  report: "Rapport",
  slides: "Présentation",
  scientific: "Article scientifique",
  comic: "BD / Manga",
  mixed: "Indéterminé",
};

const TYPE_EMOJI = {
  report: "📄",
  slides: "📊",
  scientific: "🔬",
  comic: "💥",
  mixed: "📁",
};

export default function IngestFlow() {
  const [doc, setDoc] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fileRef = useRef();

  async function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    reset();
    setLoading(true);
    try {
      const res = await api.ingest(file);
      setDoc(res.document);
      setQuestions(res.questions);
      // Pré-remplit avec les réponses par défaut.
      const defaults = {};
      res.questions.forEach((q) => {
        defaults[q.id] = q.default || (q.options?.[0] ?? "");
      });
      setAnswers(defaults);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setDoc(null);
    setQuestions([]);
    setAnswers({});
    setBrief(null);
    setError(null);
  }

  async function submitBrief() {
    setError(null);
    try {
      const b = await api.brief(doc.id, answers);
      setBrief(b);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="card">
      <h2 className="ingest-title">1 · Ingestion & clarification</h2>
      <p className="muted small-text">
        Dépose un PDF (rapport, présentation, article, ou <strong>BD/manga</strong>). Le
        système détecte le type et pose les bonnes questions pour cadrer la vidéo.
      </p>

      <button className="ghost" onClick={() => fileRef.current?.click()} disabled={loading}>
        {loading ? "Analyse…" : doc ? "Choisir un autre PDF" : "📎 Déposer un PDF"}
      </button>
      <input
        ref={fileRef}
        type="file"
        accept="application/pdf"
        onChange={handleFile}
        style={{ display: "none" }}
      />

      {error && <div className="banner error" style={{ marginTop: 16 }}>{error}</div>}

      {doc && (
        <div className="doc-summary">
          <div className="doc-type">
            <span className="doc-emoji">{TYPE_EMOJI[doc.doc_type]}</span>
            <div>
              <strong>{TYPE_LABELS[doc.doc_type] || doc.doc_type}</strong>
              <span className="conf">confiance {Math.round(doc.doc_type_confidence * 100)}%</span>
            </div>
          </div>
          <ul className="doc-stats">
            <li><b>{doc.page_count}</b> pages</li>
            <li><b>{doc.total_words}</b> mots</li>
            <li><b>{doc.total_images}</b> images</li>
            <li>couverture image <b>{Math.round(doc.avg_image_area_ratio * 100)}%</b></li>
            {doc.language_guess && <li>langue <b>{doc.language_guess}</b></li>}
          </ul>
          {doc.title_guess && <p className="doc-title">« {doc.title_guess} »</p>}
        </div>
      )}

      {doc && (
        <details className="panels-wrap" open={doc.doc_type === "comic"}>
          <summary>
            {doc.doc_type === "comic"
              ? "💥 BD détectée — segmenter les cases"
              : "C'est une BD ? Détecter les cases"}
          </summary>
          <PanelViewer documentId={doc.id} />
        </details>
      )}

      {questions.length > 0 && !brief && (
        <div className="clarify">
          <h3>Clarifions le contexte</h3>
          {questions.map((q) => (
            <div key={q.id} className="q">
              <label>{q.question}</label>
              <div className="options">
                {(q.options || []).map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    className={`chip ${answers[q.id] === opt ? "active" : ""}`}
                    onClick={() => setAnswers((a) => ({ ...a, [q.id]: opt }))}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>
          ))}
          <button className="primary" onClick={submitBrief} style={{ marginTop: 8 }}>
            Valider le brief
          </button>
        </div>
      )}

      {brief && (
        <div className="brief">
          <h3>✅ Brief prêt</h3>
          <p className="muted small-text">
            C'est le contrat qui pilotera le storyboard et le rendu (Slice 2).
          </p>
          <div className="brief-grid">
            <div><span>Type</span>{brief.doc_type}</div>
            <div><span>Objectif</span>{brief.objective || "—"}</div>
            <div><span>Audience</span>{brief.audience || "—"}</div>
            <div><span>Ton</span>{brief.tone || "—"}</div>
            <div><span>Durée</span>{brief.duration_seconds}s</div>
            <div><span>Langue</span>{brief.language}</div>
            {brief.doc_type === "comic" && (
              <>
                <div><span>Voix perso.</span>{brief.character_voices ? "oui" : "non"}</div>
                <div><span>Bruitages</span>{brief.sound_effects ? "oui" : "non"}</div>
              </>
            )}
          </div>
          <details className="raw">
            <summary>Brief JSON</summary>
            <pre>{JSON.stringify(brief, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
