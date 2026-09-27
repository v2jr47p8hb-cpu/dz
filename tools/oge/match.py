"""Сопоставление задач ФИПИ с метаданными «Решу ОГЭ» по числам и словам условия.

Выход: cache/match.json — {fid: {sid, type, cat, proto, ans, srcs, score}}.
"""
import re, json, glob, html, collections
from common import CACHE

STOP = set("""корень корня корней из начало конец аргумента аргумент умножить делить дробь числитель знаменатель
степени степень квадрате кубе минус плюс равно левая правая круглая квадратная скобка скобки система выражений
выражение выражения модуль логарифм косинус синус тангенс котангенс пи градусов градус больше меньше или равно
найдите найти значение ответ дайте запишите укажите какие какое каких которые который этого этой того той также
тогда если равен равна равны равно""".split())
NUM = re.compile(r"\d+(?:[.,]\d+)?")
WORD = re.compile(r"[а-яё]{4,}", re.I)


def norm_num(x):
    x = x.replace(".", ",").lstrip("0") or "0"
    if x.startswith(","):
        x = "0" + x
    return x


OPS_TEX = [(r"\\cdot|\\times", " opmul "), (r"\\frac|:", " opdiv "), (r"\+", " opplus "), (r"-", " opminus "),
           (r"\\sqrt", " opsqrt ")]
OPS_RU = [(r"умножить|умноженн", " opmul "), (r"дробь|делить|деленн|разделить|\bover\b", " opdiv "), (r"плюс", " opplus "),
          (r"минус", " opminus "), (r"корень", " opsqrt ")]
OP = re.compile(r"op(?:mul|div|plus|minus|sqrt)")


def fipi_plain(h):
    h = re.sub(r"<[^>]+>", " ", h)
    h = html.unescape(h)

    def math(m):
        x = m.group(1).replace("{,}", ",")
        for a, b in OPS_TEX:
            x = re.sub(a, b, x)
        return " " + x + " "
    h = re.sub(r"\$([^$]*)\$", math, h)
    return h


def sd_plain(t):
    t = t.replace("\u2060", "").replace("\\times", " opmul ")
    for a, b in OPS_RU:
        t = re.sub(a, b, t, flags=re.I)
    return t


def feats(text):
    seq = [norm_num(n) for n in NUM.findall(text)]
    nums = collections.Counter(seq)
    words = {w.lower().replace("ё", "е") for w in WORD.findall(text)} - STOP
    ops = collections.Counter(OP.findall(text))
    return nums, words, seq, ops


def nsim(a, b):
    import difflib
    return 0.5 * msim(a[0], b[0]) + 0.5 * (difflib.SequenceMatcher(None, a[2], b[2]).ratio() if (a[2] or b[2]) else 1.0)


def msim(a, b):
    if not a and not b:
        return 1.0
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / union if union else 0.0


def jac(a, b):
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b) if (a | b) else 0.0


def main():
    fipi = [json.loads(l) for l in open(CACHE / "tasks_fipi.jsonl", encoding="utf8")]
    groups = {json.loads(l)["gid"]: json.loads(l) for l in open(CACHE / "groups_fipi.jsonl", encoding="utf8")}
    sd = {}
    for f in glob.glob(str(CACHE / "sdam" / "protos" / "*.jsonl")):
        for l in open(f, encoding="utf8"):
            r = json.loads(l)
            # один sid может встречаться в нескольких прототипах/категориях — оставляем первый
            sd.setdefault(r["sid"], r)
    sd = list(sd.values())
    print("записей Решу ОГЭ:", len(sd))
    for r in sd:
        r["_f"] = feats(sd_plain(r["sig"]))
        r["_n"], r["_w"] = r["_f"][0], r["_f"][1]
        r["_t"] = feats(sd_plain(r.get("textSig") or ""))
    inv = collections.defaultdict(list)
    for i, r in enumerate(sd):
        for k in list(r["_n"]) + list(r["_w"]):
            inv[k].append(i)
    df = {k: len(v) for k, v in inv.items()}
    gfe = {gid: feats(fipi_plain(g["html"])[:1500]) for gid, g in groups.items()}
    empty = feats("")

    res, stats = {}, collections.Counter()
    for t in fipi:
        text = fipi_plain(t["html"] + " " + " ".join(t["options"]))
        f = feats(text)
        n, w = f[0], f[1]
        keys = sorted(list(n) + list(w), key=lambda k: df.get(k, 10**9))[:12]
        cand = collections.Counter()
        for k in keys:
            if df.get(k, 0) > 3000:
                continue
            for i in inv.get(k, []):
                cand[i] += 1
        best, bs, second = None, 0.0, 0.0
        scored = []
        for i, _ in cand.most_common(400):
            r = sd[i]
            ns = nsim(f, r["_f"])
            s = 0.5 * ns + 0.35 * jac(w, r["_w"]) + 0.15 * msim(f[3], r["_f"][3])
            if n and ns < 0.75:
                s = min(s, 0.5)
            if t.get("group") and r.get("textSig"):
                g = gfe.get(t["group"], empty)
                s = 0.4 * s + 0.6 * (0.5 * nsim(g, r["_t"]) + 0.5 * jac(g[1], r["_t"][1]))
            scored.append((s, i))
            if s > bs:
                best, bs, second = r, s, bs
            elif s > second:
                second = s
        scored.sort(reverse=True)
        # запасные кандидаты — для проверки ответа через ФИПИ, если ответ лучшего не подтвердится
        alts = [{"sid": sd[i]["sid"], "type": sd[i]["type"], "cat": sd[i]["cat"], "proto": sd[i]["proto"],
                 "ans": sd[i]["ans"], "srcs": sd[i]["srcs"], "score": round(s2, 3)} for s2, i in scored[1:(9 if t.get("group") else 4)] if s2 >= 0.6]
        if best and bs >= 0.7:
            res[t["fid"]] = {"sid": best["sid"], "type": best["type"], "cat": best["cat"], "proto": best["proto"],
                             "ans": best["ans"], "srcs": best["srcs"], "score": round(bs, 3), "second": round(second, 3),
                             "alts": alts}
            stats["ok"] += 1
        else:
            stats["none"] += 1
            if best:
                res[t["fid"]] = {"weak": True, "sid": best["sid"], "type": best["type"], "score": round(bs, 3)}
    json.dump(res, open(CACHE / "match.json", "w", encoding="utf8"), ensure_ascii=False)
    print(stats)
    ty = collections.Counter(v["type"] for v in res.values() if not v.get("weak"))
    print(sorted(ty.items(), key=lambda x: (x[0].startswith("Д"), int(x[0].lstrip("Д")))))


if __name__ == "__main__":
    main()
