from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

VENDOR_DIR = Path(__file__).resolve().parent / ".vendor"
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))

import qrcode
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "families.json"
TEMPLATE_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
MEDIA_DIR = ROOT / "media"
OUTPUT_DIR = ROOT / "docs"

SITE_NAME = "岁月留痕"
PUBLIC_BASE_URL = "https://godjinfinity-cpu.github.io/suiyue-memory"
BASE_URL = os.getenv("BASE_URL", PUBLIC_BASE_URL).rstrip("/")

VISIBILITY_LABELS = {
    "private": "仅家庭查看",
    "community": "社区内部展示",
    "public": "可公开展示",
}

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# A4 landscape divided into four equal cards is A6 landscape at 300 DPI.
CARD_DPI = 300
CARD_WIDTH = 1754
CARD_HEIGHT = 1240
A4_WIDTH = CARD_WIDTH * 2
A4_HEIGHT = CARD_HEIGHT * 2
EXPORT_CARD_DIR = "downloads/cards"
EXPORT_SHEET_DIR = "downloads/a4-sheets"

FONT_REGULAR_CANDIDATES = (
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
)
FONT_BOLD_CANDIDATES = (
    Path("C:/Windows/Fonts/msyhbd.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
)


def load_records() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"没有找到家庭数据文件：{DATA_FILE}")

    with DATA_FILE.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("families.json 的最外层必须是数组。")

    return records


def ensure_inside_workspace(path: Path) -> None:
    resolved_root = ROOT.resolve()
    resolved_path = path.resolve()

    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise RuntimeError(f"目标路径不在项目目录内：{resolved_path}") from exc


def reset_output_directory() -> None:
    ensure_inside_workspace(OUTPUT_DIR)

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # GitHub Pages serves this generated folder as plain static files.
    (OUTPUT_DIR / ".nojekyll").touch()


def copy_public_assets() -> None:
    if not STATIC_DIR.exists():
        raise FileNotFoundError(f"没有找到样式目录：{STATIC_DIR}")
    if not MEDIA_DIR.exists():
        raise FileNotFoundError(f"没有找到媒体目录：{MEDIA_DIR}")

    shutil.copytree(STATIC_DIR, OUTPUT_DIR / "static", dirs_exist_ok=True)
    shutil.copytree(MEDIA_DIR, OUTPUT_DIR / "media", dirs_exist_ok=True)


def assert_media_exists(record_id: str, field: str, value: str | None) -> None:
    if not value:
        return

    media_path = ROOT / value
    if not media_path.exists():
        raise FileNotFoundError(f"记录 {record_id} 的 {field} 文件不存在：{media_path}")


def validate_records(records: list[dict[str, Any]]) -> None:
    required_fields = [
        "id",
        "slug",
        "title",
        "object_name",
        "year",
        "narrator",
        "co_creator",
        "story",
        "quote",
        "photo",
        "visibility",
        "event_date",
    ]

    ids: set[str] = set()
    slugs: set[str] = set()

    for index, record in enumerate(records, start=1):
        record_id = str(record.get("id") or f"第 {index} 条")

        missing = [field for field in required_fields if not record.get(field)]
        if missing:
            raise ValueError(f"记录 {record_id} 缺少字段：{', '.join(missing)}")

        if record["id"] in ids:
            raise ValueError(f"家庭 ID 重复：{record['id']}")
        ids.add(record["id"])

        if record["slug"] in slugs:
            raise ValueError(f"页面 slug 重复：{record['slug']}")
        slugs.add(record["slug"])

        if not SLUG_PATTERN.match(record["slug"]):
            raise ValueError(f"记录 {record_id} 的 slug 只能使用小写字母、数字和短横线。")

        if record["visibility"] not in VISIBILITY_LABELS:
            allowed = ", ".join(VISIBILITY_LABELS)
            raise ValueError(f"记录 {record_id} 的 visibility 必须是：{allowed}")

        story_length = len(str(record["story"]).strip())
        if story_length < 80 or story_length > 320:
            raise ValueError(f"记录 {record_id} 的故事正文建议控制在 80-320 字，目前为 {story_length} 字。")

        assert_media_exists(record_id, "photo", record.get("photo"))
        assert_media_exists(record_id, "audio", record.get("audio"))
        assert_media_exists(record_id, "video", record.get("video"))
        assert_media_exists(record_id, "video_poster", record.get("video_poster"))


