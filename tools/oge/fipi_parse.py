"""cache/fipi/page_*.html → cache/tasks_fipi.jsonl + cache/groups_fipi.jsonl.

Условие хранится как «чистый» HTML (p, br, b, i, u, sub, sup, table, img) с формулами в $…$ (LaTeX).
Картинки получают локальные имена (oge/img/<имя>), удалённый адрес — в поле imgs.
"""
import re, json, glob, html
from bs4 import BeautifulSoup, NavigableString, Tag
from common import CACHE, FIPI, FIPI_PROJ
import mathml

KIND = {
    "Впишите правильный ответ.": "short",
    "Дайте развернутый ответ.": "long",
    "Выберите правильный ответ.": "choice",
    "Выберите один или несколько правильных ответов.": "multi",
    "Установите соответствие и впишите ответ.": "match",
}
KEEP = {"p", "br", "b", "i", "u", "sub", "sup", "table", "tr", "td", "th", "strong", "em"}
PIC = re.compile(r"ShowPicture(Q?)\('([^']+)'")
LATIN_I = re.compile(r"^[A-Za-z]{1,3}[0-9]?$")


class Ctx:
    def __init__(self, name, base=None):
        self.name = name      # префикс локальных имён картинок
        self.base = base      # files_abs_location для групп
        self.imgs = []        # [{src, local, inline}]
        self.flags = set()


def img_tag(ctx, m, inline):
    q, path = m.group(1), m.group(2)
    if q:
        url = "https://oge.fipi.ru/" + path
    else:
        url = "https://oge.fipi.ru/" + (ctx.base or "") + path
    ext = path.rsplit(".", 1)[-1].lower()
    local = f"{ctx.name}-{len(ctx.imgs) + 1}.{ext}"
    ctx.imgs.append({"src": url, "local": local, "inline": inline})
    if inline:
        ctx.flags.add("inline-img")
    return f'<img src="{local}"{" class=i" if inline else ""}>'


def enclosing_p_has_text(node):
    p = node.find_parent(["p", "td"])
    if not p:
        return False
    t = "".join(s for s in p.find_all(string=True) if not isinstance(s.parent, Tag) or s.parent.name != "script")
    t = t.replace("\xa0", " ").strip()
    return bool(t) or len(p.find_all("script")) > 1 and p.name == "p"


def san(node, ctx):
    if isinstance(node, NavigableString):
        if node.__class__.__name__ in ("Comment", "Declaration", "Doctype", "ProcessingInstruction"):
            return ""
        s = str(node).replace("­", "").replace("\r", " ").replace("\n", " ")
        if "$" in s:
            ctx.flags.add("dollar")
            s = s.replace("$", "\\$")
        return html.escape(s, quote=False)
    n = node.name
    if n.startswith("m:"):
        if n == "m:math":
            tex = mathml.to_latex(node)
            pl = mathml.plain_or_none(tex)
            if pl is not None:
                return html.escape(pl, quote=False)
            return "$" + html.escape(tex, quote=False) + "$" if tex.strip() else ""
        return ""
    if n == "script":
        out = []
        for m in PIC.finditer(node.get_text()):
            out.append(img_tag(ctx, m, enclosing_p_has_text(node)))
        return "".join(out)
    if n in ("input", "select", "form", "style", "noscript", "option", "button"):
        return ""
    if n == "table":
        rows = [tr for tr in node.find_all("tr") if tr.find_parent("table") is node]
        cells = [td for td in node.find_all(["td", "th"]) if td.find_parent("table") is node]
        def img_only(td):
            return td.find("script") and not td.get_text(" ", strip=True).replace("\xa0", "").strip(" ;')(") \
                or (td.find("script") and all(PIC.search(sc.get_text()) for sc in td.find_all("script"))
                    and not "".join(t for t in td.find_all(string=True) if t.parent.name != "script").strip())
        if len(rows) <= 1 and (len(cells) <= 1 or (len(cells) == 2 and any(img_only(c) for c in cells))):
            return "".join("<div>" + "".join(san(c, ctx) for c in td.children) + "</div>" for td in cells)
    inner = "".join(san(c, ctx) for c in node.children)
    if n == "i" and LATIN_I.match(node.get_text().strip()) and not node.find(["img", "script"]):
        return "$" + node.get_text().strip() + "$"
    if n in KEEP:
        n2 = {"strong": "b", "em": "i", "th": "td"}.get(n, n)
        if n2 == "br":
            return "<br>"
        attrs = ""
        if n2 == "p" and (node.get("align") == "center"):
            attrs = " class=c"
        if n2 == "td":
            for a in ("colspan", "rowspan"):
                if node.get(a):
                    attrs += f' {a}="{node.get(a)}"'
        if n2 == "table":
            ctx.flags.add("table")
        if n2 in ("b", "i", "u", "sub", "sup") and not inner.strip():
            return inner
        return f"<{n2}{attrs}>{inner}</{n2}>"
    return inner


