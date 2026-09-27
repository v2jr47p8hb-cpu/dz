// ОГЭ · математика: каталог задач открытого банка ФИПИ по номерам КИМ и прототипам, теория, корзина ДЗ учителя.
import { renderMath } from './tex.js';
import { md } from './md.js';
import { call, whoami, store, ApiError } from './api.js';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const plural = (n, a, b, c) => { const m = n % 10, h = n % 100; return m === 1 && h !== 11 ? a : m >= 2 && m <= 4 && (h < 10 || h >= 20) ? b : c; };
const shuffle = a => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const SDAM = id => `https://oge.sdamgia.ru/problem?id=${id}`;
const PAGE = 30;

const S = {
  index: null, nums: {}, groups: null, loc: null, theory: {},
  me: null, groupsList: [], teacher: false,
  answers: null,              // id → ответ из банка кабинета (только учителю)
  bankIds: null,              // какие om-* уже загружены в банк кабинета
  view: { sub: '', q: '', shown: PAGE, proto: '' },
  cart: [],
};

// ---------- данные ----------
async function json(url) {
  const r = await fetch(url, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`Не загрузилось: ${url}`);
  return r.json();
}
const getIndex = async () => (S.index ||= await json('data/index.json'));
async function getNum(n) {
  if (!S.nums[n]) {
    const d = await json(`data/n/${String(n).padStart(2, '0')}.json`);
    S.nums[n] = d;
    d.byId = Object.fromEntries(d.tasks.map(t => [t.id, t]));
  }
  return S.nums[n];
}
const getGroups = async () => (S.groups ||= await json('data/groups.json'));
const getLoc = async () => (S.loc ||= await json('data/loc.json'));
async function getTheory(n) {
  if (S.theory[n] == null) {
    const r = await fetch(`theory/${String(n).padStart(2, '0')}.md`, { cache: 'no-cache' });
    S.theory[n] = r.ok ? await r.text() : '';
  }
  return S.theory[n];
}
async function findTask(id) {
  const loc = await getLoc();
  const n = loc[id];
  if (n == null) return null;
  const d = await getNum(n);
  return d.byId[id] || null;
}
const numInfo = n => S.index.nums.find(x => x.n === n) || S.index.archive;

// ---------- корзина ДЗ ----------
function loadCart() { try { S.cart = JSON.parse(store.get('startum_oge_cart') || '[]'); } catch { S.cart = []; } }
function saveCart() { store.set('startum_oge_cart', JSON.stringify(S.cart)); cartBadge(); }
function cartBadge() { const b = $('#cart-n'); if (b) b.textContent = S.cart.length; }
const inCart = id => S.cart.includes(id);
function toggleCart(id) {
  if (inCart(id)) S.cart = S.cart.filter(x => x !== id); else S.cart.push(id);
  saveCart();
}