def make_url(relative_path: str | None) -> str:
    if not relative_path:
        return ""

    normalized = relative_path.replace("\\", "/").lstrip("/")
    return f"{BASE_URL}/{normalized}"


def summarize(text: str, max_length: int = 58) -> str:
    clean = " ".join(text.split())
    if len(clean) <= max_length:
        return clean

    return f"{clean[:max_length]}..."


def prepare_record(record: dict[str, Any]) -> dict[str, Any]:
    page_url = f"{BASE_URL}/f/{record['slug']}/"
    card_url = f"{BASE_URL}/cards/{record['id'].lower()}.html"
    qr_relative_path = f"qrcodes/{record['id']}.png"
    download_png_path = f"{EXPORT_CARD_DIR}/{record['id']}-card.png"
    download_pdf_path = f"{EXPORT_CARD_DIR}/{record['id']}-card.pdf"

    prepared = {
        **record,
        "page_url": page_url,
        "card_url": card_url,
        "qr_path": qr_relative_path,
        "qr_url": make_url(qr_relative_path),
        "download_png_path": download_png_path,
        "download_pdf_path": download_pdf_path,
        "download_png_url": make_url(download_png_path),
        "download_pdf_url": make_url(download_pdf_path),
        "a4_sheet_url": "",
        "photo_url": make_url(record.get("photo")),
        "audio_url": make_url(record.get("audio")),
        "video_url": make_url(record.get("video")),
        "video_poster_url": make_url(record.get("video_poster") or "media/assets/video-card.jpg"),
        "visibility_label": VISIBILITY_LABELS[record["visibility"]],
        "summary": summarize(str(record["story"])),
    }

    prepared["search_text"] = " ".join(
        [
            str(prepared.get("title", "")),
            str(prepared.get("object_name", "")),
            str(prepared.get("year", "")),
            str(prepared.get("place", "")),
            str(prepared.get("narrator", "")),
            str(prepared.get("co_creator", "")),
            str(prepared.get("story", "")),
            " ".join(prepared.get("tags", [])),
        ]
    ).lower()

    return prepared


def create_qr_image(page_url: str, box_size: int = 12) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=4,
    )
    qr.add_data(page_url)
    qr.make(fit=True)

    return qr.make_image(fill_color="#2f261f", back_color="#fffdf8").convert("RGB")


def build_qr_code(page_url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    create_qr_image(page_url).save(output_path)


def load_export_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = FONT_BOLD_CANDIDATES if bold else FONT_REGULAR_CANDIDATES
    for font_path in candidates:
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)

    raise FileNotFoundError(
        "找不到生成中文故事卡所需的字体。请确认系统中安装了微软雅黑或黑体。"
    )


def wrap_export_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    *,
    max_lines: int | None = None,
) -> list[str]:
    """Wrap Chinese-first text by measured width and optionally add an ellipsis."""
    lines: list[str] = []

    for paragraph in str(text).splitlines() or [""]:
        current = ""
        for character in paragraph:
            candidate = f"{current}{character}"
            if not current or draw.textlength(candidate, font=font) <= max_width:
                current = candidate
                continue

            lines.append(current)
            current = character

        if current:
            lines.append(current)

    if not lines:
        return [""]

    if max_lines is None or len(lines) <= max_lines:
        return lines

    visible = lines[:max_lines]
    last_line = visible[-1]
    while last_line and draw.textlength(f"{last_line}...", font=font) > max_width:
        last_line = last_line[:-1]
    visible[-1] = f"{last_line.rstrip()}..."
    return visible


def fit_export_title(
    draw: ImageDraw.ImageDraw,
    title: str,
    max_width: int,
) -> ImageFont.FreeTypeFont:
    for size in range(88, 42, -2):
        font = load_export_font(size, bold=True)
        if draw.textlength(title, font=font) <= max_width:
            return font
    return load_export_font(42, bold=True)


