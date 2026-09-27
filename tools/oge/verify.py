"""Проверка ответов через «Ответить» открытого банка ФИПИ (solve.php: 3 — верно, 2 — неверно).

Для каждой задачи с кратким ответом берём ответ сопоставленной задачи «Решу ОГЭ» (и запасных кандидатов),
пробуем варианты записи и сохраняем подтверждённый ответ в cache/verify.json.
"""
import re, json, sys
from fractions import Fraction
from common import Http, ca_bundle, CACHE, FIPI, FIPI_PROJ


def variants(ans, t):
    a = (ans or "").replace("−", "-").replace("–", "-").replace(" ", " ").strip().rstrip(".")
    a = re.sub(r"^Ответ:\s*", "", a)
    parts = re.split(r"\s*(?:\||;|\bили\b)\s*", a) if t["kind"] in ("short",) else [a]
    out = []
    for p in parts + [a]:
        p = p.strip()
        if not p:
            continue
        if t["kind"] == "multi":
            digs = [int(d) for d in re.findall(r"\d", p)]
            n = len(t["options"])
            if digs and all(1 <= d <= n for d in digs):
                out.append("".join("1" if i + 1 in digs else "0" for i in range(n)))
            continue
        if t["kind"] in ("match", "choice"):
            out.append(re.sub(r"\D", "", p))
            continue
        q = p.replace(" ", "")
        out.append(q.replace(".", ","))
        m = re.fullmatch(r"(-?\d+)/(\d+)", q)
        if m:
            fr = Fraction(int(m.group(1)), int(m.group(2)))
            d = fr.denominator
            while d % 2 == 0:
                d //= 2
            while d % 5 == 0:
                d //= 5
            if d == 1:
                out.append(str(float(fr)).rstrip("0").rstrip(".").replace(".", ","))
        if re.fullmatch(r"\d+(?:\s*\d+)+", p) and t["kind"] == "short":
            out.append(re.sub(r"\s", "", p))
    seen, res = set(), []
    for x in out:
        if x and x not in seen:
            seen.add(x)
            res.append(x)
    return res


def main():
    fipi = [json.loads(l) for l in open(CACHE / "tasks_fipi.jsonl", encoding="utf8")]
    match = json.load(open(CACHE / "match.json", encoding="utf8"))
    vf = CACHE / "verify.json"
    done = json.load(open(vf, encoding="utf8")) if vf.exists() else {}
    h = Http(delay=0.8, verify=ca_bundle())
    h.get(f"{FIPI}index.php?proj={FIPI_PROJ}")
    n = 0
    for t in fipi:
        if t["kind"] == "long":
            continue
        m = match.get(t["fid"])
        if not m or m.get("weak"):
            continue
        cands = [m] + m.get("alts", [])
        key = "|".join(f'{c["sid"]}:{c["ans"]}' for c in cands)
        if t["fid"] in done and done[t["fid"]].get("key") == key:
            continue
        rec = {"key": key, "ok": False, "tried": []}
        for c in cands:
            for v in variants(c["ans"], t):
                if v in rec["tried"]:
                    continue
                r = h.post(f"{FIPI}solve.php", data={"guid": t["guid"], "answer": v, "ajax": "1", "proj": FIPI_PROJ})
                rec["tried"].append(v)
                if r.text.strip() == "3":
                    rec.update(ok=True, ans=v, sid=c["sid"])
                    break
            if rec["ok"] or len(rec["tried"]) >= (10 if t.get("group") else 6):
                break
        done[t["fid"]] = rec
        n += 1
        if n % 50 == 0:
            json.dump(done, open(vf, "w", encoding="utf8"), ensure_ascii=False)
            ok = sum(1 for x in done.values() if x["ok"])
            print(f"проверено {len(done)}, подтверждено {ok}", flush=True)
    json.dump(done, open(vf, "w", encoding="utf8"), ensure_ascii=False)
    ok = sum(1 for x in done.values() if x["ok"])
    print(f"итого проверено {len(done)}, подтверждено {ok}")


if __name__ == "__main__":
    main()
