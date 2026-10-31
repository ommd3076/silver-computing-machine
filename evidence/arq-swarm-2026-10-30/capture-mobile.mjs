import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { setTimeout as delay } from 'node:timers/promises';
import path from 'node:path';

const root = 'C:\\ommd3076\\Proejcts\\nmit-hackathon';
const evidence = path.join(root, 'evidence', 'arq-swarm-2026-10-30');
const profile = path.join(root, '.runtime', 'swarm-chromium-capture-profile');
const browserPath = 'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe';
const exportUrl = 'http://127.0.0.1:8082/';
const debugPort = 9223;
const screenshots = path.join(evidence, 'mobile-screens');
await mkdir(screenshots, { recursive: true });

const browser = spawn(browserPath, [
  '--no-first-run', '--no-default-browser-check',
  `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`,
  '--window-size=390,844', '--force-device-scale-factor=1', 'about:blank',
], { stdio: 'ignore', windowsHide: true });

let nextId = 0;
async function waitForDebugger() {
  for (let attempt = 0; attempt < 100; attempt++) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json/version`);
      if (response.ok) return;
    } catch { /* Browser is still starting. */ }
    await delay(200);
  }
  throw new Error('Edge remote debugging endpoint did not become ready.');
}

async function createPage(url) {
  const response = await fetch(`http://127.0.0.1:${debugPort}/json/new?about:blank`, { method: 'PUT' });
  if (!response.ok) throw new Error(`Could not create browser page: ${response.status}`);
  const target = await response.json();
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true });
    socket.addEventListener('error', reject, { once: true });
  });
  const pending = new Map();
  socket.addEventListener('close', () => {
    for (const item of pending.values()) item.reject(new Error('Browser target socket closed before replying.'));
    pending.clear();
  });
  socket.addEventListener('error', () => {
    for (const item of pending.values()) item.reject(new Error('Browser target socket failed.'));
    pending.clear();
  });
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const item = pending.get(message.id);
      pending.delete(message.id);
      message.error ? item.reject(new Error(message.error.message)) : item.resolve(message.result);
    }
  });
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
    setTimeout(() => {
      if (pending.has(id)) { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }
    }, 15_000).unref?.();
  });
  await call('Page.enable');
  await call('Runtime.enable');
  await call('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await call('Page.navigate', { url });
  return { target, socket, call };
}

async function evaluate(page, expression) {
  const result = await page.call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true, userGesture: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  return result.result.value;
}
async function waitFor(page, expression, description, timeout = 12_000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (await evaluate(page, expression)) return;
    await delay(250);
  }
  throw new Error(`Timed out waiting for ${description}`);
}
async function clickText(page, text) {
  const result = await evaluate(page, `(() => {
    const wanted = ${JSON.stringify(text)};
    const elements = [...document.querySelectorAll('button,[role="button"],a,[role="tab"]')];
    const match = elements.find(el => (el.getAttribute('aria-label') || el.innerText || '').trim() === wanted);
    if (!match) return false;
    match.click(); return true;
  })()`);
  if (!result) throw new Error(`Button or tab not found: ${text}`);
}
async function typeByLabel(page, label, value) {
  const result = await evaluate(page, `(() => {
    const wanted = ${JSON.stringify(label)};
    const input = [...document.querySelectorAll('input,textarea')].find(el => el.getAttribute('aria-label') === wanted);
    if (!input) return false;
    const setter = Object.getOwnPropertyDescriptor(input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, 'value').set;
    setter.call(input, ${JSON.stringify(value)});
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  })()`);
  if (!result) throw new Error(`Input not found: ${label}`);
}
async function screenshot(page, name, gate) {
  await waitFor(page, `document.readyState === 'complete' && document.body?.innerText?.length > 20`, 'rendered app');
  await delay(300);
  const result = await page.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  await writeFile(path.join(screenshots, name), Buffer.from(result.data, 'base64'));
  const text = await evaluate(page, 'document.body.innerText');
  return { file: path.join('mobile-screens', name), gate, visible_text_sha256: await hash(text), visible_text_excerpt: text.replace(/\s+/g, ' ').trim().slice(0, 240) };
}
async function hash(text) {
  const { createHash } = await import('node:crypto');
  return createHash('sha256').update(text).digest('hex');
}