// ---------- мелочи интерфейса ----------
let toastT;
function toast(msg) {
  let t = $('.toast');
  if (!t) { t = document.createElement('div'); t.className = 'toast'; t.setAttribute('role', 'status'); document.body.append(t); }
  t.textContent = msg;
  clearTimeout(toastT);
  toastT = setTimeout(() => t.remove(), 3200);
}
document.addEventListener('click', e => {
  const img = e.target.closest('.q img:not(.i)');
  if (img) {
    const z = document.createElement('div');
    z.className = 'zoom';
    z.innerHTML = `<img src="${esc(img.src)}" alt="Рисунок крупно">`;
    z.onclick = () => z.remove();
    document.body.append(z);
  }
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') $('.zoom')?.remove(); });

// ---------- отрисовка задачи ----------
const LETTERS = 'АБВГДЕ';
function qhtml(h) {
  return (h || '').replace(/<img src="([^"]+)"/g, (m, src) => `<img loading="lazy" alt="Рисунок" src="img/${esc(src)}"`);
}
function kindTag(t) {
  if (t.kind === 'long') return '<span class="tag long">развёрнутый ответ · 2 балла</span>';
  if (t.kind === 'choice') return '<span class="tag">выбор ответа</span>';
  if (t.kind === 'multi') return '<span class="tag">несколько ответов</span>';
  if (t.kind === 'match') return '<span class="tag">соответствие</span>';
  return '';
}
function answerHint(t) {
  if (t.kind === 'match') return `Ответ — цифры под буквами ${(t.mc || []).join(', ')} подряд`;
  if (t.kind === 'choice') return 'Ответ — номер верного варианта';
  if (t.kind === 'multi') return 'Ответ — номера верных вариантов подряд, без пробелов';
  return '';
}
function taskCard(t, { full = false, showCtx = false } = {}) {
  const info = numInfo(t.n);
  const sub = info && info.subs ? info.subs.find(s => s.id === t.sub) : null;
  const opts = t.opts && t.opts.length
    ? `<ol class="opts">${t.opts.map((o, i) => `<li><b>${i + 1})</b><div>${qhtml(o)}</div></li>`).join('')}</ol>` : '';
  const ctx = (showCtx || t.g) && t.g && S.groups && S.groups[t.g]
    ? `<details class="ctx"${full ? ' open' : ''}><summary>Общий текст к заданиям: ${esc(S.groups[t.g].title)}</summary><div class="q">${qhtml(S.groups[t.g].html)}</div></details>` : '';
  const ans = S.teacher && S.answers
    ? (S.answers[t.id] != null ? `<span class="ans">Ответ: ${esc(S.answers[t.id])}</span>` : (t.kind !== 'long' ? '<span class="ans none">нет в банке кабинета</span>' : ''))
    : '';
  const src = (t.src || []).slice(0, 2).map(s => `<span class="tag src">${esc(s)}</span>`).join('');
  const hint = answerHint(t);
  const canCart = S.teacher && t.bank;
  return `<article class="task" data-id="${esc(t.id)}">
    <div class="task-h">
      <a class="no" href="#/n/${t.n || 'arch'}">${t.n ? '№ ' + t.n : 'Архив'}</a>
      ${sub ? `<span class="tag">${esc(sub.name)}</span>` : ''}${kindTag(t)}${src}
      <a class="id" href="#/t/${esc(t.id)}" title="Открыть задачу">${esc(t.fid)}</a>
    </div>
    <div class="task-b">${ctx}<div class="q">${qhtml(t.html)}</div>${opts}${hint ? `<p class="faint xs" style="margin:.6em 0 0">${hint}</p>` : ''}</div>
    <div class="task-f">
      ${ans}
      ${t.proto ? `<a class="btn sm" href="#/p/${esc(t.proto)}">Похожие${t.pc > 1 ? ` · ${t.pc}` : ''}</a>` : ''}
      ${t.n ? `<a class="btn sm" href="#/theory/${t.n}${t.sub ? '/' + esc(t.sub) : ''}">Теория</a>` : ''}
      ${t.g ? `<a class="btn sm" href="#/g/${esc(t.g)}">Весь сюжет</a>` : ''}
      ${t.sid ? `<a class="btn sm" href="${SDAM(t.sid)}" target="_blank" rel="noopener noreferrer">Разбор на Решу ОГЭ ↗</a>` : ''}
      ${canCart ? `<button class="btn sm${inCart(t.id) ? ' on' : ''}" data-cart="${esc(t.id)}">${inCart(t.id) ? '✓ В домашке' : '+ В домашку'}</button>` : ''}
    </div>
  </article>`;
}
function bindTaskButtons(root) {
  $$('[data-cart]', root).forEach(b => b.onclick = () => {
    toggleCart(b.dataset.cart);
    const on = inCart(b.dataset.cart);
    b.classList.toggle('on', on);
    b.textContent = on ? '✓ В домашке' : '+ В домашку';
  });
}

// ---------- экраны ----------
const BLOCKS = [
  ['practice', 'Практико-ориентированные задачи', '№ 1–5 — один сюжет: участок, квартира, шины, печь, тарифы, бумага…'],
  ['algebra', 'Алгебра, часть 1', '№ 6–14'],
  ['geometry', 'Геометрия, часть 1', '№ 15–19 — нужны минимум 2 балла за геометрию'],
  ['part2', 'Часть 2 — развёрнутый ответ', '№ 20–25, по 2 балла'],
];

