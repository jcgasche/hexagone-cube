// Lists the text still in English on a page of the French study: every visible text, title and label of the chosen sections,
// after their scripts have run, that looks English (two or more common English words). Needs Playwright, as shot.js.
//   node tools/i18n_check.js --file '../Paris Through Stations - FR.html' --hash access,crossing [--click "css selector"]...
const path = require('path');
const { chromium } = require('playwright');
const args = process.argv.slice(2), opt = { file: '../Paris Through Stations - FR.html', hash: 'summary', clicks: [] };
for (let i = 0; i < args.length; i++) { const a = args[i]; if (a === '--click') opt.clicks.push(args[++i]); else opt[a.replace(/^--/, '')] = args[++i]; }
const EN = /\b(the|and|of|to|with|from|for|is|are|at|by|each|every|today|hour|year|years|cost|benefits|line|lines|track|tracks|passengers|which|that|this|not|more|less|than|per|day|between|through|here|there|would|could|will|its|their|saved|built|until|after|before|without)\b/gi;
(async () => {
  const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  let total = 0;
  for (const id of opt.hash.split(',')) {
    await page.goto('file://' + path.resolve(opt.file) + '#' + id);
    await page.waitForTimeout(1200);
    for (const sel of opt.clicks) { try { await page.click(sel); await page.waitForTimeout(300); } catch (e) { /* not on this page */ } }
    const found = await page.evaluate((src) => {
      const re = new RegExp(src, 'gi'), out = new Set(), root = document.getElementById(location.hash.slice(1).split('.')[0]) || document.body;
      const look = (t) => { t = (t || '').trim(); if (t.length < 4) return; const m = t.match(re); if (m && m.length >= 2) out.add(t.slice(0, 160)); };
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
      let x; while ((x = w.nextNode())) {
        if (x.nodeType === 3) { const p = x.parentElement; if (p && !p.closest('script, style, code, .src-row th, .src-row td:nth-child(3)')) look(x.data); }
        else ['title', 'aria-label'].forEach((a) => look(x.getAttribute(a)));
      }
      return Array.from(out);
    }, EN.source);
    total += found.length;
    console.log(`#${id}: ${found.length} English-looking text${found.length === 1 ? '' : 's'}`);
    found.forEach((t) => console.log('   ' + t));
  }
  errors.forEach((e) => console.log('  ERROR ' + e));
  await browser.close();
  if (errors.length) process.exitCode = 1;
  console.log(`total: ${total}`);
})();
