"""Сборка данных сайта oge/data/* и файла импорта в банк кабинета (tools/oge/out/import_oge_math.csv).

Ответы в публичные файлы сайта НЕ попадают — только в CSV для импорта (он в .gitignore).
"""
import re, json, csv, html, datetime, collections
from common import CACHE, OUT, SITE
from nums import NUMS

GROUP_TITLES = [
    (r"шин[аыу]|маркиров", "Шины"), (r"печ[ьи]|парн", "Печь для бани"), (r"тариф|интернет|мобильн|трафик", "Тарифы"),
    (r"формат[аы]? листов|листы бумаги|бумаг", "Листы бумаги"), (r"квартир", "Квартира"),
    (r"теплиц", "Теплица"), (r"ОСАГО|страхов", "ОСАГО"), (r"зонт", "Зонт"), (r"террас", "Террасы"),
    (r"метро", "Метро"), (r"колес[оа] обозрения", "Колесо обозрения"),
    (r"домохозяйств|участ(ок|ка)|дачн", "Участок"), (r"деревн|посёлк|поселк|шоссе|село", "План местности"),
]
PAST = re.compile(r"^(ОГЭ|Демонстрац|Пробный|Тренировочн|Досрочн|Диагностич)", re.I)


def plain_parts(h):
    """HTML условия → (текст с $…$, [картинки-блоки], простое ли)."""
    simple = "<table" not in h and 'class=i' not in h
    imgs = re.findall(r'<img src="([^"]+)"', h)
    t = h
    t = re.sub(r"<sub>(.*?)</sub>", r"$_{\1}$", t)
    t = re.sub(r"<sup>(.*?)</sup>", r"$^{\1}$", t)
    t = re.sub(r"<img[^>]*>", "", t)
    t = re.sub(r"<br>", "\n", t)
    t = re.sub(r"</(p|div)>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t).replace(" ", " ")
    t = "\n".join(re.sub(r"[ \t]+", " ", x).strip() for x in t.split("\n"))
    t = re.sub(r"\n{2,}", "\n", t).strip()
    return t, imgs, simple


def group_title(g):
    txt = re.sub(r"<[^>]+>", " ", g["html"])
    for pat, name in GROUP_TITLES:
        if re.search(pat, txt, re.I):
            return name
    return "Сюжет"


def ans_for_bank(t, v):
    a = v["ans"]
    if t["kind"] == "multi":
        return "".join(str(i + 1) for i, c in enumerate(a) if c == "1") + "*"
    return a


def main():
    fipi = [json.loads(l) for l in open(CACHE / "tasks_fipi.jsonl", encoding="utf8")]
    groups = {json.loads(l)["gid"]: json.loads(l) for l in open(CACHE / "groups_fipi.jsonl", encoding="utf8")}
    match = json.load(open(CACHE / "match.json", encoding="utf8"))
    vf = CACHE / "verify.json"
    ver = json.load(open(vf, encoding="utf8")) if vf.exists() else {}
    cats = {}
    for fn in ("cats.json", "cats_all.json"):
        p = CACHE / "sdam" / fn
        if p.exists():
            for c in json.load(open(p, encoding="utf8")):
                cats[c["cat"]] = c
    order = {c: i for i, c in enumerate(cats)}

    tasks, snaps = [], []
    stat = collections.Counter()
    for t in fipi:
        m = match.get(t["fid"])
        if m and m.get("weak"):
            m = None
        v = ver.get(t["fid"])
        if m and v and v.get("ok") and v.get("sid") != m["sid"]:
            alt = next((a for a in m.get("alts", []) if a["sid"] == v["sid"]), None)
            if alt:
                m = alt
        typ = m["type"] if m else None
        n = int(typ) if typ and typ.isdigit() else 0
        # развёрнутые задачи с «кратким» типом и наоборот — не доверяем такому сопоставлению номера
        if n and (t["kind"] == "long") != (n >= 20):
            stat["kind-mismatch"] += 1
            n = 0
        sub = m["cat"] if m else "none"
        o = {
            "id": "om-" + t["fid"], "fid": t["fid"], "n": n, "sub": sub, "proto": m["proto"] if m else None,
            "kind": t["kind"], "html": t["html"], "opts": t["options"], "mc": t["matchCols"],
            "g": t.get("group"), "gk": t.get("gnum"), "sid": m["sid"] if m else None,
            "src": [s for s in (m["srcs"] if m else []) if PAST.match(s)][:3],
            "kes": [k["code"] for k in t["kes"]], "flags": t["flags"],
        }
        verified = bool(v and v.get("ok"))
        o["bank"] = bool(n) and (t["kind"] == "long" or verified)
        if o["bank"]:
            stat["bank"] += 1
        o["_ans"] = (ans_for_bank(t, v) if verified else (m["ans"] if (m and t["kind"] == "long") else ""))
        o["_t"] = t
        tasks.append(o)
        stat["n%s" % (n or "0")] += 1

    # похожие: число задач в прототипе
    pc = collections.Counter(o["proto"] for o in tasks if o["proto"])
    for o in tasks:
        o["pc"] = pc.get(o["proto"], 0)

    # сюжеты № 1–5
    gout, gcount = {}, collections.Counter()
    for gid, g in groups.items():
        mem = [o for o in tasks if o["g"] == gid]
        name = group_title(g)
        gcount[name] += 1
        gout[gid] = {"id": gid, "title": f"{name} · {gcount[name]}", "html": g["html"],
                     "nums": sorted({o["n"] for o in mem if o["n"]}), "tasks": [o["id"] for o in sorted(mem, key=lambda x: x["gk"] or 0)]}
    for gid, g in gout.items():
        if gcount[g["title"].split(" · ")[0]] == 1:
            g["title"] = g["title"].split(" · ")[0]

    # файлы сайта
    data = SITE / "data"
    (data / "n").mkdir(parents=True, exist_ok=True)
    pub = lambda o: {k: v for k, v in o.items() if not k.startswith("_") and v not in (None, [], "")}
    index = {"generated": datetime.date.today().strftime("%d.%m.%Y"), "total": len(tasks), "nums": []}
    loc = {}
    for n in list(range(1, 26)) + [0]:
        mem = [o for o in tasks if o["n"] == n]
        mem.sort(key=lambda o: (order.get(o["sub"], 999), o["proto"] or 0, o["fid"]))
        subs = collections.OrderedDict()
        for o in mem:
            if o["sub"] not in subs:
                c = cats.get(o["sub"])
                nm = (c["name"] if c else "Не разобрано").replace("­", "")
                if n == 0 and c and not str(c["sec"]).isdigit():
                    nm = re.sub(r"^Задания\s+", "", str(c["sec"]).split(".")[0]) + " · " + nm
                subs[o["sub"]] = {"id": o["sub"], "name": nm, "count": 0}
            subs[o["sub"]]["count"] += 1
        key = "arch" if n == 0 else n
        json.dump({"n": n, "tasks": [pub(o) for o in mem]}, open(data / "n" / f"{str(key).zfill(2)}.json", "w", encoding="utf8"),
                  ensure_ascii=False, separators=(",", ":"))
        for o in mem:
            loc[o["id"]] = key
            if o["proto"]:
                loc["p%s" % o["proto"]] = key
        entry = {"n": n, "count": len(mem), "bank": sum(o["bank"] for o in mem), "subs": list(subs.values())}
        if n:
            title, block, pts, about = NUMS[n]
            entry.update(title=title, block=block, pts=pts, about=about)
            index["nums"].append(entry)
        else:
            entry.update(title="Архив и не разобранные", about="Задачи старых форматов ОГЭ и задачи, которым пока не нашёлся номер КИМ 2026")
            index["archive"] = entry
    json.dump(index, open(data / "index.json", "w", encoding="utf8"), ensure_ascii=False, indent=0)
    json.dump(loc, open(data / "loc.json", "w", encoding="utf8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(gout, open(data / "groups.json", "w", encoding="utf8"), ensure_ascii=False, separators=(",", ":"))

    # импорт в банк кабинета
    rows, snap_need = [], {}
    for o in tasks:
        if not o["bank"]:
            continue
        t = o["_t"]
        body, imgs, simple = plain_parts(t["html"])
        oimgs = [x for op in t["options"] for x in re.findall(r'<img src="([^"]+)"', op)]
        opt_plain = [plain_parts(op) for op in t["options"]]
        simple = simple and len(imgs) + len(oimgs) <= 1 and all(p[2] for p in opt_plain) and not oimgs
        if t["options"] and simple:
            body += "\n" + "\n".join(f"{i + 1}) {p[0]}" for i, p in enumerate(opt_plain))
        hint = {"match": "Ответ — цифры под буквами " + ", ".join(t["matchCols"]) + " подряд, без пробелов.",
                "multi": "Ответ — номера верных вариантов подряд, без пробелов.",
                "choice": "Ответ — номер верного варианта."}.get(t["kind"], "")
        img = ""
        if o["g"]:
            if simple and not imgs:
                img = f"oge/snap/g-{o['g'][:10].lower()}.png"
                snap_need[img] = {"kind": "group", "gid": o["g"]}
            else:
                img = f"oge/snap/{o['fid']}.png"
                snap_need[img] = {"kind": "task", "id": o["id"], "ctx": True}
                body = "Прочитайте текст и условие на рисунке."
        elif simple:
            img = f"oge/img/{imgs[0]}" if imgs else ""
        else:
            img = f"oge/snap/{o['fid']}.png"
            snap_need[img] = {"kind": "task", "id": o["id"], "ctx": False}
            body = "Условие — на рисунке."
        if hint and hint not in body:
            body += "\n" + hint
        rows.append([o["id"], "ОГЭ", "математика", o["n"], (cats.get(o["sub"]) or {}).get("name", "").replace("­", ""),
                     body, img, o["_ans"], 2 if t["kind"] == "long" else 1, "long" if t["kind"] == "long" else "short"])
    rows.sort(key=lambda r: (r[3], r[0]))
    with open(OUT / "import_oge_math.csv", "w", encoding="utf8", newline="") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writerows(rows)
    json.dump(snap_need, open(CACHE / "snap_need.json", "w", encoding="utf8"), ensure_ascii=False, indent=0)

    # отчёт
    rep = [f"# Отчёт сборки банка ОГЭ-математики ({index['generated']})", "",
           f"Всего заданий ФИПИ: **{len(tasks)}**. Разложено по № 1–25: **{sum(1 for o in tasks if o['n'])}**. "
           f"В архиве/не разобрано: **{sum(1 for o in tasks if not o['n'])}**.",
           f"Годятся для ДЗ (в CSV): **{len(rows)}** (краткий ответ подтверждён ФИПИ или часть 2). Снимков условий нужно: {len(snap_need)}.", "",
           "| № | Тема | Задач | В банк | Подтипов |", "|---|---|---|---|---|"]
    for e in index["nums"]:
        rep.append(f"| {e['n']} | {e['title']} | {e['count']} | {e['bank']} | {len(e['subs'])} |")
    a = index["archive"]
    rep.append(f"| — | {a['title']} | {a['count']} | {a['bank']} | {len(a['subs'])} |")
    rep += ["", "Прочее: " + ", ".join(f"{k}: {v}" for k, v in sorted(stat.items()) if not k.startswith("n"))]
    (OUT / "report.md").write_text("\n".join(rep), encoding="utf8")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
