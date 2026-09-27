"""Выгрузка открытого банка ФИПИ ОГЭ-математика в cache/fipi/page_NNN.html (utf-8)."""
import re, sys
from common import Http, ca_bundle, CACHE, FIPI, FIPI_PROJ

PAGESIZE = 100


def main():
    out = CACHE / "fipi"
    out.mkdir(exist_ok=True)
    h = Http(delay=2.5, verify=ca_bundle())
    h.get(f"{FIPI}index.php?proj={FIPI_PROJ}")  # PHPSESSID
    first = h.get(f"{FIPI}questions.php?proj={FIPI_PROJ}&init_filter_themes=1")
    total = int(re.search(r"setQCount\((\d+)\)", first.content.decode("cp1251")).group(1))
    pages = (total + PAGESIZE - 1) // PAGESIZE
    print(f"заданий: {total}, страниц: {pages}")
    for p in range(pages):
        f = out / f"page_{p:03d}.html"
        if f.exists() and f.stat().st_size > 1000:
            continue
        r = h.get(f"{FIPI}questions.php?proj={FIPI_PROJ}&page={p}&pagesize={PAGESIZE}")
        html = r.content.decode("cp1251", errors="replace")
        n = html.count("class=\"qblock\"")
        f.write_text(html, encoding="utf-8")
        print(f"стр. {p}: блоков {n}", flush=True)
    (out / "total.txt").write_text(str(total))


if __name__ == "__main__":
    sys.exit(main())
