// Stack E2E: real Chromium -> vite dev (:5173) -> /api proxy -> FastAPI (:8000)
// Verifies the honest demo journey: history dates -> default date -> map ->
// cell click -> profile/explainer/ARGO, plus region-switch honesty and zero
// page/console errors. Waits on visible assertions, not sleeps.
import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';
const results = [];
const errors = [];

function check(name, ok, detail = '') {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  -- ' + detail : ''}`);
}

const browser = await chromium.launch();
const page = await browser.newPage();
page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
page.on('console', (m) => {
  if (m.type() === 'error') errors.push(`console.error: ${m.text()}`);
});

await page.goto(BASE, { waitUntil: 'networkidle' });

// 1. Honest footer present on load
const footer = await page.textContent('footer');
check('honest footer shown', /Modeled reconstruction/.test(footer), footer?.slice(0, 60));

// 2. Real dates load from the backend via the vite proxy; default applied
await page.waitForSelector('select', { timeout: 15000 });
const dateCount = await page.locator('[aria-label="Date"] option').count();
check('date selector has demo dates', dateCount >= 30, `${dateCount} dates`);
const chosen = await page.locator('[aria-label="Date"]').inputValue();
check('a date is selected', /^\d{4}-\d{2}-\d{2}$/.test(chosen), chosen);

// 3. Map field rendered with an honest caption
const caption = (await page.textContent('[data-testid="field-caption"]').catch(() => '')) ?? '';
check('field caption present', caption.length > 0, caption.slice(0, 60));

// 4. Click map center -> profile loads (real data or honest miss)
const mapBox = await page.locator('.leaflet-container').boundingBox();
await page.mouse.click(mapBox.x + mapBox.width / 2, mapBox.y + mapBox.height / 2);
const pageText = await page.textContent('body');
const depthLabels = await page.locator('text=/^\\d{1,4} m$/').count().catch(() => 0);
const honestMiss = /No vertical profile/.test(pageText);
check(
  'profile section rendered (real or honest miss)',
  depthLabels > 0 || honestMiss,
  `depthLabels=${depthLabels} honestMiss=${honestMiss}`,
);

// 5. ARGO validation panel reachable with honest metrics
check('ARGO panel reachable', /ARGO/i.test(pageText) && /RMSE|1\.3/i.test(pageText));

// 6. Region switch honesty: arabian_sea -> unavailable, no fabricated dates
await page.getByLabel('Region').selectOption({ label: 'arabian sea' });
await page.getByTestId('empty-region-state').getByText(/No demo data/).waitFor({ timeout: 10000 });
const banner = (await page.textContent('body')).match(/Unavailable.{0,140}/)?.[0] ?? '';
check(
  'region switch honest (unavailable, no fabricated demo)',
  /No demo data/i.test(banner),
  banner.slice(0, 120),
);
const dateAfter = await page.locator('[aria-label="Date"] option').count();
check('date selector empties for the no-data region', dateAfter === 0, `${dateAfter} dates`);

// 7. Return to Bay of Bengal restores the demo
await page.getByRole('button', { name: /Return to Bay of Bengal/ }).click();
await page.waitForFunction(
  () => document.querySelectorAll('[aria-label="Date"] option').length > 0,
  { timeout: 10000 },
);
check('return to demo region restores dates', true);

// 8. No console/page errors anywhere
check('zero page/console errors', errors.length === 0, errors.slice(0, 3).join(' | '));

await page.screenshot({ path: '/tmp/opencode/stack-e2e.png', fullPage: false });
await browser.close();

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
process.exit(failed.length ? 1 : 0);