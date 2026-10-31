import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

const root = 'C:\\ommd3076\\Proejcts\\nmit-hackathon';
const evidence = path.join(root, 'evidence', 'arq-swarm-2026-10-30');
const api = 'http://127.0.0.1:8000';
const results = [];

async function request(route, { method = 'GET', token, body } = {}) {
  const response = await fetch(`${api}${route}`, {
    method,
    headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let value = {};
  try { value = text ? JSON.parse(text) : {}; } catch { value = {}; }
  return { status: response.status, ok: response.ok, value };
}

for (const pairingCode of ['PAIR01', 'PAIR02']) {
  const paired = await request('/api/v1/demo/sessions', { method: 'POST', body: { code: pairingCode } });
  if (!paired.ok || typeof paired.value.token !== 'string') {
    const err = paired.value?.detail?.error;
    results.push({ pairing_code: pairingCode, pair_status: paired.status, error_code: typeof err?.code === 'string' ? err.code : 'pair_failed' });
    continue;
  }
  const token = paired.value.token;
  const [me, state, manifest] = await Promise.all([
    request('/api/v1/demo/me', { token }),
    request('/api/v1/demo/state', { token }),
    request('/api/v1/demo/manifest', { token }),
  ]);
  const summary = {
    pairing_code: pairingCode,
    pair_status: paired.status,
    me_status: me.status,
    driver_id: typeof me.value.driver_id === 'string' ? me.value.driver_id : null,
    driver_name: typeof me.value.driver_name === 'string' ? me.value.driver_name : null,
    vehicle_id: typeof me.value.vehicle_id === 'string' ? me.value.vehicle_id : null,
    state_status: state.status,
    state_route_id: typeof state.value.route_id === 'string' ? state.value.route_id : null,
    state_route_version: Number.isInteger(state.value.route_version) ? state.value.route_version : null,
    state_manifest_revision: Number.isInteger(state.value.manifest_revision) ? state.value.manifest_revision : null,
    manifest_status: manifest.status,
    manifest_route_id: typeof manifest.value.route_id === 'string' ? manifest.value.route_id : null,
    manifest_route_version: Number.isInteger(manifest.value.route_version) ? manifest.value.route_version : null,
    manifest_version: Number.isInteger(manifest.value.version) ? manifest.value.version : null,
  };
  if (state.ok && Number.isInteger(state.value.route_version) && state.value.route_version > 0) {
    const report = await request('/api/v1/demo/reports', { method: 'POST', token, body: {
      event_id: `mobile-qa-${randomUUID()}`,
      base_route_version: state.value.route_version,
      severity: 'moderate',
      note: 'Mobile QA congestion scenario.',
    } });
    summary.report_status = report.status;
    summary.report_decision = typeof report.value.decision === 'string' ? report.value.decision : null;
    summary.report_proposal_status = typeof report.value.status === 'string' ? report.value.status : null;
    summary.report_validation_status = typeof report.value.validation?.status === 'string' ? report.value.validation.status : null;
  }
  const revoked = await request('/api/v1/demo/sessions/current', { method: 'DELETE', token });
  summary.revoke_status = revoked.status;
  results.push(summary);
}

const health = await request('/api/v1/health');
const distinctDrivers = new Set(results.filter(item => item.pair_status === 200).map(item => item.driver_id)).size;
const distinctVehicles = new Set(results.filter(item => item.pair_status === 200).map(item => item.vehicle_id)).size;
const final = {
  execution: 'real localhost FastAPI HTTP requests; no mocks; session bearer tokens held in process memory and omitted from output',
  api_origin: api,
  health_status: health.status,
  two_distinct_driver_sessions: distinctDrivers === 2 && distinctVehicles === 2,
  driver_sessions: results,
};
await writeFile(path.join(evidence, 'mobile-api-results.json'), JSON.stringify(final, null, 2) + '\n');
console.log(JSON.stringify({ health_status: final.health_status, two_distinct_driver_sessions: final.two_distinct_driver_sessions, sessions: results.map(({ pairing_code, pair_status, driver_name, state_status, manifest_status, report_status, revoke_status, error_code }) => ({ pairing_code, pair_status, driver_name, state_status, manifest_status, report_status, revoke_status, error_code })) }, null, 2));
if (distinctDrivers !== 2 || distinctVehicles !== 2) process.exitCode = 1;
