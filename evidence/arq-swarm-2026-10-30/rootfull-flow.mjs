import { mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { chromium } from '../../nmit-frontend/frontend/node_modules/playwright/index.mjs';

const repo = 'C:\\ommd3076\\Proejcts\\nmit-hackathon';
const evidence = path.join(repo, 'evidence', 'arq-swarm-2026-10-30');
const shots = path.join(evidence, 'mobile-screens');
const profile = path.join(repo, '.runtime', 'mobile-playwright-profile');
const url = 'http://127.0.0.1:8082/';
const gate = path.join(evidence, 'mobile-approval-ready.txt');
await mkdir(shots, { recursive: true });

const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--enable-unsafe-swiftshader'] });
const driverAContext = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
const driverBContext = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
const pages = [];
const diagnostics = [];
const records = [];
const proposal = {};
function observe(page, label) {
  page.on('pageerror', error => diagnostics.push({ driver: label, type: 'pageerror', text: error.message }));
  page.on('console', message => { if (message.type() === 'error') diagnostics.push({ driver: label, type: 'console', text: message.text() }); });
  page.on('response', response => { if (response.status() >= 400) diagnostics.push({ driver: label, type: 'http-error', status: response.status(), url: response.url() }); });
}
async function capture(page, name, gateText) {
  await page.screenshot({ path: path.join(shots, name), fullPage: true });
  const text = (await page.locator('body').innerText()).replace(/\s+/g, ' ').trim();
  records.push({ file: `mobile-screens/${name}`, gate: gateText, visible_text_sha256: createHash('sha256').update(text).digest('hex'), visible_text_excerpt: text.slice(0, 240) });
  return text;
}
async function pair(context, code, driverName, label) {
  const page = await context.newPage(); pages.push(page); observe(page, label);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  await page.getByText('PAIRING CODE', { exact: true }).waitFor({ timeout: 15000 });
  await page.getByLabel('Pairing code').fill(code);
  await page.getByRole('button', { name: 'Connect' }).click();
  await page.getByText(driverName, { exact: false }).waitFor({ timeout: 15000 });
  await page.getByRole('tab', { name: 'Home' }).waitFor({ timeout: 5000 });
  return page;
}
async function writeResults(status, extra = {}) {
  const health = await fetch('http://127.0.0.1:8001/api/v1/health').then(async r => ({ status: r.status, body: r.ok ? await r.json() : null }));
  await writeFile(path.join(evidence, 'mobile-flow-results.json'), JSON.stringify({ status, capture_kind: 'Playwright Chromium headless with GPU disabled; current exported Expo web bundle; real local API8001; 390x844 mobile viewport; not native/device evidence', export_url: url, api_url: 'http://127.0.0.1:8001', api_health_status: health.status, api_health_keys: Object.keys(health.body || {}).sort(), screenshots: records, console_diagnostics: diagnostics, ...extra }, null, 2) + '\n');
}

try {
  // Distinct browser storage contexts exercise isolation between two real driver sessions.
  const a = await pair(driverAContext, 'ROOTA', 'Ramesh Kumar', 'driver A');
  await capture(a, 'flow-01-home-driver-a.png', 'ROOTA live API session for Ramesh Kumar');
  const b = await pair(driverBContext, 'ROOTB', 'Suresh Patel', 'driver B');
  await capture(b, 'flow-02-home-driver-b.png', 'ROOTB separate live API session for Suresh Patel');

  await a.getByRole('tab', { name: 'Route' }).click();
  await a.getByRole('heading', { name: 'Active route' }).waitFor({ timeout: 10000 });
  await a.locator('.maplibregl-canvas').waitFor({ state: 'visible', timeout: 20000 });
  await a.waitForFunction(() => !!document.querySelector('.maplibregl-canvas')?.getContext('webgl2') || !!document.querySelector('.maplibregl-canvas')?.getContext('webgl'));
  await a.waitForTimeout(1000);
  const mapText = await a.locator('body').innerText();
  if (diagnostics.some(d => d.driver === 'driver A' && d.type === 'pageerror')) throw new Error(`Route screen raised an uncaught page error: ${diagnostics.find(d => d.driver === 'driver A' && d.type === 'pageerror').text}`);
  if (!/Planned route|ROUTE OVERVIEW/.test(mapText)) throw new Error('Route overview text is not visible.');
  await capture(a, 'flow-03-active-route-map.png', 'Active route map rendered with MapLibre canvas and route overview');
  await a.getByRole('button', { name: 'View route guidance' }).click();
  await a.getByRole('heading', { name: 'Route guidance' }).waitFor({ timeout: 8000 });
  await capture(a, 'flow-04-navigation.png', 'planned next stop guidance rendered');
  await a.getByRole('tab', { name: 'Stops' }).click();
  await a.getByRole('heading', {name:'Stops'}).waitFor({ timeout: 8000 });
  await capture(a, 'flow-05-stops.png', 'stop list or explicit no-stops state rendered');
  await a.getByRole('tab', { name: 'Home' }).click();
  await a.getByRole('button', { name: 'Report congestion' }).first().click();
  await a.getByText('Report a delay', { exact: true }).waitFor({ timeout: 8000 });
  await capture(a, 'flow-06-report-form.png', 'report form before editing or submission');
  await a.getByRole('button', { name: 'Set heavy severity' }).click();
  await a.getByLabel('Congestion description').fill('QA heavy congestion at the demo junction');
  await capture(a, 'flow-07-report-heavy.png', 'heavy severity and QA note selected before submission');
  const [response] = await Promise.all([
    a.waitForResponse(r => r.url().endsWith('/api/v1/demo/reports') && r.request().method() === 'POST', { timeout: 30000 }),
    a.getByRole('button', { name: 'Send to dispatch' }).click(),
  ]);
  const result = await response.json();
  Object.assign(proposal, { proposal_id: result.proposal_id, vehicle_id: result.vehicle_id, driver_id: result.driver_id, decision: result.decision, base_route_version: result.base_route_version, job_id: result.job_id });
  await a.getByText(/Report received|No alternate route proposed/).first().waitFor({timeout:15000});
  const pendingText = await capture(a, 'flow-08-report-pending.png', 'real report response and its dispatch proposal result');
  if (result.decision !== 'PROPOSE_ROUTE') {
    await writeResults('BLOCKED_NO_ALTERNATE_PROPOSAL', { proposal, pending_text: pendingText });
    throw new Error(`Heavy report returned decision ${result.decision}; dispatcher approval flow cannot continue.`);
  }

  const web = await browser.newPage({viewport:{width:1366,height:900}});
  await web.goto('http://127.0.0.1:5173/#/compare');
  await web.getByRole('button',{name:'Review approval'}).waitFor({timeout:25000});
  await web.screenshot({path:path.join(shots,'root-dispatcher-comparison.png'),fullPage:true});
  await web.getByRole('button',{name:'Review approval'}).click();
  await web.getByRole('button',{name:'Confirm & publish',exact:true}).click();
  await web.getByText('The backend accepted the approval and returned the updated manifest.').waitFor({timeout:15000});
  await web.screenshot({path:path.join(shots,'root-dispatcher-approved.png'),fullPage:true});
  await a.getByRole('button', { name: 'Check for route update' }).click();
  await a.getByText('DISPATCH PUBLISHED', { exact: true }).waitFor({ timeout: 20000 });
  const update = await capture(a, 'flow-09-route-update.png', 'mobile sees dispatcher-published route update after refresh');
  const version = update.match(/Acknowledge version (\d+)/)?.[1];
  if (!version) throw new Error('Acknowledgement version is not visible after route publication.');
  await a.getByRole('button', { name: `Acknowledge version ${version}` }).click();
  await a.getByText(`Acknowledged route version ${version}`, { exact: false }).first().waitFor({ timeout: 15000 });
  await capture(a, 'flow-10-route-acknowledged.png', 'server confirms the exact route version acknowledgement');

  await b.getByRole('tab', { name: 'Settings' }).click();
  const driverBSettings = await capture(b, 'flow-11-driver-b-isolation.png', 'driver B retains separate identity and route version after driver A approval');
  const isolated = /Suresh Patel/.test(driverBSettings) && /ROUTE VERSION\s+v1/.test(driverBSettings);
  await writeResults(isolated ? 'PASS' : 'FAIL_DRIVER_ISOLATION', { proposal, driver_b_isolation: { expected_name: 'Suresh Patel', expected_route_version: 'v1', observed_text: driverBSettings.slice(0, 500) } });
  console.log(JSON.stringify({ status: isolated ? 'PASS' : 'FAIL_DRIVER_ISOLATION', proposal, screenshots: records.length }, null, 2));
  if (!isolated) throw new Error('Driver B identity or original route version was not preserved after Driver A route publication.');
} catch (error) {
  await writeResults('FAIL', { proposal, error: error.message });
  await writeFile(path.join(evidence, 'mobile-flow-failure.txt'), `${error.stack || error}\nScreenshots captured: ${records.map(r => r.file).join(', ')}\nDiagnostics: ${JSON.stringify(diagnostics, null, 2)}\n`);
  console.error(error.stack || error);
  process.exitCode = 1;
} finally {
  await driverAContext.close().catch(() => {});
  await driverBContext.close().catch(() => {});
  await browser.close().catch(() => {});
}
