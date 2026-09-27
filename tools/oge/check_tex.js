// Проверка всех формул сайта через KaTeX (throwOnError) — список ошибок в cache/tex_errors.json.
const katex = require(require('path').resolve(__dirname, '../../oge/vendor/katex/katex.min.js'));
const fs = require('fs'), path = require('path');
const D = path.resolve(__dirname, '../../oge/data');
const RE = /\$\$([\s\S]+?)\$\$|\$((?:\\\$|[^$])+?)\$/g;
const unesc = s => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const errs = [];
let total = 0;
const check = (id, h) => {
  for (const m of (h || '').replace(/<[^>]+>/g, ' ').matchAll(RE)) {
    total++;
    const tex = unesc(m[1] ?? m[2]);
    try { katex.renderToString(tex, { throwOnError: true, strict: 'ignore' }); }
    catch (e) { errs.push({ id, tex, err: e.message.slice(0, 160) }); }
  }
};
for (const f of fs.readdirSync(path.join(D, 'n'))) {
  for (const t of JSON.parse(fs.readFileSync(path.join(D, 'n', f), 'utf8')).tasks) {
    check(t.id, t.html);
    (t.opts || []).forEach(o => check(t.id, o));
  }
}
for (const [gid, g] of Object.entries(JSON.parse(fs.readFileSync(path.join(D, 'groups.json'), 'utf8')))) check('g:' + gid, g.html);
const th = path.resolve(__dirname, '../../oge/theory');
if (fs.existsSync(th)) for (const f of fs.readdirSync(th)) check('theory:' + f, fs.readFileSync(path.join(th, f), 'utf8'));
fs.writeFileSync(path.join(__dirname, 'cache', 'tex_errors.json'), JSON.stringify(errs, null, 1));
console.log('формул:', total, 'ошибок:', errs.length);
errs.slice(0, 15).forEach(e => console.log(e.id, '|', e.tex.slice(0, 80), '|', e.err.slice(0, 90)));
