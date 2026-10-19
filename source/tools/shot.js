// Screenshot of one section, with console errors printed. Needs Playwright (npm i playwright; or NODE_PATH to an install).
//   node tools/shot.js --hash cost --out /tmp/cost.png [--file '../en.html'] [--width 1280] [--height 900] [--dark] [--full]
//                      [--click "css selector"]... [--eval "js run in the page before the shot"]
const path = require('path');
const { chromium } = require('playwright');
const args = process.argv.slice(2), opt = { file: '../en.html', hash: 'summary', out: 'shot.png', width: 1280, height: 900, clicks: [], evals: [] };
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === '--dark') opt.dark = true; else if (a === '--full') opt.full = true;
  else if (a === '--click') opt.clicks.push(args[++i]); else if (a === '--eval') opt.evals.push(args[++i]);
  else opt[a.replace(/^--/, '')] = args[++i];
}
(async () => {
  const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
  const page = await browser.newPage({ viewport: { width: +opt.width, height: +opt.height }, colorScheme: opt.dark ? 'dark' : 'light' });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });   // web fonts may be blocked offline
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto('file://' + path.resolve(opt.file) + '#' + opt.hash);
  await page.waitForTimeout(700);
  for (const sel of opt.clicks) { await page.click(sel); await page.waitForTimeout(250); }
  for (const js of opt.evals) { await page.evaluate(js); await page.waitForTimeout(250); }
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  await page.screenshot({ path: opt.out, fullPage: !!opt.full });
  console.log(`${opt.out}  ${opt.width}px ${opt.dark ? 'dark' : 'light'}  horizontal overflow: ${overflow}px  errors: ${errors.length}`);
  errors.forEach(e => console.log('  ERROR ' + e));
  await browser.close();
  if (errors.length || overflow > 0) process.exitCode = 1;
})();
