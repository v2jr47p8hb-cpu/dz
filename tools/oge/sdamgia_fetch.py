"""Решу ОГЭ: только метаданные для разметки задач ФИПИ (номер КИМ, подтип, прототип, ответ, id для ссылки).

Условия и решения не сохраняем — только «подпись» текста (слова и числа) для сопоставления.
Результат: cache/sdam/protos/<cat>_<proto>.jsonl, cache/sdam/cats.json.
"""
import re, json, sys
from bs4 import BeautifulSoup
from common import Http, CACHE

BASE = "https://oge.sdamgia.ru"
D = CACHE / "sdam"
(D / "protos").mkdir(parents=True, exist_ok=True)


def sig_text(node):
    for img in node.find_all("img"):
        img.replace_with(" " + (img.get("alt") or "") + " ")
    t = node.get_text(" ", strip=True).replace("\xad", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", t)


def parse_probs(html):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for p in soup.select("div.prob_maindiv"):
        num = p.select_one(".prob_nums")
        if not num:
            continue
        a = num.find("a")
        sid = int(a.get_text(strip=True)) if a else None
        m = re.search(r"Тип\s*(Д?\d+)", num.get_text(" ", strip=True).replace("\xa0", " "))
        typ = m.group(1) if m else None
        info = p.select_one(".align-left")
        srcs = [x.get_text(" ", strip=True).replace("\xad", "") for x in info.select("a")] if info else []
        bodies = [b for b in p.select(".pbody") if not b.find_parent(class_="probtext")]
        body = bodies[0] if bodies else None
        ans = p.select_one(".answer")
        pt = p.select_one(".probtext")
        tid = pt.get("id", "").replace("text", "") if pt else None
        ptsig = sig_text(pt)[:400] if pt else ""
        out.append({
            "sid": sid, "type": typ, "srcs": srcs,
            "sig": sig_text(body) if body else "",
            "ans": re.sub(r"^Ответ:\s*", "", ans.get_text(" ", strip=True)) if ans else "",
            "hasSol": bool(p.select_one(".solution")),
            "textId": tid, "textSig": ptsig,
        })
    return out


def main(only_main=True):
    cats = json.load(open(D / "catalog.json"))
    h = Http(delay=2.0, headers={"Accept-Encoding": "gzip, deflate"})
    todo = []
    for sec in cats:
        is_main = sec["num"] != "?"
        if only_main and not is_main:
            continue
        for cid, cname, cnt in sec["cats"]:
            if cnt == "0":
                continue
            todo.append((sec["num"] if is_main else sec["title"], cid, cname))
    meta = []
    for secnum, cid, cname in todo:
        f = D / f"cat_{cid}.json"
        if f.exists():
            protos = json.load(open(f))
        else:
            r = h.get(f"{BASE}/test?filter=all&category_id={cid}&print=true&num=true")
            protos = [x["sid"] for x in parse_probs(r.text)]
            json.dump(protos, open(f, "w"))
        meta.append({"sec": secnum, "cat": cid, "name": cname, "protos": protos})
        print(f"{secnum} / {cname}: прототипов {len(protos)}", flush=True)
        for pid in protos:
            pf = D / "protos" / f"{cid}_{pid}.jsonl"
            if pf.exists():
                continue
            r = h.get(f"{BASE}/test?likes={pid}&print=true&ans=true&num=true")
            probs = parse_probs(r.text)
            with open(pf, "w", encoding="utf8") as w:
                for x in probs:
                    x["cat"], x["proto"] = cid, pid
                    w.write(json.dumps(x, ensure_ascii=False) + "\n")
        json.dump(meta, open(D / ("cats.json" if only_main else "cats_all.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(only_main="--all" not in sys.argv)
