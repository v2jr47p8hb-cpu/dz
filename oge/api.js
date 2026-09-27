// Обращения к серверу кабинета (Google Apps Script) — тот же протокол, что в основном сайте:
// POST {fn:'webCall', args:[сессия, имяФункции, аргументы]} → {ok, data | error, code}.
const URL_ = 'https://script.google.com/macros/s/AKfycbyCRvM9lvBYQARcGSCFEqgoJTlMCFOyWVYuabAsFmUOG8KpcziNb6UTBxXDZ5iuYbcF/exec';

const ls = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* приватный режим */ } },
};

export const session = () => ls.get('startum_s');
export const store = ls;

export class ApiError extends Error {
  constructor(msg, code) { super(msg); this.code = code || ''; }
  get authLost() { return this.code === 'auth' || /Войди на сайт заново|Сессия закончилась|Доступ сброшен/.test(this.message); }
}

async function raw(fn, ...args) {
  let last;
  for (let i = 0; i < 2; i++) {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 40000);
    try {
      const txt = await (await fetch(URL_, {
        method: 'POST', redirect: 'follow', signal: ctl.signal,
        headers: { 'Content-Type': 'text/plain;charset=utf-8' },
        body: JSON.stringify({ fn, args }),
      })).text();
      let m;
      try { m = JSON.parse(txt); } catch { throw new ApiError('Сервер ответил странно. Попробуй ещё раз через минуту.', 'net'); }
      if (!m.ok) throw new ApiError(m.error || 'Что-то пошло не так.', m.code);
      return m.data;
    } catch (e) {
      last = e instanceof ApiError ? e : new ApiError(e.name === 'AbortError' ? 'Сервер долго не отвечает.' : 'Нет связи с сервером.', 'net');
      if (last.code !== 'net' && last.code !== 'busy') throw last;
      await new Promise(r => setTimeout(r, 1200));
    } finally { clearTimeout(t); }
  }
  throw last;
}

export const call = (name, ...args) => raw('webCall', session(), name, args);

// Кто вошёл: берём кэш кабинета (startum_boot), иначе спрашиваем сервер.
export async function whoami() {
  if (!session()) return null;
  try {
    const b = JSON.parse(ls.get('startum_boot') || 'null');
    if (b && b.me) return { me: b.me, groups: (b.data && b.data.groups) || [] };
  } catch { /* битый кэш */ }
  try {
    const b = await raw('webBoot', session(), '');
    if (b && b.me) return { me: b.me, groups: (b.data && b.data.groups) || [] };
  } catch (e) { if (!(e instanceof ApiError && e.authLost)) console.warn('whoami:', e); }
  return null;
}
