# =============================================================================
# Module: docs.make_ui_mockup
# Responsibilities: Generates the UI design mockup PNG with Pillow.
# Dependencies: PIL
# Dependents: docs/ui-design.png
# ADRs: ADR-0010
# Traceability: docs/decisions/README.md
# =============================================================================
"""Render a UI design mockup (PNG) for the HTML interface.

Run with a Python interpreter that has Pillow installed (the DSH bundled
Python does); writes docs/ui-design.png.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "ui-design.png"

W, H = 1280, 900
BG = "#1b2f48"
PANEL = "#213a58"
PANEL2 = "#294666"
BORDER = "#3a5170"
TEXT = "#f4f7fb"
SOFT = "#cbd6e4"
MUTED = "#93a6bc"
ACCENT = "#dce8f7"
LEAD = "#1f3550"

FONT_DIR = Path("C:/Windows/Fonts")
FONT_REG = FONT_DIR / "msyh.ttc"
FONT_BOLD = FONT_DIR / "msyhbd.ttc"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a Windows CJK font at the given size.

    Preconditions:
        size > 0 and a CJK font file exists under C:/Windows/Fonts.
    Postconditions:
        PIL FreeTypeFont; bold=True prefers msyhbd.ttc when available.
    Prohibitions:
        Do not call before Pillow is importable.
    Raises:
        OSError when no font can be loaded.
    """
    path = FONT_BOLD if bold and FONT_BOLD.exists() else FONT_REG
    return ImageFont.truetype(str(path), size)


def rr(draw: ImageDraw.ImageDraw, box, radius=10, fill=PANEL, outline=BORDER, width=1):
    """Draw a rounded rectangle with the mockup palette.

    Preconditions:
        A Pillow ImageDraw and valid bounding box.
    Postconditions:
        Nothing (mutates the image canvas).
    Prohibitions:
        Do not use on images smaller than the box.
    Raises:
        None.
    """
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(draw: ImageDraw.ImageDraw, xy, content: str, size=13, color=TEXT, bold=False):
    """Draw one line of UI text at absolute coordinates.

    Preconditions:
        ImageDraw instance and an existing font size.
    Postconditions:
        Nothing (mutates the canvas).
    Prohibitions:
        Do not pass multi-line strings; use wrap() first.
    Raises:
        None.
    """
    draw.text(xy, content, font=font(size, bold), fill=color)



def wrap(draw, content: str, fnt, max_width: float, max_lines: int = 2):
    """Greedily wrap text to a pixel width.

    Preconditions:
        A draw context, string, font and positive max_width.
    Postconditions:
        List of at most max_lines strings.
    Prohibitions:
        Do not rely on word boundaries for CJK text.
    Raises:
        None.
    """
    lines, current = [], ""
    for char in content:
        if draw.textlength(current + char, font=fnt) > max_width:
            lines.append(current)
            current = char
            if len(lines) >= max_lines:
                return lines
        else:
            current += char
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# ---------------- top bar ----------------
draw.rectangle((0, 0, W, 66), fill=PANEL)
draw.rectangle((0, 65, W, 66), fill=BORDER)
rr(draw, (22, 16, 58, 52), radius=10, fill=PANEL2, outline=ACCENT)
text(draw, (33, 23), "AI", size=18, color=ACCENT, bold=True)
text(draw, (72, 16), "AI 新闻日报", size=18, bold=True)
text(draw, (72, 42), "2026-11-08 · 近 7 天窗口 · 正常", size=11, color=MUTED)

rr(draw, (940, 16, 1046, 50), radius=8, fill=ACCENT, outline=ACCENT)
text(draw, (963, 26), "生成日报", size=13, color="#14263d")
rr(draw, (1058, 16, 1164, 50), radius=8, fill=PANEL2)
text(draw, (1080, 26), "趋势分析", size=13, color=TEXT)
rr(draw, (1176, 16, 1212, 50), radius=8, fill=PANEL2)
text(draw, (1189, 25), "◐", size=14, color=TEXT)

# ---------------- sidebar ----------------
draw.rectangle((0, 66, 250, H), fill=BG)
text(draw, (22, 92), "历史报告", size=12, color=MUTED)
history = [("2026-11-08", "22 条"), ("2026-11-07", "18 条"), ("2026-11-06", "20 条"), ("2026-11-05", "16 条")]
y = 118
for index, (date, count) in enumerate(history):
    box = (16, y, 234, y + 38)
    rr(draw, box, radius=8, fill=PANEL2 if index == 0 else PANEL, outline=BORDER)
    text(draw, (28, y + 11), date, size=12, color=TEXT, bold=index == 0)
    text(draw, (188, y + 12), count, size=11, color=MUTED)
    y += 46

