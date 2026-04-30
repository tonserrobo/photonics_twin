const MATERIALS = ["Si", "SiO2"];

export default function ParameterPanel({ params, sweep, onChange }) {
  const set = (next) => onChange({ ...params, ...next }, sweep);
  const setSweep = (next) => onChange(params, { ...sweep, ...next });

  return (
    <div className="panel">
      <h2>Parameters</h2>

      <label>material_high
        <select value={params.material_high}
                onChange={(e) => set({ material_high: e.target.value })}>
          {MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </label>

      <label>material_low
        <select value={params.material_low}
                onChange={(e) => set({ material_low: e.target.value })}>
          {MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </label>

      <label>centre_nm = {params.centre_nm.toFixed(1)}
        <input type="range" min="800" max="2000" step="1"
               value={params.centre_nm}
               onChange={(e) => set({ centre_nm: Number(e.target.value) })} />
      </label>

      <label>periods = {params.periods}
        <input type="range" min="2" max="16" step="1"
               value={params.periods}
               onChange={(e) => set({ periods: Number(e.target.value) })} />
      </label>

      <h3>Sweep</h3>
      <label>start_nm = {sweep.start_nm.toFixed(0)}
        <input type="range" min="400" max="2400" step="1"
               value={sweep.start_nm}
               onChange={(e) => setSweep({ start_nm: Number(e.target.value) })} />
      </label>
      <label>stop_nm = {sweep.stop_nm.toFixed(0)}
        <input type="range" min="400" max="2400" step="1"
               value={sweep.stop_nm}
               onChange={(e) => setSweep({ stop_nm: Number(e.target.value) })} />
      </label>
      <label>n_points = {sweep.n_points}
        <input type="range" min="51" max="1001" step="50"
               value={sweep.n_points}
               onChange={(e) => setSweep({ n_points: Number(e.target.value) })} />
      </label>
    </div>
  );
}
