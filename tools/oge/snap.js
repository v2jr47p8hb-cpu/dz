// Снимки условий для банка кабинета: задачи с таблицами, формулами-картинками, несколькими рисунками
// и общие тексты сюжетов № 1–5 → oge/snap/*.png. Нужен запущенный `python3 -m http.server 8765` в корне репо.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..', '..');
const need = JSON.parse(fs.readFileSync(path.join(__dirname, 'cache', 'snap_need.json'), 'utf8'));
const loc = JSON.parse(fs.readFileSync(path.join(ROOT, 'oge', 'data', 'loc.json'), 'utf8'));
const groups = JSON.parse(fs.readFileSync(path.join(ROOT, 'oge', 'data', 'groups.json'), 'utf8'));
const nums = {};
const task = id => {
  const n = loc[id];
  if (!nums[n]) nums[n] = JSON.parse(fs.readFileSync(path.join(ROOT, 'oge', 'data', 'n', `${String(n).padStart(2, '0')}.json`), 'utf8'));
  return nums[n].tasks.find(t => t.id === id);
};
const img = h => (h || '').replace(/<img src="([^"]+)"/g, '<img src="../../oge/img/$1"');
(async () => {
  fs.mkdirSync(path.join(ROOT, 'oge', 'snap'), { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 720, height: 800 }, deviceScaleFactor: 1.5 });
  await p.goto('http://localhost:8765/tools/oge/snap.html');
  await p.waitForFunction(() => window.ready);
  let n = 0;
  for (const [out, it] of Object.entries(need)) {
    const file = path.join(ROOT, out);
    if (fs.existsSync(file) && !process.argv.includes('--force')) continue;
    let html;
    if (it.kind === 'group') html = `<div class="q">${img(groups[it.gid].html)}</div>`;
    else {
      const t = task(it.id);
      const ctx = it.ctx && t.g ? `<div class="ctx"><div class="q">${img(groups[t.g].html)}</div></div>` : '';
      const opts = t.opts ? `<ol class="opts">${t.opts.map((o, i) => `<li><b>${i + 1})</b><div>${img(o)}</div></li>`).join('')}</ol>` : '';
      html = `${ctx}<div class="q">${img(t.html)}</div>${opts}`;
    }
    await p.evaluate(h => { const s = document.getElementById('s'); s.innerHTML = h; window.renderMath(s); }, html);
    await p.evaluate(() => Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; }))));
    await p.evaluate(() => document.fonts.ready);
    await (await p.$('#s')).screenshot({ path: file });
    if (++n % 50 === 0) console.log(n);
  }
  console.log('снимков:', n);
  await b.close();
})();
