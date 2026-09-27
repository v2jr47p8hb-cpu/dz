// Формулы: $…$ и $$…$$ в текстовых узлах → KaTeX (window.katex из vendor/katex).
const RE = /\$\$([\s\S]+?)\$\$|\$((?:\\\$|[^$])+?)\$/g;

export function renderMath(root) {
  const K = window.katex;
  if (!K || !root) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: n => (n.nodeValue.includes('$') && !n.parentElement.closest('.katex,code,pre,script,style,textarea'))
      ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT,
  });
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  // формула может быть разорвана тегами (<i>, <br>) — склеиваем соседние текстовые узлы только внутри одного узла
  for (const n of nodes) {
    const s = n.nodeValue;
    RE.lastIndex = 0;
    if (!RE.test(s)) continue;
    RE.lastIndex = 0;
    const frag = document.createDocumentFragment();
    let pos = 0, m;
    while ((m = RE.exec(s))) {
      if (m.index > pos) frag.append(s.slice(pos, m.index).replace(/\\\$/g, '$'));
      const span = document.createElement('span');
      const tex = m[1] != null ? m[1] : m[2];
      try {
        K.render(tex, span, { throwOnError: false, displayMode: m[1] != null, strict: 'ignore', output: 'html' });
      } catch { span.textContent = tex; }
      frag.append(span);
      pos = m.index + m[0].length;
    }
    if (pos < s.length) frag.append(s.slice(pos).replace(/\\\$/g, '$'));
    n.replaceWith(frag);
  }
}
