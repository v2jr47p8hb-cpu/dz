# Банк ОГЭ по математике: как пересобрать

Эти скрипты собирают данные для раздела `oge/` из открытого банка заданий ФИПИ.

Разметку (номер КИМ, подтип, прототип, ответ) берём со страниц «Решу ОГЭ», но с них сохраняются **только метаданные**. Условия берутся из ФИПИ. Решения «Решу ОГЭ» не копируются: на сайте у задачи стоит ссылка на разбор.

## Зависимости

- `pip install beautifulsoup4 lxml pillow requests`
- Node с Playwright — только для снимков условий: `NODE_PATH=$(npm root -g)`.

## Порядок

```bash
cd tools/oge
python3 fipi_fetch.py      # 39 страниц банка ФИПИ → cache/fipi/ (пауза 2,5 с)
python3 fipi_parse.py      # → cache/tasks_fipi.jsonl, cache/groups_fipi.jsonl
python3 fipi_images.py     # рисунки → oge/img/
python3 sdamgia_fetch.py   # каталог «Решу ОГЭ» № 1–25 → cache/sdam/ (≈ 800 запросов, пауза 2 с)
python3 sdamgia_fetch.py --all   # + архивные разделы Д1–Д38
python3 match.py           # сопоставление → cache/match.json
python3 verify.py          # проверка ответов через «Ответить» на сайте ФИПИ → cache/verify.json
python3 build.py           # → oge/data/*, out/import_oge_math.csv, out/report.md
node check_tex.js          # все формулы через KaTeX
python3 -m http.server 8765 --directory ../.. &   # для снимков
NODE_PATH=$(npm root -g) node snap.js    # снимки условий-таблиц и сюжетов → oge/snap/
```

- **TLS.** `oge.fipi.ru` не отдаёт промежуточный сертификат GlobalSign. `common.ca_bundle()` добавляет его к системному бандлу, проверку сертификатов не отключаем.
- **Ответы.** В публичные `oge/data/*.json` ответы не попадают. Они есть только в `out/import_oge_math.csv`: этот файл импортируется в кабинете («Пробники → Банк задач → Загрузить задачи») и в репозиторий не коммитится.
- **Кэш.** Кэш и выходные файлы лежат в `cache/` и `out/`, обе папки в `.gitignore`. Повторный запуск ничего заново не скачивает.
