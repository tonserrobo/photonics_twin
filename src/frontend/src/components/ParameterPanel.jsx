const MATERIALS = ["Si", "SiO2"];

const BASE_PARAMS = {
  material_high: "Si",
  material_low: "SiO2",
  centre_nm: 1550,
  periods: 15,
  temperature_c: 20,
  strain_microstrain: 0,
  wavelength_noise_nm: 0.01,
};

const PRESETS = {
  telecom: {
    params: { ...BASE_PARAMS },
    sweep: { start_nm: 1400, stop_nm: 1700, n_points: 501 },
  },
  sensing: {
    params: { ...BASE_PARAMS },
    sweep: { start_nm: 1150, stop_nm: 1350, n_points: 501 },
  },
  strain: {
    params: { ...BASE_PARAMS },
    sweep: { start_nm: 1200, stop_nm: 1240, n_points: 401 },
  },
};

export default function ParameterPanel({ params, sweep, onChange }) {
  const set = (next) => onChange({ ...params, ...next }, sweep);
  const setSweep = (next) => onChange(params, { ...sweep, ...next });
  const applyPreset = (preset) => onChange(preset.params, preset.sweep);

  return (
    <div className="panel">
      <h2>Parameters</h2>

      <div className="presets">
        <button type="button" onClick={() => applyPreset(PRESETS.telecom)}>
          Telecom filter
        </button>
        <button type="button" onClick={() => applyPreset(PRESETS.sensing)}>
          Sensing edge
        </button>
        <button type="button" onClick={() => applyPreset(PRESETS.strain)}>
          Strain gauge
        </button>
      </div>

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

      <label>temperature_c = {params.temperature_c.toFixed(0)}
        <input type="range" min="-40" max="200" step="1"
               value={params.temperature_c}
               onChange={(e) => set({ temperature_c: Number(e.target.value) })} />
      </label>

      <label>strain_microstrain = {params.strain_microstrain.toFixed(0)}
        <input type="range" min="-5000" max="5000" step="100"
               value={params.strain_microstrain}
               onChange={(e) => set({ strain_microstrain: Number(e.target.value) })} />
      </label>      <label>wavelength_noise_nm = {params.wavelength_noise_nm.toFixed(3)}
        <input type="range" min="0.001" max="0.1" step="0.001"
               value={params.wavelength_noise_nm}
               onChange={(e) => set({ wavelength_noise_nm: Number(e.target.value) })} />
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
