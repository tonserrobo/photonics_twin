import { useRef, useState } from "react";
import { parseScenario, toCsv, toResultJson, toScenarioJson } from "../lib/scenario.js";

function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

const stamp = () => new Date().toISOString().replace(/[:.]/g, "-");

export default function ScenarioControls({ params, sweep, result, onLoad }) {
  const fileRef = useRef(null);
  const [message, setMessage] = useState("");

  const exportCsv = () => {
    if (!result) return;
    download(`bragg-spectrum-${stamp()}.csv`,
             toCsv(result.wavelengths_nm, result.reflectance),
             "text/csv");
  };

  const exportJson = () => {
    if (!result) return;
    download(`bragg-result-${stamp()}.json`,
             toResultJson(params, sweep, result),
             "application/json");
  };

  const saveScenario = () => {
    download(`bragg-scenario-${stamp()}.json`,
             toScenarioJson(params, sweep),
             "application/json");
  };

  const loadScenario = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const next = parseScenario(await file.text());
      onLoad(next.params, next.sweep);
      setMessage(`Loaded ${file.name}`);
    } catch (err) {
      setMessage(`Load failed: ${err.message}`);
    } finally {
      event.target.value = "";
    }
  };

  return (
    <div className="actions">
      <button type="button" onClick={exportCsv} disabled={!result}>
        Export CSV
      </button>
      <button type="button" onClick={exportJson} disabled={!result}>
        Export JSON
      </button>
      <button type="button" onClick={saveScenario}>
        Save scenario
      </button>
      <button type="button" onClick={() => fileRef.current?.click()}>
        Load scenario
      </button>
      <input ref={fileRef} type="file" accept="application/json,.json"
             onChange={loadScenario} hidden />
      {message && <span className="action-message">{message}</span>}
    </div>
  );
}