const records = [];
let first;
let second;
try {
  await waitForDebugger();
  first = await createPage(exportUrl);
  await waitFor(first, `document.body?.innerText?.includes('PAIRING CODE')`, 'pair screen');
  records.push(await screenshot(first, '01-pair-driver-1.png', 'pair form before submitting PAIR01'));
  await typeByLabel(first, 'Pairing code', 'PAIR01');
  await clickText(first, 'Connect');
  await waitFor(first, `document.body?.innerText?.includes('Ramesh Kumar')`, 'first driver session');
  records.push(await screenshot(first, '02-home-driver-1.png', 'PAIR01 actual local API session home'));

  second = await createPage(exportUrl);
  await waitFor(second, `document.body?.innerText?.includes('PAIRING CODE')`, 'second pair screen');
  records.push(await screenshot(second, '03-pair-driver-2.png', 'pair form before submitting PAIR02'));
  await typeByLabel(second, 'Pairing code', 'PAIR02');
  await clickText(second, 'Connect');
  await waitFor(second, `document.body?.innerText?.includes('Suresh Patel')`, 'second driver session');
  records.push(await screenshot(second, '04-home-driver-2.png', 'PAIR02 actual local API session home'));

  await clickText(first, 'Route');
  records.push(await screenshot(first, '05-route-map.png', 'route map for PAIR01'));
  await clickText(first, 'View route guidance');
  records.push(await screenshot(first, '06-navigation.png', 'route guidance screen for PAIR01'));
  await clickText(first, 'Stops');
  records.push(await screenshot(first, '07-stops.png', 'stops list or explicit empty state for PAIR01'));
  await clickText(first, 'Home');
  await clickText(first, 'Report congestion');
  records.push(await screenshot(first, '08-report-form.png', 'report form before submission'));
  await clickText(first, 'Set heavy severity');
  records.push(await screenshot(first, '09-report-heavy.png', 'report form with heavy severity selected; submit left untouched'));
  await clickText(second, 'Settings');
  records.push(await screenshot(second, '10-settings-driver-2.png', 'settings for separate PAIR02 session'));
  if (records.length !== 10) throw new Error(`Expected ten mobile screenshots, captured ${records.length}.`);

  const apiEvidence = await fetch('http://127.0.0.1:8000/api/v1/health').then(r => r.ok ? r.json() : Promise.reject(new Error(`API health HTTP ${r.status}`)));
  await writeFile(path.join(evidence, 'mobile-capture-results.json'), JSON.stringify({
    capture_kind: 'local Chromium CDP browser at mobile viewport; exported Expo web bundle; not native runtime or device testing',
    export_url: exportUrl,
    api_url: 'http://127.0.0.1:8000',
    api_health_status: 'reachable',
    api_health_keys: Object.keys(apiEvidence || {}).sort(),
    session_pairs: ['PAIR01', 'PAIR02'],
    session_identity_visible: ['Ramesh Kumar', 'Suresh Patel'],
    screenshots: records,
  }, null, 2) + '\n');
  console.log(JSON.stringify({ status: 'PASS', screenshots: records.length, files: records.map(r => r.file), api_health_status: 'reachable' }, null, 2));
} catch (error) {
  await writeFile(path.join(evidence, 'mobile-capture-attempt.txt'), `${error.stack || error}\n`);
  console.error(error.stack || error);
  process.exitCode = 1;
} finally {
  for (const page of [first, second]) {
    try { page?.socket.close(); } catch { /* Browser may already be closed. */ }
  }
  browser.kill();
}