async function vHome() {
  const ix = await getIndex();
  const card = x => `<div class="card">
      <a class="no" href="#/n/${x.n}" aria-label="Номер ${x.n}">№ ${x.n}</a>
      <a class="t" href="#/n/${x.n}" style="color:var(--ink)">${esc(x.title)}</a>
      <div class="meta">${x.count} ${plural(x.count, 'задача', 'задачи', 'задач')}${x.subs.length > 1 ? ` · ${x.subs.length} ${plural(x.subs.length, 'подтип', 'подтипа', 'подтипов')}` : ''}</div>
      <div class="acts"><a href="#/n/${x.n}">Задачи</a><a href="#/theory/${x.n}">Теория</a></div>
    </div>`;
  return `<div class="head"><div><h1>ОГЭ по математике</h1>
      <p>Все ${ix.total} ${plural(ix.total, 'задание', 'задания', 'заданий')} открытого банка ФИПИ, разложенные по номерам КИМ и прототипам. К каждому номеру — теория, у каждой задачи — похожие и ссылка на разбор.</p></div></div>
    ${S.teacher ? `<p class="note">Режим учителя: у задач видны ответы и кнопка «+ В домашку». Собери задачи в <a href="#/cart">домашку</a> и выдай группе — ученики решат в кабинете, краткие ответы проверятся сами.</p>` : ''}
    ${BLOCKS.map(([b, t, d]) => `<div class="blk"><h2>${t}</h2><span class="faint sm">${d}</span></div>
      <div class="grid">${ix.nums.filter(x => x.block === b).map(card).join('')}</div>`).join('')}
    ${ix.archive && ix.archive.count ? `<div class="blk"><h2>Архив</h2><span class="faint sm">Задачи старых форматов, которых нет в КИМ 2026</span></div>
      <div class="grid"><div class="card"><a class="no" href="#/n/arch">Д</a><a class="t" href="#/n/arch" style="color:var(--ink)">${esc(ix.archive.title)}</a><div class="meta">${ix.archive.count} ${plural(ix.archive.count, 'задача', 'задачи', 'задач')}</div></div></div>` : ''}
    <p class="faint xs" style="margin-top:28px">Условия — открытый банк заданий ФИПИ (${esc(ix.generated)}). Структура КИМ — спецификация ОГЭ 2026. Разборы — на сайте «Решу ОГЭ» Д. Д. Гущина.</p>`;
}

function filterTasks(d, v) {
  const q = v.q.trim().toLowerCase();
  return d.tasks.filter(t => (!v.sub || t.sub === v.sub) && (!v.proto || String(t.proto) === v.proto)
    && (!q || (t._s ||= (t.fid + ' ' + t.html.replace(/<[^>]+>/g, ' ') + ' ' + (t.opts || []).join(' ')).toLowerCase()).includes(q)));
}

