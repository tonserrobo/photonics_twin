import { useState } from "react";
import { useSimulation } from "./hooks/useSimulation.js";
import ParameterPanel from "./components/ParameterPanel.jsx";
import SpectralPlot from "./components/SpectralPlot.jsx";
import LayerStackView from "./components/LayerStackView.jsx";

const INITIAL_PARAMS = { material_high: "Si", material_low: "SiO2",
                          centre_nm: 1550.0, periods: 15 };
const INITIAL_SWEEP  = { start_nm: 1400.0, stop_nm: 1700.0, n_points: 501 };

export default function App() {
  const [params, setParams] = useState(INITIAL_PARAMS);
  const [sweep,  setSweep]  = useState(INITIAL_SWEEP);
  const onChange = (p, s) => { setParams(p); setSweep(s); };

  const { result, status, error } = useSimulation(params, sweep);

  return (
    <div className="container">
      <ParameterPanel params={params} sweep={sweep} onChange={onChange} />
      <div className="right">
        <div className={`status ${status}`}>
          status: {status}
          {result?.meta?.compute_ms != null &&
            ` · compute: ${result.meta.compute_ms.toFixed(2)} ms`}
          {error && ` · error: ${error.message}`}
        </div>
        <SpectralPlot wavelengths={result?.wavelengths_nm}
                      reflectance={result?.reflectance} />
        <LayerStackView stack={result?.stack} />
      </div>
    </div>
  );
}
