const STATUS_LABELS = {
  queued: "En file",
  enhancing: "Amélioration du prompt…",
  running: "Génération en cours…",
  succeeded: "Terminé",
  failed: "Échec",
};

export default function JobCard({ job }) {
  const busy = ["queued", "enhancing", "running"].includes(job.status);
  return (
    <div className={`card job status-${job.status}`}>
      <div className="job-head">
        <span className={`badge ${job.status}`}>{STATUS_LABELS[job.status] || job.status}</span>
        <span className="job-provider">{job.provider}</span>
      </div>

      <p className="job-prompt">{job.prompt}</p>

      {busy && (
        <div className="progress">
          <div className="progress-bar" />
        </div>
      )}

      {job.status === "succeeded" && job.video_url && (
        <video className="job-video" src={job.video_url} controls loop muted playsInline />
      )}

      {job.status === "failed" && <p className="job-error">{job.error}</p>}

      {job.enhanced_prompt && job.enhanced_prompt !== job.prompt && (
        <details className="job-enhanced">
          <summary>Prompt amélioré</summary>
          <p>{job.enhanced_prompt}</p>
        </details>
      )}
    </div>
  );
}
