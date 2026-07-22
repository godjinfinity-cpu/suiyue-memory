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

    prepared = {
        **record,
        "page_url": page_url,
        "card_url": card_url,
        "qr_path": qr_relative_path,
        "qr_url": make_url(qr_relative_path),
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


def build_qr_code(page_url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=4,
    )
    qr.add_data(page_url)
    qr.make(fit=True)

    image = qr.make_image(fill_color="#2f261f", back_color="#fffdf8")
    image.save(output_path)


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
