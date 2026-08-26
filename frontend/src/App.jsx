import { useEffect, useRef, useState } from "react";
import { api } from "./lib/api.js";
import PromptForm from "./components/PromptForm.jsx";
import JobCard from "./components/JobCard.jsx";
import IngestFlow from "./components/IngestFlow.jsx";
import AudioToolkit from "./components/AudioToolkit.jsx";
import DesignStudio from "./components/DesignStudio.jsx";

export default function App() {
  const [providers, setProviders] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("pdf");
  const pollers = useRef({});

  useEffect(() => {
    api.providers().then(setProviders).catch((e) => setError(e.message));
    api.jobs().then(setJobs).catch(() => {});
    return () => Object.values(pollers.current).forEach(clearInterval);
  }, []);

  function pollJob(id) {
    if (pollers.current[id]) return;
    pollers.current[id] = setInterval(async () => {
      try {
        const job = await api.job(id);
        setJobs((prev) => prev.map((j) => (j.id === id ? job : j)));
        if (job.status === "succeeded" || job.status === "failed") {
          clearInterval(pollers.current[id]);
          delete pollers.current[id];
        }
      } catch {
        clearInterval(pollers.current[id]);
        delete pollers.current[id];
      }
    }, 2000);
  }

  async function handleGenerate(payload) {
    setError(null);
    try {
      const job = await api.generate(payload);
      setJobs((prev) => [job, ...prev]);
      pollJob(job.id);
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>
          <span className="logo">▶</span> videos-gen
        </h1>
        <p className="tagline">
          Génère des vidéos IA réalistes à partir d'un simple prompt. Multi-providers,
          amélioration automatique du prompt.
        </p>
      </header>

      <nav className="tabs">
        <button className={tab === "pdf" ? "tab active" : "tab"} onClick={() => setTab("pdf")}>
          Depuis un PDF
        </button>
        <button className={tab === "prompt" ? "tab active" : "tab"} onClick={() => setTab("prompt")}>
          Depuis un prompt (b-roll)
        </button>
        <button className={tab === "audio" ? "tab active" : "tab"} onClick={() => setTab("audio")}>
          🎧 Audio toolkit
        </button>
        <button className={tab === "design" ? "tab active" : "tab"} onClick={() => setTab("design")}>
          🎨 Graphic design
        </button>
      </nav>

      {error && <div className="banner error">{error}</div>}

      {tab === "pdf" && <IngestFlow />}
      {tab === "audio" && <AudioToolkit />}
      {tab === "design" && <DesignStudio />}

      {tab === "prompt" && (
        <>
          <PromptForm providers={providers} onGenerate={handleGenerate} />
          <section className="gallery">
            <h2>Générations {jobs.length > 0 && <span className="count">{jobs.length}</span>}</h2>
            {jobs.length === 0 ? (
              <p className="empty">Aucune génération pour l'instant. Lance ton premier prompt ci-dessus.</p>
            ) : (
              <div className="grid">
                {jobs.map((job) => (
                  <JobCard key={job.id} job={job} />
                ))}
              </div>
            )}
          </section>
        </>
      )}

      <footer className="footer">
        Astuce : sans clé API, utilise le provider <strong>Démo</strong> pour tester la
        chaîne. Ajoute une clé <code>FAL_KEY</code> ou <code>REPLICATE_API_TOKEN</code>
        (crédits gratuits) pour du vrai réalisme.
      </footer>
    </div>
  );
}
