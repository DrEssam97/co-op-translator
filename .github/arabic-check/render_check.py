"""Run co-op-translator's real ImageTranslator.render_translated_image on Arabic text.

Usage: python render_check.py OUT_DIR

No Azure keys are needed: text detection and translation are skipped and the boxes and
translations are given directly. Each mode is drawn twice: with Pillow as installed
(Raqm if this Pillow has it) and with Pillow forced to its basic layout, which is what
Pillow does when Raqm is missing.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features

sys.stdout.reconfigure(encoding="utf-8")
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

from co_op_translator.config.font_config import FontConfig  # noqa: E402
from co_op_translator.core.vision.image_translator import ImageTranslator  # noqa: E402

print("raqm:", features.check_feature("raqm"), "fribidi:", features.version_feature("fribidi"))


class OfflineTranslator(ImageTranslator):
    def get_image_analysis_client(self):
        raise NotImplementedError

    def extract_line_bounding_boxes(self, image_path):
        raise NotImplementedError


def make_source(path: Path) -> list[dict]:
    """An English slide with two text lines, and the boxes OCR would return."""
    img = Image.new("RGB", (900, 260), (240, 240, 240))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FONTS / "NotoSans-Medium.ttf"), 44, layout_engine=ImageFont.Layout.BASIC)
    boxes = []
    for i, text in enumerate(["Hello world", "Translate text in images"]):
        x, y = 60, 50 + i * 100
        l, t, r, b = draw.textbbox((x, y), text, font=font)
        draw.text((x, y), text, font=font, fill=(20, 20, 20))
        boxes.append({"bounding_box": [l, t, r, t, r, b, l, b], "text": text})
    img.save(path)
    return boxes


FONTS = Path(FontConfig().get_font_path("en")).parent
source = out / "source.png"
boxes = make_source(source)
translations = ["مرحبا بالعالم", "ترجمة النصوص في الصور"]

translator = OfflineTranslator.__new__(OfflineTranslator)
translator.font_config = FontConfig()

real_truetype = ImageFont.truetype
rows = []
for layout in ("as installed", "basic"):
    if layout == "basic":
        ImageFont.truetype = lambda *a, **k: real_truetype(*a, **{**k, "layout_engine": ImageFont.Layout.BASIC})
    for fast in (True, False):
        img = translator.render_translated_image(str(source), boxes, translations, "ar", fast_mode=fast)
        name = f"{'fast' if fast else 'neat'}-{layout.replace(' ', '-')}.png"
        img.convert("RGB").save(out / name)
        rows.append((f"{'fast' if fast else 'neat'} mode, Pillow layout {layout}", img.convert("RGB")))
    ImageFont.truetype = real_truetype

label_font = real_truetype(str(FONTS / "NotoSans-Medium.ttf"), 26, layout_engine=ImageFont.Layout.BASIC)
sheet = Image.new("RGB", (900, sum(r.height + 44 for _, r in rows)), "white")
y = 0
for label, img in rows:
    ImageDraw.Draw(sheet).text((12, y + 6), label, font=label_font, fill="black")
    sheet.paste(img, (0, y + 44))
    y += img.height + 44
sheet.save(out / "sheet.png")
print("saved", out / "sheet.png")