async function vNum(key) {
  const ix = await getIndex();
  const n = key === 'arch' ? 0 : +key;
  const info = numInfo(n);
  if (!info) return notFound();
  const d = await getNum(key === 'arch' ? 'arch' : n);
  if (d.tasks.some(t => t.g)) await getGroups();
  const v = S.view;
  if (v.key !== key) Object.assign(v, { key, sub: '', q: '', shown: PAGE, proto: '' });
  const list = filterTasks(d, v);
  const subs = info.subs || [];
  const plots = n >= 1 && n <= 5 ? Object.values(S.groups).filter(g => g.nums.includes(n)) : [];
  return `<div class="crumbs"><a href="#/">Каталог</a> / ${n ? '№ ' + n : 'Архив'}</div>
    <div class="head"><div><h1>${n ? `№ ${n}. ` : ''}${esc(info.title)}</h1>
      <p>${esc(info.about || '')}${info.pts ? ` · ${info.pts} ${plural(info.pts, 'балл', 'балла', 'баллов')}` : ''}</p></div>
      ${n ? `<a class="btn" href="#/theory/${n}">Теория к № ${n}</a>` : ''}</div>
    ${plots.length ? `<details class="panel" style="margin-bottom:14px"><summary><b>Сюжеты (${plots.length})</b> <span class="faint sm">— текст и все вопросы к нему сразу</span></summary>
      <div class="chips" style="margin-top:10px">${plots.map(g => `<a class="chip" href="#/g/${esc(g.id)}">${esc(g.title)}</a>`).join('')}</div></details>` : ''}
    ${subs.length > 1 ? `<div class="chips" role="group" aria-label="Подтипы">
      <button class="chip" data-sub="" aria-pressed="${!v.sub}">Все<small>${d.tasks.length}</small></button>
      ${subs.map(s => `<button class="chip" data-sub="${esc(s.id)}" aria-pressed="${v.sub === s.id}">${esc(s.name)}<small>${s.count}</small></button>`).join('')}</div>` : ''}
    <div class="bar">
      <input class="inp search" id="q" type="search" placeholder="Поиск по тексту или номеру ФИПИ" value="${esc(v.q)}" aria-label="Поиск">
      ${v.proto ? `<span class="tag">прототип ${esc(v.proto)} <a href="#/n/${key}" data-unproto>×</a></span>` : ''}
      <span class="faint sm">${list.length} ${plural(list.length, 'задача', 'задачи', 'задач')}</span>
      ${S.teacher ? `<span style="margin-left:auto;display:flex;gap:6px;align-items:center;flex-wrap:wrap">
        <input class="inp" id="rn" type="number" min="1" max="50" value="10" style="width:72px" aria-label="Сколько задач">
        <label class="sm"><input type="checkbox" id="rp" checked> разные прототипы</label>
        <button class="btn" id="radd">+ Случайные в домашку</button></span>` : ''}
    </div>
    <div class="list" id="list">${list.slice(0, v.shown).map(t => taskCard(t)).join('') || '<div class="empty">Ничего не нашлось</div>'}</div>
    ${list.length > v.shown ? `<div class="more"><button class="btn" id="more">Показать ещё ${Math.min(PAGE, list.length - v.shown)} из ${list.length - v.shown}</button></div>` : ''}`;
}
function bindNum(key) {
  const v = S.view;
  $$('[data-sub]').forEach(b => b.onclick = () => { v.sub = b.dataset.sub; v.shown = PAGE; v.proto = ''; render(); });
  let t;
  const q = $('#q');
  if (q) q.oninput = () => { clearTimeout(t); t = setTimeout(() => { v.q = q.value; v.shown = PAGE; render({ keepFocus: '#q' }); }, 250); };
  const more = $('#more');
  if (more) more.onclick = () => { v.shown += PAGE; render({ keepScroll: true }); };
  const radd = $('#radd');
  if (radd) radd.onclick = async () => {
    const d = await getNum(key === 'arch' ? 'arch' : +key);
    const pool = shuffle(filterTasks(d, v).filter(x => x.bank && !inCart(x.id)));
    const want = Math.max(1, Math.min(50, +$('#rn').value || 10));
    const picked = [];
    if ($('#rp').checked) {
      const seen = new Set();
      for (const x of pool) if (picked.length < want && !seen.has(x.proto || x.id)) { seen.add(x.proto || x.id); picked.push(x); }
    }
    for (const x of pool) if (picked.length < want && !picked.includes(x)) picked.push(x);
    if (!picked.length) { toast('Подходящих задач нет — все уже в домашке или без ответа'); return; }
    S.cart.push(...picked.map(x => x.id));
    saveCart();
    toast(`Добавлено в домашку: ${picked.length}`);
    render({ keepScroll: true });
  };
}

async function vTask(id) {
  await getIndex();
  const t = await findTask(id);
  if (!t) return notFound();
  if (t.g) await getGroups();
  const d = await getNum(t.n || 'arch');
  const sim = t.proto ? d.tasks.filter(x => x.proto === t.proto && x.id !== t.id) : [];
  return `<div class="crumbs"><a href="#/">Каталог</a> / <a href="#/n/${t.n || 'arch'}">${t.n ? '№ ' + t.n : 'Архив'}</a> / ${esc(t.fid)}</div>
    <div class="list">${taskCard(t, { full: true, showCtx: true })}</div>
    ${sim.length ? `<div class="blk"><h2>Похожие задачи</h2><span class="faint sm">тот же прототип · ${sim.length}</span></div>
      <div class="list">${sim.slice(0, 6).map(x => taskCard(x)).join('')}</div>
      ${sim.length > 6 ? `<div class="more"><a class="btn" href="#/p/${esc(t.proto)}">Все похожие (${sim.length + 1})</a></div>` : ''}` : ''}`;
}

