#!/usr/bin/env python3
"""Распаковывает самораспаковывающийся HTML-артефакт «Теплее» в статический сайт
для GitHub Pages и применяет продакшн-доработки (см. qa/02_доработка.md)."""

import base64
import gzip
import json
import os
import re
import shutil
import sys

SRC = "/Users/DmitryRubin2/Downloads/Отчёт Теплее - для отправки.html"
OUT = "/Users/DmitryRubin2/Documents/Claude/Projects/0._Different_projects/teplee-report"
SITE_URL = "https://mrdmitrydouble.github.io/teplee-report/"

TITLE = "Теплее · Итоги созвона 05.08.2026 и проверка данными"
DESC = ("Кофейня «Теплее», Лыткарино. Что показали данные кассы yTimes за 10 месяцев — "
        "и что это меняет. Разбор по чекам, безубыточность, аренда, АУП.")

# подмножества шрифтов, ни один символ которых в тексте не встречается
DROP_SUBSETS = {"greek", "vietnamese"}

# критические шрифты первого экрана — их грузим сразу, без ожидания раскладки
PRELOAD = [
    "golos-text-400-cyrillic.woff2",
    "golos-text-400-latin.woff2",
    "playfair-display-500-cyrillic.woff2",
    "playfair-display-500-latin.woff2",
]

FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 200 200%22%3E"
    "%3Crect width=%22200%22 height=%22200%22 rx=%2244%22 fill=%22%23f4efe7%22/%3E"
    "%3Cg transform=%22translate(100 104)%22 fill=%22none%22 stroke=%22%238a5a2b%22 stroke-width=%227%22 "
    "stroke-linecap=%22round%22 stroke-linejoin=%22round%22%3E"
    "%3Cpath d=%22M-34 -16h56v26a22 22 0 0 1-22 22h-12a22 22 0 0 1-22-22z%22/%3E"
    "%3Cpath d=%22M22 -8h11a13 13 0 0 1 0 26H22%22/%3E"
    "%3Cpath d=%22M-16 -34c-5 7 5 10 0 17M2 -34c-5 7 5 10 0 17%22/%3E%3C/g%3E%3C/svg%3E"
)

# ── доработки: горизонтальные скроллеры, фокус, печать ───────────────────────
PROD_CSS = """
<style>
  /* Горизонтально прокручиваемые графики и таблицы.
     Тень у края показывает, что блок сдвигается; на самом краю она гаснет
     (перекрывается слоями с background-attachment: local).
     overscroll-behavior не даёт свайпу по графику увести со страницы. */
  .xscroll {
    overscroll-behavior-x: contain;
    background-image:
      linear-gradient(to right, #fffdf9 40%, rgba(255,253,249,0)),
      linear-gradient(to left,  #fffdf9 40%, rgba(255,253,249,0)),
      radial-gradient(farthest-side at 0 50%,   rgba(90,60,28,.20), rgba(90,60,28,0)),
      radial-gradient(farthest-side at 100% 50%, rgba(90,60,28,.20), rgba(90,60,28,0));
    background-position: 0 0, 100% 0, 0 0, 100% 0;
    background-repeat: no-repeat;
    background-size: 40px 100%, 40px 100%, 15px 100%, 15px 100%;
    background-attachment: local, local, scroll, scroll;
  }
  .xscroll:focus-visible {
    outline: 2px solid #8a5a2b;
    outline-offset: 3px;
    border-radius: 10px;
  }
  /* Подсказка в подписи к рисунку — показывается скриптом только там,
     где блок реально не помещается в экран. */
  .swipe-hint { display: none; color: #a8703a; white-space: nowrap; }

  a:focus-visible,
  button:focus-visible,
  [tabindex]:focus-visible {
    outline: 2px solid #8a5a2b;
    outline-offset: 3px;
    border-radius: 8px;
  }

  @media print {
    .xscroll { background-image: none !important; }
    .swipe-hint { display: none !important; }
  }
</style>
"""

