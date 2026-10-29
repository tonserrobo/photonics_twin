import { useState } from "react";
import { useSimulation } from "./hooks/useSimulation.js";
import ParameterPanel from "./components/ParameterPanel.jsx";
import ScenarioControls from "./components/ScenarioControls.jsx";
import SpectralPlot from "./components/SpectralPlot.jsx";
import LayerStackView from "./components/LayerStackView.jsx";

const INITIAL_PARAMS = { material_high: "Si", material_low: "SiO2",
                          centre_nm: 1550.0, periods: 15,
                          temperature_c: 20.0, strain_microstrain: 0.0 };
const INITIAL_SWEEP  = { start_nm: 1400.0, stop_nm: 1700.0, n_points: 501 };

export default function App() {
  const [params, setParams] = useState(INITIAL_PARAMS);
  const [sweep,  setSweep]  = useState(INITIAL_SWEEP);
  const onChange = (p, s) => { setParams(p); setSweep(s); };

  const { result, status, error } = useSimulation(params, sweep);

  return (
    <div className="container">
      <div className="left">
        <ParameterPanel params={params} sweep={sweep} onChange={onChange} />
        <ScenarioControls params={params} sweep={sweep} result={result}
                          onLoad={onChange} />
      </div>
      <div className="right">
        <div className={`status ${status}`}>
          status: {status}
          {result?.meta?.compute_ms != null &&
            ` - compute: ${result.meta.compute_ms.toFixed(2)} ms`}
          {error && ` - error: ${error.message}`}
        </div>
        {(result?.meta?.sensitivity_nm_per_k != null
          || result?.meta?.strain_sensitivity_pm_per_microstrain != null) && (
          <div className="sensing">
            temperature {result.meta.temperature_c.toFixed(0)} C
            {` | strain ${result.meta.strain_microstrain.toFixed(0)} ue`}
            {` | stop-band centre ${result.meta.stop_band_centre_nm?.toFixed(2) ?? "n/a"} nm`}
            {result.meta.sensitivity_nm_per_k != null &&
              ` | T sensitivity ${result.meta.sensitivity_nm_per_k.toFixed(3)} nm/K`}
            {result.meta.strain_sensitivity_pm_per_microstrain != null &&
              ` | strain sensitivity ${result.meta.strain_sensitivity_pm_per_microstrain.toFixed(2)} pm/ue`}
          </div>
        )}
        <SpectralPlot wavelengths={result?.wavelengths_nm}
                      reflectance={result?.reflectance} />
        <LayerStackView stack={result?.stack} />
      </div>
    </div>
  );
}
