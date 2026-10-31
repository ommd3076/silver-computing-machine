import { mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { chromium } from '../../nmit-frontend/frontend/node_modules/playwright/index.mjs';

const repo = 'C:\\ommd3076\\Proejcts\\nmit-hackathon';
const evidence = path.join(repo, 'evidence', 'arq-swarm-2026-10-30');
const screenshots = path.join(evidence, 'mobile-screens');
const url = 'http://127.0.0.1:8082/';
await mkdir(screenshots, { recursive: true });

const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--disable-software-rasterizer'] });
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
const pages = [];
const diagnostics = [];
const records = [];
const page = await context.newPage();
pages.push(page);
for (const type of ['console', 'pageerror', 'requestfailed']) page.on(type, event => diagnostics.push({ type, text: type === 'console' ? event.text() : String(event.message ?? event.errorText ?? event) }));
page.on('response', response => { if (response.status() >= 400) diagnostics.push({ type: 'http-error', status: response.status(), url: response.url() }); });

async function capture(target, name, gate) {
  await target.screenshot({ path: path.join(screenshots, name), fullPage: true });
  const text = (await target.locator('body').innerText()).replace(/\s+/g, ' ').trim();
  records.push({ file: `mobile-screens/${name}`, gate, visible_text_sha256: createHash('sha256').update(text).digest('hex'), visible_text_excerpt: text.slice(0, 240) });
}

let failure;
try {
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  await page.getByText('PAIRING CODE', { exact: true }).waitFor({ timeout: 15000 });
  await capture(page, '01-pair-driver-1.png', 'pair form before submitting PAIR01');
  await page.getByLabel('Pairing code').fill('PAIR01');
  await page.getByRole('button', { name: 'Connect' }).click();
  try {
    await page.getByText('Ramesh Kumar').waitFor({ timeout: 15000 });
  } catch (error) {
    await capture(page, '02-pair-rejected.png', 'pair submission was rejected by the local API');
    throw error;
  }
  await capture(page, '02-home-driver-1.png', 'PAIR01 actual local API session home');

  const second = await context.newPage();
  pages.push(second);
  for (const type of ['console', 'pageerror', 'requestfailed']) second.on(type, event => diagnostics.push({ type, text: type === 'console' ? event.text() : String(event.message ?? event.errorText ?? event) }));
  await second.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  await second.getByText('PAIRING CODE', { exact: true }).waitFor({ timeout: 15000 });
  await capture(second, '03-pair-driver-2.png', 'pair form before submitting PAIR02');
  await second.getByLabel('Pairing code').fill('PAIR02');
  await second.getByRole('button', { name: 'Connect' }).click();
  await second.getByText('Suresh Patel').waitFor({ timeout: 15000 });
  await capture(second, '04-home-driver-2.png', 'PAIR02 actual local API session home');

  await page.getByRole('button', { name: 'Route' }).click();
  await capture(page, '05-route-map.png', 'route map for PAIR01');
  await page.getByRole('button', { name: 'View route guidance' }).click();
  await capture(page, '06-navigation.png', 'route guidance screen for PAIR01');
  await page.getByRole('button', { name: 'Stops' }).click();
  await capture(page, '07-stops.png', 'stops list or explicit empty state for PAIR01');
  await page.getByRole('button', { name: 'Home' }).click();
  await page.getByRole('button', { name: 'Report congestion' }).click();
  await capture(page, '08-report-form.png', 'report form before submission');
  await page.getByRole('button', { name: 'Set heavy severity' }).click();
  await capture(page, '09-report-heavy.png', 'report form with heavy severity selected; submit untouched');
  await second.getByRole('button', { name: 'Settings' }).click();
  await capture(second, '10-settings-driver-2.png', 'settings for separate PAIR02 session');
  const api = await fetch('http://127.0.0.1:8001/api/v1/health').then(async r => ({ status: r.status, body: r.ok ? await r.json() : null }));
  await writeFile(path.join(evidence, 'mobile-capture-results.json'), JSON.stringify({ capture_kind: 'Playwright Chromium headless with GPU disabled; exported Expo web bundle; mobile viewport; not native runtime/device evidence', export_url: url, api_url: 'http://127.0.0.1:8001', api_health_status: api.status, api_health_keys: Object.keys(api.body || {}).sort(), screenshots: records, console_diagnostics: diagnostics }, null, 2) + '\n');
  console.log(JSON.stringify({ status: 'PASS', screenshots: records.length, files: records.map(r => r.file), diagnostics }, null, 2));
} catch (error) {
  failure = error;
  await writeFile(path.join(evidence, 'mobile-capture-attempt.txt'), `${error.stack || error}\nCaptured before failure: ${records.map(r => r.file).join(', ')}\nBrowser diagnostics: ${JSON.stringify(diagnostics, null, 2)}\n`);
  console.error(error.stack || error);
} finally {
  await context.close().catch(() => {});
  await browser.close().catch(() => {});
}
if (failure) process.exitCode = 1;