PROD_JS = """
<script>
/* Доступность и подсказки для горизонтально прокручиваемых блоков.
   Эти блоки шире экрана на телефоне: без tabindex до правой половины графика
   не добраться с клавиатуры, а без подсказки читатель не понимает, что блок
   вообще двигается. Атрибуты ставятся снаружи React — он их не перезаписывает,
   потому что сам эти пропсы не задаёт. */
(function () {
  function label(sc) {
    var svg = sc.querySelector('svg[aria-label]');
    if (svg) return svg.getAttribute('aria-label') + ' — прокручивается вбок';
    var cap = caption(sc);
    if (cap) {
      var copy = cap.cloneNode(true);
      var h = copy.querySelector('.swipe-hint');
      if (h) h.remove();
      return copy.textContent.replace(/\\s+/g, ' ').trim() + ' — прокручивается вбок';
    }
    return 'Прокручиваемая область — сдвиньте вбок';
  }

  function caption(sc) {
    var node = sc;
    while (node && node.parentElement) {
      var prev = node.previousElementSibling;
      if (prev && prev.tagName === 'P' && prev.querySelector('.swipe-hint')) return prev;
      if (prev) return null;
      node = node.parentElement;
    }
    return null;
  }

  function sync() {
    var list = document.querySelectorAll('.xscroll');
    for (var i = 0; i < list.length; i++) {
      var sc = list[i];
      var overflows = sc.scrollWidth > sc.clientWidth + 1;
      if (overflows) {
        if (sc.getAttribute('tabindex') === null) {
          sc.setAttribute('tabindex', '0');
          sc.setAttribute('role', 'group');
          sc.setAttribute('aria-label', label(sc));
        }
      } else if (sc.getAttribute('tabindex') !== null) {
        sc.removeAttribute('tabindex');
        sc.removeAttribute('role');
        sc.removeAttribute('aria-label');
      }
      var cap = caption(sc);
      var hint = cap && cap.querySelector('.swipe-hint');
      if (hint) hint.style.display = overflows ? 'inline' : 'none';
    }
  }

  var timer = null;
  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(sync, 120);
  }

  function start() {
    sync();
    setTimeout(sync, 400);   // после того как графики смонтированы
    setTimeout(sync, 1500);  // после подгрузки шрифтов
    addEventListener('resize', schedule);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(sync);
  }

  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', start);
  else start();

  /* Оглавление: состояние для скринридера и закрытие по Escape.
     Клик по документу уже закрывает меню — им и пользуемся. */
  function tocButton() {
    var b = document.querySelectorAll('button');
    for (var i = 0; i < b.length; i++) if (/Оглавление/.test(b[i].textContent)) return b[i];
    return null;
  }

  function menuOpen() {
    return document.querySelectorAll('a[href^="#s"]').length > 8;
  }

  addEventListener('keydown', function (e) {
    if (e.key !== 'Escape' || !menuOpen()) return;
    document.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    var btn = tocButton();
    if (btn) btn.focus();
  });

  setInterval(function () {
    var btn = tocButton();
    if (!btn) return;
    var open = menuOpen() ? 'true' : 'false';
    if (btn.getAttribute('aria-expanded') !== open) btn.setAttribute('aria-expanded', open);
    if (!btn.hasAttribute('aria-haspopup')) btn.setAttribute('aria-haspopup', 'true');
  }, 400);
})();
</script>
"""

