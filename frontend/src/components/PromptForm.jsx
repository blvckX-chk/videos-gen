import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

const RATIOS = ["16:9", "9:16", "1:1"];

export default function PromptForm({ providers, onGenerate }) {
  const [prompt, setPrompt] = useState("");
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [enhance, setEnhance] = useState(true);
  const [duration, setDuration] = useState(5);
  const [aspect, setAspect] = useState("16:9");
  const [preview, setPreview] = useState("");
  const [enhancing, setEnhancing] = useState(false);

  // Sélectionne par défaut le premier provider disponible.
  useEffect(() => {
    if (!provider && providers.length) {
      const first = providers.find((p) => p.available) || providers[0];
      setProvider(first.id);
    }
  }, [providers, provider]);

  const current = providers.find((p) => p.id === provider);

  useEffect(() => {
    setModel(current?.models?.[0] || "");
  }, [provider]); // eslint-disable-line

  async function handlePreview() {
    if (!prompt.trim()) return;
    setEnhancing(true);
    try {
      const { enhanced_prompt } = await api.enhance(prompt);
      setPreview(enhanced_prompt);
    } finally {
      setEnhancing(false);
    }
  }

  function submit(e) {
    e.preventDefault();
    if (!prompt.trim() || !provider) return;
    onGenerate({
      prompt,
      provider,
      model: model || null,
      enhance,
      duration: Number(duration),
      aspect_ratio: aspect,
    });
  }

  return (
    <form className="card form" onSubmit={submit}>
      <label className="field">
        <span>Prompt</span>
        <textarea
          rows={3}
          placeholder="Ex : un renard roux traverse une forêt enneigée au lever du soleil"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
      </label>

      <div className="row">
        <label className="field">
          <span>Provider</span>
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            {providers.map((p) => (
              <option key={p.id} value={p.id} disabled={!p.available}>
                {p.name} {p.available ? (p.free ? "· gratuit" : "") : "· clé manquante"}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Modèle</span>
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            {(current?.models || []).map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="row">
        <label className="field small">
          <span>Ratio</span>
          <select value={aspect} onChange={(e) => setAspect(e.target.value)}>
            {RATIOS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>

        <label className="field small">
          <span>Durée (s) : {duration}</span>
          <input
            type="range"
            min={1}
            max={15}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
        </label>

        <label className="field checkbox">
          <input type="checkbox" checked={enhance} onChange={(e) => setEnhance(e.target.checked)} />
          <span>Améliorer le prompt (réalisme)</span>
        </label>
      </div>

      {current && !current.available && current.requires_key && (
        <p className="hint warn">
          Ce provider nécessite la clé <code>{current.requires_key}</code> dans le
          <code>.env</code> du backend.
        </p>
      )}

      <div className="actions">
        <button type="button" className="ghost" onClick={handlePreview} disabled={enhancing || !prompt.trim()}>
          {enhancing ? "…" : "Prévisualiser le prompt amélioré"}
        </button>
        <button type="submit" className="primary" disabled={!prompt.trim() || !provider}>
          Générer la vidéo
        </button>
      </div>

      {preview && (
        <div className="preview">
          <span className="preview-label">Prompt envoyé au modèle :</span>
          <p>{preview}</p>
        </div>
      )}
    </form>
  );
}