async function vProto(pid) {
  const ix = await getIndex();
  const loc = await getLoc();
  const n = loc['p' + pid];
  if (n == null) return notFound();
  const d = await getNum(n || 'arch');
  const list = d.tasks.filter(t => String(t.proto) === String(pid));
  if (list.some(t => t.g)) await getGroups();
  const info = numInfo(n);
  const sub = info.subs && info.subs.find(s => s.id === list[0]?.sub);
  return `<div class="crumbs"><a href="#/">Каталог</a> / <a href="#/n/${n || 'arch'}">${n ? '№ ' + n : 'Архив'}</a> / прототип</div>
    <div class="head"><div><h1>Похожие задачи</h1><p>${n ? `№ ${n}` : 'Архив'}${sub ? ` · ${esc(sub.name)}` : ''} · один прототип, ${list.length} ${plural(list.length, 'задача', 'задачи', 'задач')}</p></div>
    ${S.teacher ? `<button class="btn" id="pall">+ Все в домашку</button>` : ''}</div>
    <div class="list">${list.map(t => taskCard(t)).join('')}</div>`;
}
function bindProto(pid) {
  const b = $('#pall');
  if (b) b.onclick = async () => {
    const loc = await getLoc();
    const d = await getNum(loc['p' + pid] || 'arch');
    const add = d.tasks.filter(t => String(t.proto) === String(pid) && t.bank && !inCart(t.id)).map(t => t.id);
    S.cart.push(...add); saveCart(); toast(`Добавлено: ${add.length}`); render({ keepScroll: true });
  };
}

async function vGroup(gid) {
  await getIndex();
  const G = await getGroups();
  const g = G[gid];
  if (!g) return notFound();
  const tasks = [];
  for (const id of g.tasks) { const t = await findTask(id); if (t) tasks.push(t); }
  tasks.sort((a, b) => (a.n || 99) - (b.n || 99) || a.gk - b.gk);
  return `<div class="crumbs"><a href="#/">Каталог</a> / <a href="#/n/1">№ 1–5</a> / сюжет</div>
    <div class="head"><div><h1>${esc(g.title)}</h1><p>Сюжет практико-ориентированных заданий: один текст и ${tasks.length} ${plural(tasks.length, 'вопрос', 'вопроса', 'вопросов')} к нему (на экзамене — пять, № 1–5).</p></div>
    ${S.teacher ? `<button class="btn" id="gall">+ Все вопросы в домашку</button>` : ''}</div>
    <div class="panel q" style="margin-bottom:16px">${qhtml(g.html)}</div>
    <div class="list">${tasks.map(t => taskCard(t)).join('')}</div>`;
}
function bindGroup(gid) {
  const b = $('#gall');
  if (b) b.onclick = async () => {
    const g = (await getGroups())[gid];
    const add = [];
    for (const id of g.tasks) { const t = await findTask(id); if (t && t.bank && !inCart(id)) add.push(id); }
    S.cart.push(...add); saveCart(); toast(`Добавлено: ${add.length}`); render({ keepScroll: true });
  };
}

