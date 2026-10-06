import { useEffect, useRef, useState } from "react";
import { api } from "./lib/api.js";
import Home from "./components/Home.jsx";
import PromptForm from "./components/PromptForm.jsx";
import JobCard from "./components/JobCard.jsx";
import IngestFlow from "./components/IngestFlow.jsx";
import AudioToolkit from "./components/AudioToolkit.jsx";
import DesignStudio from "./components/DesignStudio.jsx";
import CampaignStudio from "./components/CampaignStudio.jsx";
import IdentityStudio from "./components/IdentityStudio.jsx";
import CopyStudio from "./components/CopyStudio.jsx";
import ChatStudio from "./components/ChatStudio.jsx";
import StockStudio from "./components/StockStudio.jsx";

// Navigation groupée : CRÉER (le flux principal) vs OUTILS (appoints).
const NAV = [
  { group: "Créer", items: [
    { id: "home",     label: "Accueil",        icon: "🏠" },
    { id: "chat",     label: "KORA",           icon: "💬" },
    { id: "pdf",      label: "Depuis un PDF",  icon: "📄" },
    { id: "campaign", label: "Campagne 360°",  icon: "🚀" },
  ]},
  { group: "Outils", items: [
    { id: "design",   label: "Graphic design", icon: "🎨" },
    { id: "stock",    label: "Stock",          icon: "🎞️" },
    { id: "audio",    label: "Audio",          icon: "🎧" },
    { id: "copy",     label: "Copywriting",    icon: "✍️" },
    { id: "prompt",   label: "Prompt b-roll",  icon: "⚡" },
  ]},
];

const TITLES = {
  home: "Créer", chat: "KORA", pdf: "Vidéo depuis un PDF", campaign: "Campagne 360°",
  design: "Graphic design", stock: "Stock — médias libres", audio: "Audio toolkit",
  copy: "Copywriting", prompt: "Prompt → b-roll", settings: "Réglages",
};

export default function App() {
  const [view, setView] = useState("home");
  const [seed, setSeed] = useState("");       // amorce passée à la console KORA
  const [role, setRole] = useState(null);
  const [navOpen, setNavOpen] = useState(false);

  // Vue "prompt b-roll" (génération directe)
  const [providers, setProviders] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [error, setError] = useState(null);
  const pollers = useRef({});

  useEffect(() => {
    api.providers().then(setProviders).catch(() => {});
    api.jobs().then(setJobs).catch(() => {});
    return () => Object.values(pollers.current).forEach(clearInterval);
  }, []);

  // Rafraîchit le rôle à chaque navigation (ex: après déblocage admin).
  useEffect(() => { api.identity.me().then((m) => setRole(m.role)).catch(() => {}); }, [view]);

  function go(v, s) {
    setSeed(s || "");
    setView(v);
    setNavOpen(false);
  }

  function pollJob(id) {
    if (pollers.current[id]) return;
    pollers.current[id] = setInterval(async () => {
      try {
        const job = await api.job(id);
        setJobs((prev) => prev.map((j) => (j.id === id ? job : j)));
        if (job.status === "succeeded" || job.status === "failed") {
          clearInterval(pollers.current[id]); delete pollers.current[id];
        }
      } catch { clearInterval(pollers.current[id]); delete pollers.current[id]; }
    }, 2000);
  }
  async function handleGenerate(payload) {
    setError(null);
    try {
      const job = await api.generate(payload);
      setJobs((prev) => [job, ...prev]);
      pollJob(job.id);
    } catch (e) { setError(e.message); }
  }

  return (
    <div className="shell">
      {/* ---------- Top bar ---------- */}
      <header className="topbar">
        <button className="nav-toggle" onClick={() => setNavOpen((o) => !o)} aria-label="Menu">☰</button>
        <button className="brand" onClick={() => go("home")}>
          <span className="logo" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>
          <span className="brand-name">KORA</span>
        </button>
        <div className="topbar-right">
          {role && <span className={`role-badge ${role}`}>{role}</span>}
          <button className={`settings-btn ${view === "settings" ? "active" : ""}`}
            onClick={() => go("settings")} title="Réglages & identité">⚙️</button>
        </div>
      </header>

      <div className="body">
        {/* ---------- Sidebar ---------- */}
        <nav className={`sidebar ${navOpen ? "open" : ""}`}>
          {NAV.map((g) => (
            <div className="nav-group" key={g.group}>
              <p className="nav-group-h">{g.group}</p>
              {g.items.map((it) => (
                <button key={it.id} className={`nav-item ${view === it.id ? "active" : ""}`}
                  onClick={() => go(it.id)}>
                  <span className="nav-ic" aria-hidden="true">{it.icon}</span>{it.label}
                </button>
              ))}
            </div>
          ))}
        </nav>
        {navOpen && <div className="scrim" onClick={() => setNavOpen(false)} />}

        {/* ---------- Contenu ---------- */}
        <main className="content">
          <div className="content-head">
            <h2>{TITLES[view]}</h2>
            {view !== "home" && (
              <button className="back-link" onClick={() => go("home")}>← Accueil</button>
            )}
          </div>

          {error && view === "prompt" && <div className="banner error">{error}</div>}

          {view === "home" && <Home onPick={go} />}
          {view === "chat" && <ChatStudio seed={seed} />}
          {view === "pdf" && <IngestFlow />}
          {view === "campaign" && <CampaignStudio />}
          {view === "design" && <DesignStudio />}
          {view === "stock" && <StockStudio />}
          {view === "audio" && <AudioToolkit />}
          {view === "copy" && <CopyStudio />}
          {view === "settings" && <IdentityStudio />}

          {view === "prompt" && (
            <>
              <PromptForm providers={providers} onGenerate={handleGenerate} />
              <section className="gallery">
                <h3>Générations {jobs.length > 0 && <span className="count">{jobs.length}</span>}</h3>
                {jobs.length === 0 ? (
                  <p className="empty">Aucune génération. Lance ton premier prompt ci-dessus.</p>
                ) : (
                  <div className="grid">{jobs.map((job) => <JobCard key={job.id} job={job} />)}</div>
                )}
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