def draw_export_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    position: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill: str,
    *,
    line_gap: int,
) -> int:
    x, y = position
    bbox = draw.textbbox((0, 0), "中文", font=font)
    line_height = bbox[3] - bbox[1]

    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height + line_gap

    return y


def render_printable_card(item: dict[str, Any]) -> Image.Image:
    """Create a self-contained A6 landscape card at 300 DPI."""
    background = "#fffdf8"
    ink = "#34261e"
    muted = "#806b58"
    accent = "#944b43"
    line = "#dccab5"

    card = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), background)
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        (14, 14, CARD_WIDTH - 14, CARD_HEIGHT - 14),
        radius=28,
        outline="#cbb18f",
        width=3,
        fill=background,
    )
    draw.rounded_rectangle((72, 70, 84, 208), radius=6, fill=accent)

    header_font = load_export_font(28)
    title_font = fit_export_title(draw, item["title"], 1530)
    draw.text((112, 73), "岁月留痕 | 家庭数字记忆档案", font=header_font, fill=muted)
    draw.text((112, 116), item["title"], font=title_font, fill=ink)

    photo_box = (74, 272, 820, 888)
    with Image.open(ROOT / item["photo"]) as source_photo:
        photo = ImageOps.fit(
            source_photo.convert("RGB"),
            (photo_box[2] - photo_box[0], photo_box[3] - photo_box[1]),
            method=Image.Resampling.LANCZOS,
        )
    card.paste(photo, photo_box[:2])
    draw.rounded_rectangle(photo_box, radius=20, outline="#bfa88c", width=3)

    label_font = load_export_font(28)
    value_font = load_export_font(34, bold=True)
    details_x = 888
    detail_rows = (
        ("物件", item["object_name"]),
        ("年代", item["year"]),
        ("地点", item.get("place") or "待确认"),
    )
    detail_y = 280
    for label, value in detail_rows:
        draw.text((details_x, detail_y), label, font=label_font, fill=muted)
        draw.text((details_x + 126, detail_y - 2), value, font=value_font, fill=ink)
        detail_y += 76

    story_label_font = load_export_font(28, bold=True)
    story_font = load_export_font(34)
    draw.text((details_x, 520), "记忆片段", font=story_label_font, fill=accent)
    story_lines = wrap_export_text(draw, item["story"], story_font, 760, max_lines=5)
    draw_export_lines(
        draw,
        story_lines,
        (details_x, 570),
        story_font,
        ink,
        line_gap=11,
    )

    quote_font = load_export_font(36, bold=True)
    quote_lines = wrap_export_text(draw, item["quote"], quote_font, 1460, max_lines=2)
    draw.rounded_rectangle((74, 930, 1372, 1012), radius=15, fill="#f8eeee")
    draw_export_lines(
        draw,
        quote_lines,
        (102, 947),
        quote_font,
        accent,
        line_gap=4,
    )

    draw.line((74, 1056, CARD_WIDTH - 74, 1056), fill=line, width=2)
    footer_font = load_export_font(27)
    draw.text((74, 1090), f"讲述人：{item['narrator']}", font=footer_font, fill=muted)
    draw.text((74, 1135), f"共创人：{item['co_creator']}", font=footer_font, fill=muted)
    draw.text((470, 1090), f"展示范围：{item['visibility_label']}", font=footer_font, fill=muted)
    draw.text((470, 1135), "AI 辅助整理，经本人确认", font=footer_font, fill=muted)

    qr_size = 240
    qr = create_qr_image(item["page_url"], box_size=10).resize(
        (qr_size, qr_size), Image.Resampling.NEAREST
    )
    qr_x, qr_y = 1426, 916
    card.paste(qr, (qr_x, qr_y))
    qr_label_font = load_export_font(23)
    qr_label = "扫码查看完整档案"
    label_width = draw.textlength(qr_label, font=qr_label_font)
    draw.text(
        (qr_x + (qr_size - label_width) / 2, 1164),
        qr_label,
        font=qr_label_font,
        fill=muted,
    )

    return card