rr(draw, (16, 310, 234, 352), radius=8, fill=PANEL, outline=BORDER)
draw.ellipse((30, 324, 40, 334), fill="#34d399")
text(draw, (50, 321), "上次完成：11-08 20:32", size=10, color=MUTED)

# ---------------- stats ----------------
stats = [("12", "科技与产品"), ("6", "财务与资本"), ("4", "政策与监管"), ("7 天", "统计窗口"), ("deepseek-flash", "整理模型")]
x = 274
for num, label in stats:
    width = 150 if label != "整理模型" else 178
    rr(draw, (x, 88, x + width, 150), radius=10, fill=PANEL)
    text(draw, (x + 16, 100), num, size=20, color=TEXT, bold=True)
    text(draw, (x + 16, 130), label, size=11, color=MUTED)
    x += width + 10

# ---------------- leads ----------------
text(draw, (274, 172), "头条", size=12, color=MUTED)
leads = [
    ("1", "OpenAI 新融资到账 110 亿美元，不及原计划一半", "2026-11-07"),
    ("2", "月之暗面发布 Kimi-K3.1-Pro 模型", "2026-11-02"),
    ("3", "DeepSeek 开源推理框架并披露账本", "2026-11-08"),
]
x = 274
for rank, title, meta in leads:
    rr(draw, (x, 196, x + 312, 300), radius=10, fill=PANEL, outline=BORDER)
    draw.rectangle((x, 196, x + 3, 300), fill=ACCENT)
    text(draw, (x + 14, 206), rank, size=13, color=ACCENT, bold=True)
    title_font = font(12, bold=True)
    for line_index, line_text in enumerate(wrap(draw, title, title_font, 268, max_lines=2)):
        text(draw, (x + 34, 204 + line_index * 21), line_text, size=12,
             color=TEXT, bold=(line_index == 0))
    text(draw, (x + 14, 258), "摘要：AI 行业重要动态，详见正文。", size=10, color=SOFT)
    text(draw, (x + 14, 278), meta, size=9, color=MUTED)
    x += 322

# ---------------- sections ----------------
sections = [
    ("一、科技与产品", "12 条", [("月之暗面", "Kimi-K3.1-Pro 发布 / Kimi Code CLI"), ("DeepSeek", "开源推理框架并披露账本"), ("阿里", "Qwen-MM-Plugins / qwen-code")]),
    ("二、AI 公司财务与资本", "6 条", [("OpenAI", "新融资到账 110 亿美元"), ("NVIDIA", "AI 融资交易带动金融股"), ("其他", "华为系具身智能融资 86 亿")]),
    ("三、政府与监管 AI 政策", "4 条", [("美国政府", "AI 安全中心独立性担忧"), ("中国政府", "经观社论：AI 对就业影响")]),
]
y = 322
for title, count, rows in sections:
    height = 34 + len(rows) * 34 + 8
    rr(draw, (274, y, 1256, y + height), radius=12, fill=PANEL, outline=BORDER)
    text(draw, (290, y + 10), title, size=13, color=TEXT, bold=True)
    text(draw, (1188, y + 11), count, size=10, color=MUTED)
    draw.line((290, y + 30, 1240, y + 30), fill=BORDER)
    row_y = y + 34
    for company, headline in rows:
        text(draw, (290, row_y + 6), company, size=10, color=SOFT, bold=True)
        text(draw, (390, row_y + 6), headline, size=11, color=TEXT)
        draw.line((290, row_y + 26, 1240, row_y + 26), fill="#20252e")
        row_y += 34
    y += height + 12

# ---------------- footer ----------------
text(draw, (274, H - 34), "数据：45+ 官方渠道 · 公开接口 ｜ 标题/摘要由 DeepSeek 整理 ｜ 仅供个人研究，不构成投资建议", size=10, color=MUTED)
text(draw, (W - 250, H - 34), "主题：深色 / 浅色（可切换）", size=10, color=MUTED)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(f"saved {OUT} ({img.size[0]}x{img.size[1]})")

