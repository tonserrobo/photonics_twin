export const SCENARIO_VERSION = 1;
export const COMPONENT = "bragg_grating";

const MATERIALS = ["Si", "SiO2"];
const PARAM_KEYS = ["material_high", "material_low", "centre_nm", "periods"];
const SWEEP_KEYS = ["start_nm", "stop_nm", "n_points"];

const isNumber = (value) => typeof value === "number" && Number.isFinite(value);

export function toCsv(wavelengths, reflectance) {
  if (!Array.isArray(wavelengths) || !Array.isArray(reflectance)) {
    throw new Error("wavelengths and reflectance must be arrays");
  }
  if (wavelengths.length !== reflectance.length) {
    throw new Error("wavelengths and reflectance must have the same length");
  }
  const rows = ["wavelength_nm,reflectance"];
  for (let i = 0; i < wavelengths.length; i += 1) {
    if (!isNumber(wavelengths[i]) || !isNumber(reflectance[i])) {
      throw new Error(`row ${i} is not numeric`);
    }
    rows.push(`${wavelengths[i].toFixed(4)},${reflectance[i].toFixed(10)}`);
  }
  return `${rows.join("\n")}\n`;
}

export function toScenarioJson(params, sweep) {
  return `${JSON.stringify({
    schema_version: SCENARIO_VERSION,
    component: COMPONENT,
    params,
    sweep,
  }, null, 2)}\n`;
}

export function toResultJson(params, sweep, result) {
  return `${JSON.stringify({
    schema_version: SCENARIO_VERSION,
    component: COMPONENT,
    params,
    sweep,
    result,
  }, null, 2)}\n`;
}

function requireKeys(object, keys, label) {
  if (!object || typeof object !== "object") {
    throw new Error(`missing ${label}`);
  }
  for (const key of keys) {
    if (!(key in object)) throw new Error(`missing ${label}.${key}`);
  }
}

export function parseScenario(text) {
  let raw;
  try {
    raw = JSON.parse(text);
  } catch {
    throw new Error("not valid JSON");
  }
  if (!raw || typeof raw !== "object") {
    throw new Error("scenario must be an object");
  }
  if (raw.component && raw.component !== COMPONENT) {
    throw new Error(`unsupported component: ${raw.component}`);
  }
  if (raw.schema_version != null && raw.schema_version !== SCENARIO_VERSION) {
    throw new Error(`unsupported schema_version: ${raw.schema_version}`);
  }

  const { params, sweep } = raw;
  requireKeys(params, PARAM_KEYS, "params");
  requireKeys(sweep, SWEEP_KEYS, "sweep");

  if (!MATERIALS.includes(params.material_high) || !MATERIALS.includes(params.material_low)) {
    throw new Error("unsupported material");
  }
  if (!isNumber(params.centre_nm)) throw new Error("params.centre_nm must be a number");
  if (!isNumber(params.periods)) throw new Error("params.periods must be a number");
  const temperature = params.temperature_c ?? 20;
  if (!isNumber(temperature)) throw new Error("params.temperature_c must be a number");
  const strain = params.strain_microstrain ?? 0;
  if (!isNumber(strain)) throw new Error("params.strain_microstrain must be a number");
  for (const key of SWEEP_KEYS) {
    if (!isNumber(sweep[key])) throw new Error(`sweep.${key} must be a number`);
  }

  if (params.centre_nm < 400 || params.centre_nm > 2500) {
    throw new Error("params.centre_nm out of range");
  }
  if (!Number.isInteger(params.periods) || params.periods < 2 || params.periods > 16) {
    throw new Error("params.periods out of range");
  }
  if (temperature < -40 || temperature > 200) {
    throw new Error("params.temperature_c out of range");
  }
  if (strain < -5000 || strain > 5000) {
    throw new Error("params.strain_microstrain out of range");
  }
  if (sweep.start_nm < 200 || sweep.start_nm > 3000
      || sweep.stop_nm < 200 || sweep.stop_nm > 3000) {
    throw new Error("sweep out of range");
  }
  if (!Number.isInteger(sweep.n_points) || sweep.n_points < 11 || sweep.n_points > 4001) {
    throw new Error("sweep.n_points out of range");
  }
  if (sweep.start_nm >= sweep.stop_nm) {
    throw new Error("sweep.start_nm must be less than sweep.stop_nm");
  }

  return {
    params: { ...params, temperature_c: temperature, strain_microstrain: strain },
    sweep: { ...sweep },
  };
}
