import assert from "node:assert/strict";
import test from "node:test";

import { parseScenario, toCsv, toResultJson, toScenarioJson } from "../src/lib/scenario.js";

const PARAMS = {
  material_high: "Si",
  material_low: "SiO2",
  centre_nm: 1550,
  periods: 15,
};
const SWEEP = { start_nm: 1400, stop_nm: 1700, n_points: 11 };

test("toCsv writes a header and one row per wavelength", () => {
  const csv = toCsv([1400, 1550], [1.0, 0.5]);
  assert.equal(csv.split("\n")[0], "wavelength_nm,reflectance");
  assert.equal(csv.split("\n")[1], "1400.0000,1.0000000000");
  assert.ok(csv.endsWith("\n"));
});

test("toCsv rejects mismatched arrays", () => {
  assert.throws(() => toCsv([1400], []), /same length/);
});

test("scenario JSON round-trips params and sweep", () => {
  const parsed = parseScenario(toScenarioJson(PARAMS, SWEEP));
  assert.deepEqual(parsed.params, PARAMS);
  assert.deepEqual(parsed.sweep, SWEEP);
});

test("result JSON contains the simulation result", () => {
  const result = { wavelengths_nm: [1400, 1550], reflectance: [1, 0.5] };
  const exported = JSON.parse(toResultJson(PARAMS, SWEEP, result));
  assert.equal(exported.component, "bragg_grating");
  assert.deepEqual(exported.params, PARAMS);
  assert.deepEqual(exported.result, result);
});

test("parseScenario rejects an unsupported component", () => {
  const raw = JSON.parse(toScenarioJson(PARAMS, SWEEP));
  raw.component = "ring_resonator";
  assert.throws(() => parseScenario(JSON.stringify(raw)), /unsupported component/);
});

test("parseScenario rejects a missing field", () => {
  const raw = JSON.parse(toScenarioJson(PARAMS, SWEEP));
  delete raw.params.periods;
  assert.throws(() => parseScenario(JSON.stringify(raw)), /missing params\.periods/);
});

test("parseScenario rejects an out-of-range period count", () => {
  const raw = JSON.parse(toScenarioJson(PARAMS, SWEEP));
  raw.params.periods = 17;
  assert.throws(() => parseScenario(JSON.stringify(raw)), /periods out of range/);
});

test("parseScenario rejects an inverted sweep", () => {
  const raw = JSON.parse(toScenarioJson(PARAMS, SWEEP));
  raw.sweep.start_nm = 1800;
  assert.throws(() => parseScenario(JSON.stringify(raw)), /start_nm must be less/);
});