NOT_FOUND = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Страница не найдена · Теплее</title>
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#f4efe7">
<link rel="icon" href="__FAVICON__">
<style>
  @font-face {
    font-family: 'Golos Text'; font-style: normal; font-weight: 400; font-display: swap;
    src: url("/teplee-report/assets/fonts/golos-text-400-cyrillic.woff2") format('woff2');
    unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116;
  }
  @font-face {
    font-family: 'Playfair Display'; font-style: normal; font-weight: 500; font-display: swap;
    src: url("/teplee-report/assets/fonts/playfair-display-500-cyrillic.woff2") format('woff2');
    unicode-range: U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    background: #f4efe7; color: #231a13; padding: 24px;
    font: 17px/1.6 'Golos Text', system-ui, sans-serif; text-wrap: pretty;
  }
  main { max-width: 30rem; }
  h1 {
    font-family: 'Playfair Display', Georgia, serif; font-weight: 500;
    font-size: clamp(30px, 7vw, 44px); line-height: 1.1; margin: 18px 0 14px;
  }
  p { color: #5b4835; margin: 0 0 22px; }
  a {
    display: inline-block; color: #8a5a2b; text-decoration: none; font-weight: 600;
    border: 1px solid rgba(90,60,28,.22); border-radius: 999px; padding: 11px 20px;
    min-height: 44px;
  }
  a:hover { background: #eee1cc; }
  a:focus-visible { outline: 2px solid #8a5a2b; outline-offset: 3px; }
  .eyebrow {
    font-size: 12.5px; letter-spacing: .12em; text-transform: uppercase;
    color: #8f7a61; font-weight: 600;
  }
</style>
</head>
<body>
<main>
  <div class="eyebrow">Кофейня «Теплее» · Лыткарино</div>
  <h1>Такой страницы здесь нет</h1>
  <p>Возможно, в ссылке опечатка. Отчёт целиком — по кнопке ниже.</p>
  <a href="/teplee-report/">Открыть отчёт</a>
</main>
</body>
</html>
"""


def main():
    src = open(SRC, encoding="utf-8").read()

    def bundle_part(tag):
        m = re.search(r'<script type="__bundler/%s">(.*?)</script>' % tag, src, re.S)
        return m.group(1) if m else None

    manifest = json.loads(bundle_part("manifest"))
    template = json.loads(bundle_part("template"))
    ext = json.loads(bundle_part("ext_resources"))

    keep = {".git", ".github", ".gitignore", "README.md", "tools"}
    if os.path.isdir(OUT):
        for name in os.listdir(OUT):
            if name in keep:
                continue
            path = os.path.join(OUT, name)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    for d in ("assets/fonts", "assets/img", "assets/vendor"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)

    def payload(uuid):
        e = manifest[uuid]
        data = base64.b64decode(e["data"])
        return gzip.decompress(data) if e.get("compressed") else data

    # ── имена файлов шрифтов из @font-face ───────────────────────────────────
    slug = {"Golos Text": "golos-text", "JetBrains Mono": "jetbrains-mono",
            "Playfair Display": "playfair-display"}
    font_name, font_subset = {}, {}
    for subset, body in re.findall(r"/\* ([\w-]+) \*/\s*@font-face \{(.*?)\}", template, re.S):
        fam = re.search(r"font-family: '([^']+)'", body).group(1)
        weight = re.search(r"font-weight: (\d+)", body).group(1)
        style = re.search(r"font-style: (\w+)", body).group(1)
        uuid = re.search(r'url\("([^"]+)"\)', body).group(1)
        font_name.setdefault(uuid, "%s-%s%s-%s.woff2" % (
            slug[fam], weight, "-italic" if style == "italic" else "", subset))
        font_subset.setdefault(uuid, subset)

    # ── выгрузка ресурсов ───────────────────────────────────────────────────
    url_map, dropped_fonts = {}, []
    for uuid, entry in manifest.items():
        mime = entry["mime"]
        if mime == "font/woff2":
            if font_subset[uuid] in DROP_SUBSETS:
                dropped_fonts.append(font_name[uuid])
                continue
            name = font_name[uuid]
            open(os.path.join(OUT, "assets/fonts", name), "wb").write(payload(uuid))
            url_map[uuid] = "./assets/fonts/" + name
        elif mime == "image/png":
            open(os.path.join(OUT, "assets/img/paper-texture.png"), "wb").write(payload(uuid))
            url_map[uuid] = "./assets/img/paper-texture.png"
        elif mime == "text/javascript":
            ids = [x["id"] for x in ext if x["uuid"] == uuid]
            if ids:
                name = ids[0].rsplit("/", 1)[-1]
                open(os.path.join(OUT, "assets/vendor", name), "wb").write(payload(uuid))
                url_map[uuid] = "./assets/vendor/" + name
            else:
                open(os.path.join(OUT, "assets/dc-runtime.js"), "wb").write(payload(uuid))
                url_map[uuid] = "./assets/dc-runtime.js"

    html = template

    # ── выкинуть @font-face неиспользуемых подмножеств ──────────────────────
    for uuid in list(font_subset):
        if font_subset[uuid] in DROP_SUBSETS:
            html = re.sub(r"/\* [\w-]+ \*/\s*@font-face \{[^}]*?%s[^}]*?\}\s*" % re.escape(uuid),
                          "", html, flags=re.S)

    for uuid, path in url_map.items():
        html = html.replace(uuid, path)

    left = set(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", html))
    if left:
        sys.exit("!! в разметке остались неразрешённые UUID: %s" % left)

    html = re.sub(r'\s+integrity="[^"]*"', "", html)

    # ── горизонтальные скроллеры: класс + подсказка в подписи ───────────────
    html, n_inline = re.subn(r'<div style="overflowX:auto;', '<div class="xscroll" style="overflowX:auto;', html)
    html, n_js = re.subn(r"h\('div',\{style:\{overflowX:'auto',WebkitOverflowScrolling:'touch'\}\}",
                         "h('div',{className:'xscroll',style:{overflowX:'auto',WebkitOverflowScrolling:'touch'}}", html)
    if n_inline + n_js != 9:
        sys.exit("!! ожидалось 9 прокручиваемых блоков, размечено %d" % (n_inline + n_js))

    hint = '<span class="swipe-hint"> · листайте вбок →</span>'
    caption_re = re.compile(r"(<p style=\"fontFamily:'JetBrains Mono'[^\"]*\">(?:(?!</p>).)*?)(</p>)", re.S)
    captions = ["Рис. 1 ", "Рис. 3 ", "Рис. 5 ", "Таблица 1 ", "Рис. 6 ",
                "Рис. 7 ", "Таблица 2 ", "Рис. 8 ", "Рис. 9 "]

    def add_hint(m):
        return m.group(1) + hint + m.group(2) if any(c in m.group(1) for c in captions) else m.group(0)

    html, n_hint = caption_re.subn(add_hint, html)
    if html.count('class="swipe-hint"') != 9:
        sys.exit("!! подсказок размечено %d, ожидалось 9" % html.count('class="swipe-hint"'))

    # ── дубль viewport из <helmet> (в <head> он уже есть) ───────────────────
    head_end = html.index("</head>")
    body = html[head_end:]
    body, n_vp = re.subn(r'<meta name="viewport" content="width=device-width, initial-scale=1">\s*', "", body, count=1)
    html = html[:head_end] + body

    # ── мёртвые preconnect на Google Fonts: шрифты локальные ────────────────
    html, n_pc = re.subn(r'\s*<link rel="preconnect" href="https://fonts\.(googleapis|gstatic)\.com"[^>]*>', "", html)

    # ── голова ──────────────────────────────────────────────────────────────
    resources = {x["id"]: url_map[x["uuid"]] for x in ext}
    head = ["<script>window.__resources=%s;</script>"
            % json.dumps(resources, ensure_ascii=False).replace("</", "<\\/")]
    head += ['<link rel="preload" href="./assets/fonts/%s" as="font" type="font/woff2" crossorigin>' % f
             for f in PRELOAD]
    head += [
        '<meta name="robots" content="noindex, nofollow">',
        '<meta name="description" content="%s">' % DESC,
        '<meta name="theme-color" content="#f4efe7">',
        '<link rel="icon" href="%s">' % FAVICON,
        '<link rel="canonical" href="%s">' % SITE_URL,
        '<meta property="og:type" content="article">',
        '<meta property="og:locale" content="ru_RU">',
        '<meta property="og:site_name" content="Кофейня «Теплее»">',
        '<meta property="og:url" content="%s">' % SITE_URL,
        '<meta property="og:title" content="%s">' % TITLE,
        '<meta property="og:description" content="%s">' % DESC,
        '<meta property="og:image" content="%sassets/img/og-cover.jpg">' % SITE_URL,
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:type" content="image/jpeg">',
        '<meta property="og:image:alt" content="Теплее · итоги созвона 05.08.2026">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:title" content="%s">' % TITLE,
        '<meta name="twitter:description" content="%s">' % DESC,
        '<meta name="twitter:image" content="%sassets/img/og-cover.jpg">' % SITE_URL,
    ]

    html = html.replace("<html>", '<html lang="ru">', 1)
    i = html.index("<head>") + len("<head>")
    html = html[:i] + "\n" + "\n".join(head) + "\n" + PROD_CSS + html[i:]
    html = html.replace("</body>", PROD_JS + "</body>", 1)

    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)
    open(os.path.join(OUT, "404.html"), "w", encoding="utf-8").write(
        NOT_FOUND.replace("__FAVICON__", FAVICON))
    open(os.path.join(OUT, ".nojekyll"), "w").write("")

    print("собрано →", OUT)
    print("  скроллеров размечено: %d (инлайн %d + React %d)" % (n_inline + n_js, n_inline, n_js))
    print("  подсказок в подписях: %d" % html.count('class="swipe-hint"'))
    print("  снято preconnect: %d, дублей viewport: %d" % (n_pc, n_vp))
    print("  не выгружены неиспользуемые подмножества: %s" % ", ".join(sorted(dropped_fonts)))


if __name__ == "__main__":
    main()