def tidy(h):
    h = re.sub(r"[ \t ]+", lambda m: " " if " " not in m.group(0) else " ", h)
    h = re.sub(r"<p( class=c)?>\s*( |&nbsp;)?\s*</p>", "", h)
    h = re.sub(r"(<br>\s*)+</p>", "</p>", h)
    h = re.sub(r"<p( class=c)?>\s*(<br>\s*)+", r"<p\1>", h)
    h = re.sub(r"\$\s*\$", "", h)
    h = re.sub(r"<p( class=c)?>\s*<p( class=c)?>", r"<p\2>", h)
    h = re.sub(r"</p>\s*</p>", "</p>", h)
    h = re.sub(r"<p>\s*</p>", "", h)
    h = re.sub(r"\s+", " ", h).strip()
    return h


def info(qid, soup):
    d = soup.find(id="i" + qid)
    kes, atype = [], ""
    if d:
        for tr in d.select("tr"):
            nm = tr.select_one(".param-name")
            if not nm:
                continue
            if "КЭС" in nm.get_text():
                for div in tr.select(".param-row div"):
                    t = div.get_text(" ", strip=True)
                    m = re.match(r"(\d+(?:\.\d+)*)\s*(.*)", t)
                    if m:
                        kes.append({"code": m.group(1), "name": m.group(2)})
            elif "Тип ответа" in nm.get_text():
                atype = tr.find_all("td")[-1].get_text(strip=True)
    return kes, atype


def parse_task(q, soup):
    qid = q["id"][1:]
    guid = q.find("input", attrs={"name": "guid"})["value"]
    hint = q.select_one(".hint").get_text(strip=True)
    gnum = None
    m = re.match(r"Задание №(\d+)\.\s*(.*)", hint)
    if m:
        gnum, hint = int(m.group(1)), m.group(2)
    ctx = Ctx(qid)
    cell = q.select_one("td.cell_0")
    text = tidy("".join(san(c, ctx) for c in cell.children)) if cell else ""
    options = []
    dt = q.select_one("table.distractors-table")
    if dt:
        for tr in dt.find_all("tr", recursive=False):
            tds = tr.find_all("td", recursive=False)
            if tds:
                options.append(tidy("".join(san(c, ctx) for c in tds[-1].children)))
    match_cols = []
    at = q.select_one("table.answer-table")
    if at:
        first = at.find("tr")
        match_cols = [td.get_text(strip=True) for td in first.find_all("td")]
    kes, atype = info(qid, soup)
    return {
        "fid": qid, "guid": guid, "kind": KIND.get(hint, hint), "hint": hint, "gnum": gnum,
        "kes": kes, "atype": atype, "html": text, "options": options, "matchCols": match_cols,
        "imgs": ctx.imgs, "flags": sorted(ctx.flags),
    }


def parse_group(q):
    scr = " ".join(s.get_text() for s in q.find_all("script"))
    m = re.search(r"files_abs_location='([^']+)'", scr)
    base = m.group(1) if m else ""
    gid = base.rstrip("/").split("/")[-1]
    ctx = Ctx("g" + gid[:10].lower(), base)
    body = []
    for c in q.children:
        if isinstance(c, Tag) and c.get("id") == "hint":
            continue
        body.append(san(c, ctx))
    return {"gid": gid, "html": tidy("".join(body)), "imgs": ctx.imgs, "flags": sorted(ctx.flags)}


def main():
    tasks, groups, seen = [], [], set()
    cur_group = None
    for f in sorted(glob.glob(str(CACHE / "fipi" / "page_*.html"))):
        soup = BeautifulSoup(open(f, encoding="utf8").read(), "lxml")
        for q in soup.select("div.qblock"):
            if not q.get("id"):
                g = parse_group(q)
                if g["gid"] not in {x["gid"] for x in groups}:
                    groups.append(g)
                cur_group = g["gid"]
                continue
            t = parse_task(q, soup)
            if t["gnum"] is None:
                cur_group = None
            else:
                t["group"] = cur_group
            if t["fid"] in seen:
                continue
            seen.add(t["fid"])
            tasks.append(t)
    with open(CACHE / "tasks_fipi.jsonl", "w", encoding="utf8") as w:
        for t in tasks:
            w.write(json.dumps(t, ensure_ascii=False) + "\n")
    with open(CACHE / "groups_fipi.jsonl", "w", encoding="utf8") as w:
        for g in groups:
            w.write(json.dumps(g, ensure_ascii=False) + "\n")
    from collections import Counter
    print("заданий:", len(tasks), "групп:", len(groups))
    print(Counter(t["kind"] for t in tasks))
    print("в группах:", sum(1 for t in tasks if t.get("group")))
    print("флаги:", Counter(f for t in tasks for f in t["flags"]))
    print("незнакомые теги MathML:", mathml.UNKNOWN)
    print("картинок:", sum(len(t["imgs"]) for t in tasks) + sum(len(g["imgs"]) for g in groups))


if __name__ == "__main__":
    main()
