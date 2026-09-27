"""Скачивает рисунки заданий ФИПИ в oge/img/ (имена — из tasks_fipi.jsonl / groups_fipi.jsonl)."""
import json
from common import Http, ca_bundle, CACHE, SITE


def main():
    dst = SITE / "img"
    dst.mkdir(parents=True, exist_ok=True)
    items = []
    for fn in ("tasks_fipi.jsonl", "groups_fipi.jsonl"):
        for line in open(CACHE / fn, encoding="utf8"):
            items += json.loads(line)["imgs"]
    h = Http(delay=0.7, verify=ca_bundle())
    bad = []
    for i, im in enumerate(items):
        f = dst / im["local"]
        if f.exists() and f.stat().st_size > 0:
            continue
        r = h.get(im["src"])
        if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image"):
            bad.append((im["local"], r.status_code))
            continue
        f.write_bytes(r.content)
        if i % 100 == 0:
            print(i, "/", len(items), flush=True)
    print("готово, ошибок:", len(bad), bad[:20])


if __name__ == "__main__":
    main()
