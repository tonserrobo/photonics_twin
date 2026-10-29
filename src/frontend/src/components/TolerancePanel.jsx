import { useState } from "react";

const DEFAULTS = { n_samples: 50, thickness_sigma_nm: 2.0, tolerance_nm: 2.0 };

export default function TolerancePanel({ params, sweep }) {
  const [settings, setSettings] = useState(DEFAULTS);
  const [stats, setStats] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  const update = (next) => setSettings((current) => ({ ...current, ...next }));

  const run = async () => {
    setStatus("running");
    setError("");
    setStats(null);
    try {
      const response = await fetch("/simulate/tmm/tolerance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          component: "bragg_grating",
          params,
          sweep,
          n_samples: settings.n_samples,
          thickness_sigma_nm: settings.thickness_sigma_nm,
          tolerance_nm: settings.tolerance_nm,
          seed: 12345,
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setStats(data.meta?.tolerance ?? null);
      setStatus("done");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  };

  const yieldText = stats?.yield == null
    ? "n/a"
    : `${(stats.yield * 100).toFixed(0)}%`;

  return (
    <div className="tolerance">
      <h3>Fabrication tolerance</h3>
      <div className="tolerance-controls">
        <label>sigma (nm)
          <input type="number" min="0" max="50" step="0.5"
                 value={settings.thickness_sigma_nm}
                 onChange={(e) => update({ thickness_sigma_nm: Number(e.target.value) })} />
        </label>
        <label>target (nm)
          <input type="number" min="0.1" max="50" step="0.5"
                 value={settings.tolerance_nm}
                 onChange={(e) => update({ tolerance_nm: Number(e.target.value) })} />
        </label>
        <label>samples
          <input type="number" min="10" max="200" step="10"
                 value={settings.n_samples}
                 onChange={(e) => update({ n_samples: Number(e.target.value) })} />
        </label>
        <button type="button" onClick={run} disabled={status === "running"}>
          {status === "running" ? "Running..." : "Run tolerance"}
        </button>
      </div>
      {status === "error" && (
        <div className="tolerance-error">Tolerance failed: {error}</div>
      )}
      {stats && (
        <div className="tolerance-result">
          <strong>Yield {yieldText}</strong>
          {` (${stats.n_samples} samples, ${stats.tolerance_nm} nm target)`}
          <br />
          {`centre std ${stats.std_centre_nm?.toFixed(2) ?? "n/a"} nm`}
          {` | P5 ${stats.p05_centre_nm?.toFixed(2) ?? "n/a"} nm`}
          {` | P95 ${stats.p95_centre_nm?.toFixed(2) ?? "n/a"} nm`}
          {` | failed ${stats.failed_samples}`}
        </div>
      )}
    </div>
  );
}
