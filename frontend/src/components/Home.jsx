import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

// Accueil « Créer » — un point d'entrée unique. Tu choisis CE QUE tu veux créer,
// pas un onglet technique. Inspiré de la simplicité Fooocus.
const MODES = [
  { id: "pdf",      view: "pdf",      icon: "📄", accent: "g1",
    title: "Vidéo depuis un PDF",
    desc: "Transforme un document ou une BD en vidéo animée. Le plus abouti." },
  { id: "chat",     view: "chat",     icon: "💬", accent: "g3",
    title: "Décrire à KORA",
    desc: "Explique en une phrase ce que tu veux — KORA s'occupe du reste." },
  { id: "campaign", view: "campaign", icon: "🚀", accent: "g1",
    title: "Campagne 360°",
    desc: "Un brief → vidéo + affiche + textes, d'un seul coup." },
  { id: "poster",   view: "design",   icon: "🖼️", accent: "g4",
    title: "Affiche / visuel",
    desc: "Crée une affiche ou un visuel réseaux prêt à publier." },
  { id: "copy",     view: "copy",     icon: "✍️", accent: "g2",
    title: "Copywriting",
    desc: "Accroches, légendes et hashtags, par plateforme." },
  { id: "stock",    view: "stock",    icon: "🎞️", accent: "g5",
    title: "Trouver du stock",
    desc: "Photos et vidéos libres de droits pour ton b-roll." },
];

export default function Home({ onPick }) {
  const [presets, setPresets] = useState([]);
  useEffect(() => { api.presets().then(setPresets).catch(() => {}); }, []);

  return (
    <div className="home">
      <div className="home-hero">
        <h1>Que veux-tu créer&nbsp;?</h1>
        <p>Choisis un objectif. Tu pourras tout ajuster ensuite.</p>
      </div>

      <div className="mode-grid">
        {MODES.map((m) => (
          <button key={m.id} className={`mode-card ${m.accent}`} onClick={() => onPick(m.view)}>
            <span className="mode-ic" aria-hidden="true">{m.icon}</span>
            <span className="mode-title">{m.title}</span>
            <span className="mode-desc">{m.desc}</span>
            <span className="mode-go">Commencer →</span>
          </button>
        ))}
      </div>

      {presets.length > 0 && (
        <div className="home-presets">
          <p className="home-presets-h">Ou pars d'un format tout prêt :</p>
          <div className="preset-grid">
            {presets.map((p) => (
              <button key={p.id} className={`preset-card ${p.accent}`} title={p.description}
                onClick={() => onPick("chat", p.prompt)}>
                <span className="preset-ic" aria-hidden="true">{p.icon}</span>
                <span className="preset-label">{p.label}</span>
                <span className="preset-desc">{p.description}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