async function vTheoryIndex() {
  const ix = await getIndex();
  return `<div class="head"><div><h1>Теория ОГЭ по математике</h1><p>Коротко и по делу: что спрашивают в каждом номере, нужные формулы, алгоритм и типичные ошибки. Под каждым разделом — задачи для тренировки.</p></div></div>
    ${BLOCKS.map(([b, t]) => `<div class="blk"><h2>${t}</h2></div><div class="grid">${ix.nums.filter(x => x.block === b).map(x =>
      `<a class="card" href="#/theory/${x.n}"><span class="no">№ ${x.n}</span><span class="t">${esc(x.title)}</span></a>`).join('')}</div>`).join('')}`;
}
async function vTheory(n, anchor) {
  const ix = await getIndex();
  const info = numInfo(n);
  if (!info || !n) return notFound();
  const src = await getTheory(n);
  if (!src) return `<div class="crumbs"><a href="#/theory">Теория</a> / № ${n}</div><div class="empty">Теория к № ${n} пока пишется. <a href="#/n/${n}">Перейти к задачам</a></div>`;
  const { html, toc } = md(src);
  const prev = ix.nums.find(x => x.n === n - 1), next = ix.nums.find(x => x.n === n + 1);
  return `<div class="crumbs"><a href="#/theory">Теория</a> / № ${n}</div>
    <div class="side"><article class="theory" id="th">${html}
      <div class="bar" style="margin-top:28px">${prev ? `<a class="btn" href="#/theory/${prev.n}">← № ${prev.n}</a>` : ''}<a class="btn pri" href="#/n/${n}">Задачи № ${n}</a>${next ? `<a class="btn" href="#/theory/${next.n}">№ ${next.n} →</a>` : ''}</div></article>
      <aside><h3>№ ${n}. ${esc(info.title)}</h3>${toc.length ? `<ol>${toc.map(x => `<li><a href="#/theory/${n}/${esc(x.id)}">${x.title.replace(/\$[^$]*\$/g, '…')}</a></li>`).join('')}</ol>` : ''}
      <p style="margin:12px 0 0"><a href="#/n/${n}">Все задачи № ${n} →</a></p></aside></div>`;
}
function bindTheory(n, anchor) {
  // ссылки «Потренироваться» вида #/n/9?sub=43 → фильтр по подтипу
  $$('#th a[href^="#/n/"]').forEach(a => a.onclick = e => {
    const m = a.getAttribute('href').match(/^#\/n\/(\w+)(?:\?sub=([\w-]+))?/);
    if (m && m[2]) { e.preventDefault(); Object.assign(S.view, { key: m[1], sub: m[2], q: '', shown: PAGE, proto: '' }); location.hash = `#/n/${m[1]}`; }
  });
  if (anchor) {
    const el = document.getElementById(anchor) || $(`#th [id="${CSS.escape(anchor)}"]`);
    if (el) requestAnimationFrame(() => el.scrollIntoView({ block: 'start' }));
    else {
      // якорь = подтип: ищем раздел с data-sub
      const h = $$('#th h2').find(x => x.id === 's' + anchor || x.id === anchor);
      if (h) requestAnimationFrame(() => h.scrollIntoView({ block: 'start' }));
    }
  }
}

// ---------- корзина и выдача ----------
async function vCart() {
  await getIndex();
  if (!S.teacher) return `<div class="empty">Домашку собирает преподаватель. <a href="../">Войти в кабинет</a></div>`;
  const tasks = [];
  for (const id of S.cart) { const t = await findTask(id); if (t) tasks.push(t); }
  if (tasks.some(t => t.g)) await getGroups();
  const short = tasks.filter(t => t.kind !== 'long').length, long = tasks.length - short;
  const pts = tasks.reduce((a, t) => a + (t.kind === 'long' ? 2 : 1), 0);
  const groups = S.groupsList.slice().sort((a, b) => (b.exam === 'math-oge') - (a.exam === 'math-oge'));
  const missing = S.bankIds ? tasks.filter(t => !S.bankIds.has(t.id)) : [];
  return `<div class="head"><div><h1>Домашка из банка</h1><p>${tasks.length} ${plural(tasks.length, 'задача', 'задачи', 'задач')} · ${short} с кратким ответом (проверятся сами)${long ? `, ${long} с развёрнутым (фото решения, проверяешь ты)` : ''} · ${pts} ${plural(pts, 'балл', 'балла', 'баллов')}</p></div></div>
    ${!tasks.length ? `<div class="empty">Пока пусто. Открой <a href="#/">каталог</a> и нажимай «+ В домашку» — или «+ Случайные» на странице номера.</div>` : `
    <div class="two"><div class="list" id="cart">${tasks.map((t, i) => `<div class="cart-row"><div class="cart-ctl">
        <button class="btn sm" data-up="${i}" ${i ? '' : 'disabled'} aria-label="Выше">↑</button>
        <button class="btn sm" data-down="${i}" ${i < tasks.length - 1 ? '' : 'disabled'} aria-label="Ниже">↓</button></div>${taskCard(t)}</div>`).join('')}</div>
      <form class="panel" id="iss" novalidate>
        <h3 style="margin-bottom:12px">Выдать группе</h3>
        ${missing.length ? `<p class="err">В банке кабинета нет ${missing.length} ${plural(missing.length, 'задачи', 'задач', 'задач')} из домашки — сначала импортируй файл ОГЭ в «Пробники → Банк задач».</p>` : ''}
        <div class="field"><label for="i-g">Группа</label><select class="inp" id="i-g">${groups.map(g => `<option value="${esc(g.id)}">${esc(g.icon || '')} ${esc(g.title)}</option>`).join('')}</select></div>
        <div class="field"><label for="i-t">Название</label><input class="inp" id="i-t" maxlength="80" value="${esc(defaultTitle(tasks))}"></div>
        <div class="field"><label for="i-d">Сколько дней на выполнение</label><input class="inp" id="i-d" type="number" min="0" max="30" value="7" style="width:100px" inputmode="numeric"></div>
        <div class="field"><label for="i-m">Время, минут · 0 — без таймера</label><input class="inp" id="i-m" type="number" min="0" max="600" step="5" value="0" style="width:100px" inputmode="numeric"></div>
        <div class="field"><span class="lbl">Ответы ученику</span><div class="seg" id="i-r">
          <button type="button" class="chip" data-r="submit" aria-pressed="true">Сразу после сдачи</button>
          <button type="button" class="chip" data-r="close" aria-pressed="false">После срока</button></div></div>
        <div class="err" id="i-err"></div>
        <div class="bar"><button class="btn pri" id="i-go">Выдать</button><button type="button" class="btn" id="i-clr">Очистить</button></div>
        <p class="faint xs">Домашка уходит как пробник без таймера: ученик видит её в «Пробниках», краткие ответы проверяются автоматически, результаты — в «Пробники → Выданные».</p>
      </form></div>`}`;
}
function defaultTitle(tasks) {
  const ns = [...new Set(tasks.map(t => t.n).filter(Boolean))].sort((a, b) => a - b);
  const d = new Date();
  return `ОГЭ · ${ns.length ? (ns.length > 3 ? `№ ${ns[0]}–${ns[ns.length - 1]}` : '№ ' + ns.join(', ')) : 'задачи'} · ${d.getDate()}.${String(d.getMonth() + 1).padStart(2, '0')}`;
}
function bindCart() {
  $$('[data-up]').forEach(b => b.onclick = () => { const i = +b.dataset.up; [S.cart[i - 1], S.cart[i]] = [S.cart[i], S.cart[i - 1]]; saveCart(); render({ keepScroll: true }); });
  $$('[data-down]').forEach(b => b.onclick = () => { const i = +b.dataset.down; [S.cart[i + 1], S.cart[i]] = [S.cart[i], S.cart[i + 1]]; saveCart(); render({ keepScroll: true }); });
  $$('#cart [data-cart]').forEach(b => b.onclick = () => { toggleCart(b.dataset.cart); render({ keepScroll: true }); });
  let reveal = 'submit';
  $$('#i-r [data-r]').forEach(b => b.onclick = () => { reveal = b.dataset.r; $$('#i-r [data-r]').forEach(x => x.setAttribute('aria-pressed', x === b)); });
  const clr = $('#i-clr');
  if (clr) clr.onclick = () => { if (confirm('Убрать все задачи из домашки?')) { S.cart = []; saveCart(); render(); } };
  const f = $('#iss');
  if (!f) return;
  f.onsubmit = async e => {
    e.preventDefault();
    const err = $('#i-err'), go = $('#i-go');
    err.textContent = '';
    const title = $('#i-t').value.trim() || 'ОГЭ · домашка';
    const minutes = Math.round(+$('#i-m').value || 0), days = Math.round(+$('#i-d').value || 0);
    if (!$('#i-g').value) { err.textContent = 'Нет групп.'; return; }
    if (minutes < 0 || minutes > 600) { err.textContent = 'Время — от 0 до 600 минут.'; return; }
    go.disabled = true; go.textContent = 'Выдаём…';
    try {
      const v = await call('webVariantSave', { title, tasks: S.cart.slice() });
      let vid = v && v.id;
      if (!vid) {
        const d = await call('webMockTeacher');
        const same = d.variants.filter(x => x.title === (v && v.title || title));
        vid = same.length ? same[same.length - 1].id : null;
      }
      if (!vid) throw new ApiError('Вариант собран, но не нашёлся — выдай его в кабинете: «Пробники → Выдать».');
      const r = await call('webMockIssue', { gid: $('#i-g').value, title, variants: [vid], mode: 'same', minutes, days, reveal });
      S.cart = []; saveCart();
      $('#main').innerHTML = `<div class="empty"><h2 style="margin-bottom:8px">Выдано ✓</h2><p>${esc(r.title || title)} · ${esc(r.gt || '')}</p>
        <p><a class="btn pri" href="../#/t/mock/r/${encodeURIComponent(r.id || '')}">Результаты в кабинете</a> <a class="btn" href="#/">В каталог</a></p></div>`;
    } catch (ex) {
      err.textContent = ex.message || String(ex);
      go.disabled = false; go.textContent = 'Выдать';
    }
  };
}

// учителю: ответы и список уже импортированных задач из банка кабинета
async function loadTeacherBank() {
  if (!S.teacher || S.answers) return;
  try {
    const d = await call('webMockTeacher');
    S.answers = {}; S.bankIds = new Set();
    for (const t of d.bank || []) if (String(t.id).startsWith('om-')) { S.answers[t.id] = t.ans; S.bankIds.add(t.id); }
  } catch (e) {
    S.answers = {}; S.bankIds = null;
    if (e instanceof ApiError && e.authLost) { S.teacher = false; toast('Сессия кабинета закончилась — войди заново'); }
  }
}

function notFound() { return `<div class="empty">Такой страницы нет. <a href="#/">В каталог</a></div>`; }

// ---------- маршрутизация ----------
let busy = 0;
async function render(opt = {}) {
  const my = ++busy;
  const h = decodeURIComponent(location.hash.slice(1) || '/');
  const main = $('#main');
  const y = scrollY;
  let html, bind = () => {}, m;
  try {
    if (h === '/') html = await vHome();
    else if ((m = h.match(/^\/n\/(\d+|arch)$/))) { html = await vNum(m[1]); bind = () => bindNum(m[1]); }
    else if ((m = h.match(/^\/t\/([\w-]+)$/))) html = await vTask(m[1]);
    else if ((m = h.match(/^\/p\/(\d+)$/))) { html = await vProto(m[1]); bind = () => bindProto(m[1]); }
    else if ((m = h.match(/^\/g\/([\w-]+)$/))) { html = await vGroup(m[1]); bind = () => bindGroup(m[1]); }
    else if (h === '/theory') html = await vTheoryIndex();
    else if ((m = h.match(/^\/theory\/(\d+)(?:\/([\w-]+))?$/))) { html = await vTheory(+m[1], m[2]); bind = () => bindTheory(+m[1], m[2]); }
    else if (h === '/cart') { html = await vCart(); bind = bindCart; }
    else html = notFound();
  } catch (e) {
    console.error(e);
    html = `<div class="empty">Не получилось загрузить: ${esc(e.message)}. <a href="#/">Обновить</a></div>`;
  }
  if (my !== busy) return;
  const focusSel = opt.keepFocus, caret = focusSel && $(focusSel) ? $(focusSel).selectionStart : null;
  main.innerHTML = html;
  renderMath(main);
  bindTaskButtons(main);
  bind();
  $$('#nav [data-nav]').forEach(a => a.toggleAttribute('aria-current', false));
  const top = '/' + (h.split('/')[1] || '');
  const cur = $(`#nav [data-nav="${top === '/theory' ? '/theory' : top === '/cart' ? '/cart' : '/'}"]`);
  if (cur) cur.setAttribute('aria-current', 'page');
  if (focusSel && $(focusSel)) { const el = $(focusSel); el.focus(); if (caret != null) el.setSelectionRange(caret, caret); }
  if (opt.keepScroll || opt.keepFocus) scrollTo(0, y); else if (!/^\/theory\/\d+\/./.test(h)) scrollTo(0, 0);
  document.title = (main.querySelector('h1')?.textContent || 'ОГЭ · математика') + ' — Стартум';
}

async function boot() {
  loadCart();
  cartBadge();
  window.addEventListener('hashchange', () => render());
  await render();
  const who = await whoami();
  if (who && who.me && who.me.role !== 's') {
    S.me = who.me; S.groupsList = who.groups; S.teacher = true;
    document.documentElement.dataset.role = 't';
    $('#nav-cart').hidden = false;
    await loadTeacherBank();
    render({ keepScroll: true });
  }
}
boot();
