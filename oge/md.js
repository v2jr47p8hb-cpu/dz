// Небольшой Markdown для страниц теории: заголовки (## Текст {#якорь}), абзацы, списки, таблицы,
// цитаты, **жирный**, *курсив*, `код`, [ссылки](#/…), --- и формулы $…$ / $$…$$ (их рисует tex.js).
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function inline(s) {
  const math = [];
  s = s.replace(/\$\$[\s\S]+?\$\$|\$(?:\\\$|[^$])+?\$/g, m => { math.push(m); return `\u0000${math.length - 1}\u0000`; });
  s = esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\w)/g, '$1<i>$2</i>')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, t, h) => {
      const ext = /^https?:/.test(h);
      return `<a href="${h}"${ext ? ' target="_blank" rel="noopener noreferrer"' : ''}>${t}${ext ? ' ↗' : ''}</a>`;
    });
  return s.replace(/\u0000(\d+)\u0000/g, (m, i) => esc(math[+i]));
}

const slug = s => s.toLowerCase().replace(/<[^>]+>/g, '').replace(/[^a-zа-яё0-9]+/gi, '-').replace(/^-|-$/g, '');

export function md(src) {
  const lines = src.replace(/\r/g, '').split('\n');
  const out = [], toc = [];
  let i = 0;
  const para = [];
  const flush = () => { if (para.length) { out.push(`<p>${inline(para.join(' '))}</p>`); para.length = 0; } };
  while (i < lines.length) {
    const l = lines[i];
    if (!l.trim()) { flush(); i++; continue; }
    let m;
    if ((m = l.match(/^(#{1,3})\s+(.*?)(?:\s*\{#([\w-]+)\})?\s*$/))) {
      flush();
      const lv = m[1].length, id = m[3] || slug(m[2]);
      if (lv === 2) toc.push({ id, title: m[2] });
      out.push(`<h${lv} id="${esc(id)}">${inline(m[2])}</h${lv}>`);
      i++; continue;
    }
    if (/^\$\$/.test(l.trim())) {
      flush();
      const buf = [l];
      if (!(l.trim().length > 2 && l.trim().endsWith('$$'))) {
        while (++i < lines.length) { buf.push(lines[i]); if (lines[i].trim().endsWith('$$')) break; }
      }
      out.push(`<div class="katex-block">${esc(buf.join('\n'))}</div>`);
      i++; continue;
    }
    if (/^---+\s*$/.test(l)) { flush(); out.push('<hr>'); i++; continue; }
    if (/^>\s?/.test(l)) {
      flush();
      const buf = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^>\s?/, ''));
      out.push(`<blockquote>${md(buf.join('\n')).html}</blockquote>`);
      continue;
    }
    if (/^\|/.test(l)) {
      flush();
      const rows = [];
      while (i < lines.length && /^\|/.test(lines[i])) rows.push(lines[i++]);
      const cells = r => r.replace(/^\||\|\s*$/g, '').split('|').map(c => c.trim());
      const hasHead = rows[1] && /^\|?[\s:|-]+\|?$/.test(rows[1]);
      let h = '<table>';
      if (hasHead) h += `<thead><tr>${cells(rows[0]).map(c => `<th>${inline(c)}</th>`).join('')}</tr></thead>`;
      h += '<tbody>' + rows.slice(hasHead ? 2 : 0).map(r => `<tr>${cells(r).map(c => `<td>${inline(c)}</td>`).join('')}</tr>`).join('') + '</tbody></table>';
      out.push(h);
      continue;
    }
    if ((m = l.match(/^(\s*)([-*]|\d+[.)])\s+/))) {
      flush();
      const ordered = /\d/.test(m[2]);
      const items = [];
      while (i < lines.length) {
        const x = lines[i].match(/^(\s*)([-*]|\d+[.)])\s+(.*)$/);
        if (x && x[1].length < 2) { items.push([x[3]]); i++; continue; }
        if (items.length && lines[i].trim() && /^\s{2,}/.test(lines[i])) { items[items.length - 1].push(lines[i]); i++; continue; }
        break;
      }
      const tag = ordered ? 'ol' : 'ul';
      out.push(`<${tag}>` + items.map(it => {
        const [first, ...rest] = it;
        const sub = rest.length ? md(rest.map(r => r.replace(/^\s{2,4}/, '')).join('\n')).html : '';
        return `<li>${inline(first)}${sub}</li>`;
      }).join('') + `</${tag}>`);
      continue;
    }
    para.push(l.trim());
    i++;
  }
  flush();
  return { html: out.join('\n'), toc };
}
