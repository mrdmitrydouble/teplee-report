#!/usr/bin/env python3
"""Рисует картинки сайта: превью ссылки для мессенджеров (1200×630),
favicon.svg, favicon.ico и apple-touch-icon.png.
Запускать ПОСЛЕ build.py — берёт шрифты и текстуру из собранного сайта."""

import os
import subprocess
import sys
import tempfile

OUT = os.environ.get("TEPLEE_SITE",
                     os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROME = os.environ.get("CHROME",
                        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
TMP = tempfile.mkdtemp(prefix="teplee-og-")

CARD = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @font-face { font-family:'Golos Text'; font-weight:400;
    src:url("FONTS/golos-text-400-cyrillic.woff2") format('woff2'); }
  @font-face { font-family:'Golos Text'; font-weight:600;
    src:url("FONTS/golos-text-400-cyrillic.woff2") format('woff2'); }
  @font-face { font-family:'Playfair'; font-weight:500; font-style:normal;
    src:url("FONTS/playfair-display-500-cyrillic.woff2") format('woff2'); }
  @font-face { font-family:'Playfair'; font-weight:500; font-style:italic;
    src:url("FONTS/playfair-display-500-italic-cyrillic.woff2") format('woff2'); }
  @font-face { font-family:'PlayfairLat'; font-weight:500;
    src:url("FONTS/playfair-display-500-latin.woff2") format('woff2'); }
  * { margin:0; padding:0; box-sizing:border-box; }
  html,body { width:1200px; height:630px; }
  body {
    background:#f4efe7 url("IMG/paper-texture.png");
    font-family:'Golos Text',sans-serif; color:#231a13;
    padding:72px 80px; position:relative; overflow:hidden;
    display:flex; flex-direction:column; justify-content:space-between;
  }
  .rings { position:absolute; top:-120px; right:-110px; width:520px; height:520px; opacity:.5; }
  .eyebrow {
    display:flex; align-items:center; gap:14px;
    font-size:19px; letter-spacing:.14em; text-transform:uppercase;
    color:#8f7a61; font-weight:600; position:relative;
  }
  h1 {
    font-family:'Playfair','PlayfairLat',Georgia,serif; font-weight:500;
    font-size:70px; line-height:1.08; letter-spacing:-.015em;
    max-width:19ch; margin:0; position:relative;
  }
  h1 i { font-style:italic; color:#8a5a2b; }
  .foot {
    display:flex; align-items:center; gap:18px; position:relative;
    font-size:23px; color:#5b4835;
  }
  .rule { flex:1; height:1px; background:rgba(90,60,28,.22); }
  .badge {
    font-size:19px; font-weight:600; color:#8a5a2b;
    border:1px solid rgba(90,60,28,.22); border-radius:999px; padding:9px 20px;
    background:#fffdf9; white-space:nowrap;
  }
</style></head>
<body>
  <svg class="rings" viewBox="0 0 200 200">
    <circle cx="100" cy="100" r="86" fill="none" stroke="#8a5a2b" stroke-opacity=".10" stroke-width="1.5"/>
    <circle cx="100" cy="100" r="66" fill="none" stroke="#8a5a2b" stroke-opacity=".16" stroke-width="1"/>
    <circle cx="100" cy="100" r="46" fill="#8a5a2b" fill-opacity=".05"/>
  </svg>

  <div class="eyebrow">
    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#a8703a"
         stroke-width="1.6" stroke-linecap="round">
      <path d="M4 10h12v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4v-6z"/>
      <path d="M16 11h2.2a2.3 2.3 0 0 1 0 4.6H16"/>
      <path d="M8 4c-1 1.5 1 2.2 0 3.7M12 4c-1 1.5 1 2.2 0 3.7"/>
    </svg>
    Кофейня «Теплее» · Лыткарино
  </div>

  <h1>Что показали данные кассы&nbsp;— и <i>что это меняет</i></h1>

  <div class="foot">
    <span>Итоги созвона 05.08.2026</span>
    <span class="rule"></span>
    <span class="badge">проверено по чекам yTimes</span>
  </div>
</body></html>
"""


# Кофейная чашка — тот же знак, что в шапке отчёта.
ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <rect width="200" height="200" rx="44" fill="#f4efe7"/>
  <g transform="translate(100 104)" fill="none" stroke="#8a5a2b" stroke-width="7"
     stroke-linecap="round" stroke-linejoin="round">
    <path d="M-34 -16h56v26a22 22 0 0 1-22 22h-12a22 22 0 0 1-22-22z"/>
    <path d="M22 -8h11a13 13 0 0 1 0 26H22"/>
    <path d="M-16 -34c-5 7 5 10 0 17M2 -34c-5 7 5 10 0 17"/>
  </g>
</svg>
"""


def shot(html_path, width, height, png_path):
    subprocess.run([
        CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1", "--allow-file-access-from-files",
        "--window-size=%d,%d" % (width, height),
        "--screenshot=" + png_path, "file://" + html_path,
    ], check=True, capture_output=True)


def main():
    if not os.path.isdir(os.path.join(OUT, "assets/fonts")):
        sys.exit("!! сначала запусти build.py")
    from PIL import Image

    # ── превью ссылки ───────────────────────────────────────────────────────
    card = os.path.join(TMP, "og-card.html")
    with open(card, "w", encoding="utf-8") as f:
        f.write(CARD.replace("FONTS", "file://" + OUT + "/assets/fonts")
                    .replace("IMG", "file://" + OUT + "/assets/img"))
    raw = os.path.join(TMP, "og-raw.png")
    shot(card, 1200, 630, raw)
    # мессенджеры показывают превью как растр — JPEG втрое легче PNG с текстурой
    jpg = os.path.join(OUT, "assets/img/og-cover.jpg")
    Image.open(raw).convert("RGB").save(jpg, "JPEG", quality=88, optimize=True, progressive=True)
    print("og-cover.jpg:", os.path.getsize(jpg), "байт")

    # ── иконки ──────────────────────────────────────────────────────────────
    # SVG понимают современные браузеры, .ico — Safari и старые, PNG нужен iOS
    # для ярлыка «на экран Домой».
    svg_out = os.path.join(OUT, "assets/img/favicon.svg")
    open(svg_out, "w", encoding="utf-8").write(ICON_SVG)

    def render(size, radius):
        html = os.path.join(TMP, "icon-%d.html" % size)
        open(html, "w", encoding="utf-8").write(
            "<html><head><style>html,body{margin:0;padding:0}"
            "svg{display:block;width:%dpx;height:%dpx}</style></head>"
            "<body>" % (size, size) + ICON_SVG.replace('rx="44"', 'rx="%d"' % radius)
            + "</body></html>")
        png = os.path.join(TMP, "icon-%d.png" % size)
        shot(html, size, size, png)
        return Image.open(png).convert("RGB")

    # iOS накладывает на ярлык собственную маску-скругление, поэтому квадрат
    # рисуем во весь кадр — иначе по углам полезут светлые серпы.
    apple = os.path.join(OUT, "assets/img/apple-touch-icon.png")
    render(180, 0).save(apple, "PNG", optimize=True)

    # Для .ico рендерим 64 px и уменьшаем — со 180 обводка чашки на 16 px «плывёт».
    ico = os.path.join(OUT, "assets/img/favicon.ico")
    render(64, 14).save(ico, "ICO", sizes=[(16, 16), (32, 32), (48, 48)])

    print("favicon.svg / favicon.ico / apple-touch-icon.png:",
          os.path.getsize(svg_out), "/", os.path.getsize(ico), "/",
          os.path.getsize(apple), "байт")


if __name__ == "__main__":
    main()
