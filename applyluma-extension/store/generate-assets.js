// Regenerates the store screenshots and promo tile in this folder.
//
//   cd applyluma-extension && node store/generate-assets.js
//
// Needs Playwright (`npm i -D playwright` anywhere on NODE_PATH, or run from
// frontend/ where it can be installed). The popup is rendered for real from
// popup/popup.html with a stubbed `chrome` API and sample job data, so the
// screenshots track UI changes — re-run after editing the popup.
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const EXT = path.resolve(__dirname, '..');
const OUT = __dirname;
const APP_ICON = path.resolve(EXT, '../frontend/public/icon-512.png');

const job = {
  title: 'Senior Backend Engineer',
  company: 'Northwind Analytics',
  url: 'https://www.linkedin.com/jobs/view/4012345678',
  description: 'We are looking for a backend engineer with strong Python and PostgreSQL experience to build our data platform. You will design FastAPI services, own our event pipeline, and mentor two junior engineers…',
  extractedAt: Date.now(),
};

function stub(state) {
  return `
    window.chrome = {
      storage: { local: {
        _d: ${JSON.stringify(state)},
        async get(k) { const keys = Array.isArray(k) ? k : [k]; const o = {}; for (const x of keys) if (x in this._d) o[x] = this._d[x]; return o; },
        async set(o) { Object.assign(this._d, o); },
        async remove() {},
      }},
      tabs: { create() {} },
      runtime: { sendMessage() {} },
    };`;
}

async function popupShot(browser, state, after, file) {
  const page = await browser.newPage({ viewport: { width: 360, height: 600 }, deviceScaleFactor: 2 });
  await page.addInitScript(stub(state));
  await page.goto('file://' + path.join(EXT, 'popup/popup.html'));
  await page.waitForTimeout(300);
  if (after) await page.evaluate(after);
  await page.waitForTimeout(200);
  const box = await page.locator('.container').boundingBox();
  await page.screenshot({ path: file, clip: { x: box.x, y: box.y, width: Math.floor(box.width), height: Math.ceil(box.height) } });
  await page.close();
}

async function compose(browser, popupPng, heading, sub, file) {
  const img = fs.readFileSync(popupPng).toString('base64');
  const html = `<html><body style="margin:0;width:1280px;height:800px;display:flex;align-items:center;gap:72px;padding:0 96px;box-sizing:border-box;
    background:linear-gradient(135deg,#eef2ff 0%,#e0e7ff 55%,#c7d2fe 100%);font-family:Inter,system-ui,sans-serif">
    <div style="flex:1">
      <div style="display:inline-block;padding:6px 14px;border-radius:999px;background:#4f46e5;color:#fff;font-size:15px;font-weight:600;margin-bottom:22px">ApplyLuma for Chrome</div>
      <h1 style="font-size:52px;line-height:1.1;color:#1e1b4b;margin:0 0 20px;font-weight:800">${heading}</h1>
      <p style="font-size:22px;line-height:1.5;color:#4338ca;margin:0">${sub}</p>
    </div>
    <img src="data:image/png;base64,${img}" style="width:380px;border-radius:16px;box-shadow:0 24px 60px rgba(30,27,75,.28);max-height:720px;object-fit:cover;object-position:top"/>
  </body></html>`;
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.setContent(html);
  await page.screenshot({ path: file });
  await page.close();
}

(async () => {
  const browser = await chromium.launch();
  const tmp = fs.mkdtempSync(path.join(require('os').tmpdir(), 'al-store-'));
  fs.mkdirSync(tmp, { recursive: true });
  fs.mkdirSync(OUT, { recursive: true });

  const connected = { applyluma_token: 'x', linkedinJob: job, savedUrls: [] };
  await popupShot(browser, connected, null, `${tmp}/save.png`);
  await popupShot(browser, connected, () => {
    const s = document.getElementById('save-status');
    s.textContent = 'Saved to ApplyLuma!'; s.className = 'status success';
    document.getElementById('btn-save').disabled = true;
    document.getElementById('score-section').classList.remove('hidden');
    document.getElementById('score-value').textContent = '86%';
    const bar = document.getElementById('score-bar'); bar.style.width = '86%'; bar.style.background = '#10b981';
    document.getElementById('score-hint').textContent = 'Strong match with your default CV.';
    document.getElementById('btn-track').classList.remove('hidden');
    document.getElementById('tailor-section').classList.remove('hidden');
    document.getElementById('tailor-usage').textContent = '9 of 10 tailors left today';
    const sel = document.getElementById('tailor-cv-select'); sel.innerHTML = '<option>Backend CV (default)</option>';
    document.getElementById('field-description').closest('.field').style.display = 'none';
  }, `${tmp}/score.png`);
  await popupShot(browser, { savedUrls: [] }, null, `${tmp}/connect.png`);
  await popupShot(browser, { applyluma_token: 'x', savedUrls: new Array(24).fill('u') }, null, `${tmp}/connected.png`);

  await compose(browser, `${tmp}/save.png`, 'Save any job in one click', 'Title, company and description are read straight from LinkedIn, Indeed, Glassdoor and Arbetsförmedlingen.', `${OUT}/screenshot-1-save.png`);
  await compose(browser, `${tmp}/score.png`, 'See how well you match', 'Get an AI match score against your CV, track the application, and tailor your CV — without leaving the posting.', `${OUT}/screenshot-2-match.png`);
  await compose(browser, `${tmp}/connected.png`, 'Everything lands in ApplyLuma', 'Saved jobs sync to your dashboard. Press Alt+Shift+S to save without opening the popup.', `${OUT}/screenshot-3-synced.png`);

  // Small promo tile 440x280
  const page = await browser.newPage({ viewport: { width: 440, height: 280 } });
  const icon = fs.readFileSync(APP_ICON).toString('base64');
  await page.setContent(`<html><body style="margin:0;width:440px;height:280px;display:flex;flex-direction:column;align-items:center;justify-content:center;
    background:linear-gradient(135deg,#4f46e5,#7c3aed);font-family:Inter,system-ui,sans-serif;color:#fff">
    <img src="data:image/png;base64,${icon}" style="width:84px;height:84px;margin-bottom:18px"/>
    <div style="font-size:34px;font-weight:800">ApplyLuma</div>
    <div style="font-size:17px;opacity:.9;margin-top:6px">Save jobs. See your match. Apply smarter.</div></body></html>`);
  await page.screenshot({ path: `${OUT}/promo-small-440x280.png` });
  await browser.close();
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log(`store assets written to ${OUT}`);
})();