def build_a4_sheet(cards: list[Image.Image]) -> Image.Image:
    """Place four A6 landscape cards on an A4 landscape sheet at 300 DPI."""
    sheet = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), "#fffdf8")
    for index, card in enumerate(cards):
        x = (index % 2) * CARD_WIDTH
        y = (index // 2) * CARD_HEIGHT
        sheet.paste(card, (x, y))

    draw = ImageDraw.Draw(sheet)
    draw.line((CARD_WIDTH, 0, CARD_WIDTH, A4_HEIGHT), fill="#b7b0a8", width=2)
    draw.line((0, CARD_HEIGHT, A4_WIDTH, CARD_HEIGHT), fill="#b7b0a8", width=2)
    return sheet


def build_printable_exports(records: list[dict[str, Any]]) -> None:
    """Generate downloadable A6 cards and four-up A4 PDF sheets from the same data."""
    generated_cards: list[tuple[dict[str, Any], Image.Image]] = []

    for item in records:
        card = render_printable_card(item)
        png_path = OUTPUT_DIR / item["download_png_path"]
        pdf_path = OUTPUT_DIR / item["download_pdf_path"]
        png_path.parent.mkdir(parents=True, exist_ok=True)
        card.save(png_path, "PNG", dpi=(CARD_DPI, CARD_DPI), optimize=True)
        card.save(pdf_path, "PDF", resolution=CARD_DPI, quality=92)
        generated_cards.append((item, card))

    for sheet_number, start_index in enumerate(range(0, len(generated_cards), 4), start=1):
        group = generated_cards[start_index : start_index + 4]
        sheet = build_a4_sheet([card for _, card in group])
        relative_path = f"{EXPORT_SHEET_DIR}/sheet-{sheet_number:02d}.pdf"
        sheet_path = OUTPUT_DIR / relative_path
        sheet_path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(sheet_path, "PDF", resolution=CARD_DPI, quality=92)
        sheet_url = make_url(relative_path)
        for item, _ in group:
            item["a4_sheet_url"] = sheet_url


def render_template(
    environment: Environment,
    template_name: str,
    output_path: Path,
    context: dict[str, Any],
) -> None:
    template = environment.get_template(template_name)
    rendered_html = template.render(**context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_html, encoding="utf-8")


def build_site() -> None:
    records = load_records()
    validate_records(records)
    prepared_records = [prepare_record(record) for record in records]

    reset_output_directory()
    copy_public_assets()

    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    )

    shared_context = {
        "site_name": SITE_NAME,
        "base_url": BASE_URL,
        "static_url": make_url("static/style.css"),
        "script_url": make_url("static/script.js"),
    }

    for item in prepared_records:
        build_qr_code(item["page_url"], OUTPUT_DIR / item["qr_path"])

    build_printable_exports(prepared_records)

    render_template(
        environment,
        "index.html",
        OUTPUT_DIR / "index.html",
        {
            **shared_context,
            "records": prepared_records,
            "story_count": len(prepared_records),
            "audio_count": sum(1 for item in prepared_records if item.get("audio_url")),
            "video_count": sum(1 for item in prepared_records if item.get("video_url")),
            "hero_image": make_url("media/assets/hero-cover.png"),
            "exhibition_image": make_url("media/assets/exhibition.jpg"),
            "story_card_image": make_url("media/assets/story-card.jpg"),
            "label_card_image": make_url("media/assets/label-card.jpg"),
            "video_card_image": make_url("media/assets/video-card.jpg"),
        },
    )

    for item in prepared_records:
        render_template(
            environment,
            "family.html",
            OUTPUT_DIR / "f" / item["slug"] / "index.html",
            {**shared_context, "item": item},
        )
        render_template(
            environment,
            "story-card.html",
            OUTPUT_DIR / "cards" / f"{item['id'].lower()}.html",
            {**shared_context, "item": item},
        )

    print(f"网站构建完成：{OUTPUT_DIR}")
    print(f"基础网址：{BASE_URL}")
    for item in prepared_records:
        print(f"- {item['id']}: {item['page_url']}")


if __name__ == "__main__":
    build_site()
