# -*- coding: utf-8 -*-
"""
扫描 images/<分类>/ 目录，读取每张照片的 EXIF（相机型号 / ISO / 光圈 /
曝光时间 / 焦距），生成缩略图并输出 photos.js 供网页加载。

用法：
    python scan.py

说明：
  - 新增 / 删除照片后重新运行本脚本即可更新网页。
  - 标题默认按「分类 + 序号」自动生成，可在生成的 captions.json 中自定义，
    再次运行脚本会保留你的修改、并为新照片补充默认标题。
"""

import os
import sys
import json
from PIL import Image, ImageOps, ExifTags

# Windows 控制台默认 GBK，重定向为 UTF-8 以正常打印进度符号
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(ROOT, "images")
THUMBS_DIR = os.path.join(ROOT, "thumbs")
OUTPUT_JS = os.path.join(ROOT, "photos.js")
CAPTIONS_FILE = os.path.join(ROOT, "captions.json")

# 分类显示顺序与中文名（决定侧边栏排序）
CATEGORIES = [
    ("landscape", "风光"),
    ("portrait", "人像"),
    ("animal", "动物"),
    ("still-life", "静物"),
    ("street", "街拍"),
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".heic", ".tif", ".tiff"}
THUMB_MAX = 1100   # 缩略图最长边像素
THUMB_QUALITY = 82

# EXIF 标签名 -> tag id
TAGS = {v: k for k, v in ExifTags.TAGS.items()}


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        try:
            return value[0] / value[1]
        except Exception:
            return None


def fmt_shutter(value):
    x = _to_float(value)
    if x is None or x <= 0:
        return None
    if x >= 1:
        return f"{x:g}s"
    return f"1/{round(1 / x)}s"


def fmt_aperture(value):
    x = _to_float(value)
    return f"f/{x:g}" if x else None


def fmt_focal(value):
    x = _to_float(value)
    return f"{round(x)}mm" if x else None


def clean_model(model):
    if not model:
        return None
    m = str(model).strip().replace("\x00", "")
    # 常见型号美化
    m = m.replace("NIKON Z50_2", "Nikon Z50II")
    m = m.replace("NIKON", "Nikon")
    return m or None


def read_exif(img):
    """返回 dict: camera / iso / aperture / shutter / focal（缺失项为 None）"""
    info = {"camera": None, "iso": None, "aperture": None,
            "shutter": None, "focal": None}
    try:
        exif = img._getexif() or {}
    except Exception:
        exif = {}
    if not exif:
        return info

    def g(name):
        return exif.get(TAGS.get(name))

    info["camera"] = clean_model(g("Model"))

    iso = g("ISOSpeedRatings")
    if isinstance(iso, (list, tuple)):
        iso = iso[0] if iso else None
    if iso:
        info["iso"] = f"ISO{int(iso)}"

    info["aperture"] = fmt_aperture(g("FNumber"))
    info["shutter"] = fmt_shutter(g("ExposureTime"))
    info["focal"] = fmt_focal(g("FocalLength"))
    return info


def make_thumb(img, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    thumb = img.copy()
    thumb.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
    if thumb.mode not in ("RGB", "L"):
        thumb = thumb.convert("RGB")
    thumb.save(dst, "JPEG", quality=THUMB_QUALITY, optimize=True)


def load_captions():
    if os.path.exists(CAPTIONS_FILE):
        try:
            with open(CAPTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            print("⚠ captions.json 解析失败，将忽略。")
    return {}


def clean_orphan_thumbs(valid_thumbs):
    """删除 thumbs/ 下不在 valid_thumbs 中的孤儿缩略图，并清理空目录。

    valid_thumbs: 本次有效缩略图的 normpath 绝对路径集合。
    返回被删除的文件数。
    """
    if not os.path.isdir(THUMBS_DIR):
        return 0
    removed = 0
    for dirpath, _dirnames, filenames in os.walk(THUMBS_DIR):
        for fname in filenames:
            path = os.path.normpath(os.path.join(dirpath, fname))
            if path not in valid_thumbs:
                try:
                    os.remove(path)
                    removed += 1
                    rel = os.path.relpath(path, ROOT).replace("\\", "/")
                    print(f"🗑 删除孤儿缩略图  {rel}")
                except OSError as e:
                    print(f"⚠ 无法删除 {path}: {e}")
    # 清理可能变空的分类子目录
    for dirpath, dirnames, filenames in os.walk(THUMBS_DIR, topdown=False):
        if dirpath != THUMBS_DIR and not dirnames and not filenames:
            try:
                os.rmdir(dirpath)
            except OSError:
                pass
    return removed


def main():
    captions = load_captions()
    photos = []
    counts = {}
    valid_thumbs = set()   # 本次有效的缩略图绝对路径（用于清理孤儿文件）
    valid_srcs = set()     # 本次有效的源文件相对路径（用于清理 captions.json）

    for cat, cat_cn in CATEGORIES:
        src_dir = os.path.join(IMAGES_DIR, cat)
        if not os.path.isdir(src_dir):
            continue
        files = sorted(
            f for f in os.listdir(src_dir)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS
        )
        idx = 0
        for fname in files:
            src = os.path.join(src_dir, fname)
            rel_src = f"images/{cat}/{fname}".replace("\\", "/")
            idx += 1
            try:
                with Image.open(src) as original:
                    exif = read_exif(original)          # 旋正会丢弃 EXIF，先读取
                    img = ImageOps.exif_transpose(original)  # 按方向旋正
                    w, h = img.size
                    stem = os.path.splitext(fname)[0]
                    thumb_rel = f"thumbs/{cat}/{stem}.jpg".replace("\\", "/")
                    thumb_dst = os.path.join(THUMBS_DIR, cat, stem + ".jpg")
                    # 仅当缺失或源文件更新时才重新生成缩略图
                    if (not os.path.exists(thumb_dst)
                            or os.path.getmtime(thumb_dst) < os.path.getmtime(src)):
                        make_thumb(img, thumb_dst)
                        status = "✓ thumb"
                    else:
                        status = "· skip"
            except Exception as e:
                print(f"✗ 跳过 {rel_src}: {e}")
                continue

            valid_thumbs.add(os.path.normpath(thumb_dst))
            valid_srcs.add(rel_src)

            default_title = f"{cat_cn} {idx:02d}"
            title = captions.get(rel_src) or default_title
            captions[rel_src] = title  # 写回，供用户编辑

            photos.append({
                "cat": cat,
                "title": title,
                "file": rel_src,
                "thumb": thumb_rel,
                "w": w,
                "h": h,
                "camera": exif["camera"],
                "iso": exif["iso"],
                "aperture": exif["aperture"],
                "shutter": exif["shutter"],
                "focal": exif["focal"],
            })
            counts[cat] = counts.get(cat, 0) + 1
            print(f"{status}  {rel_src}  [{w}x{h}]  "
                  f"{exif['camera'] or '—'} {exif['focal'] or ''} "
                  f"{exif['aperture'] or ''} {exif['shutter'] or ''} {exif['iso'] or ''}")

    # 清理孤儿缩略图：删除 thumbs/ 中已不再对应任何源图的文件
    removed = clean_orphan_thumbs(valid_thumbs)

    # 清理 captions.json 中已删除照片的标题条目
    stale = [k for k in captions if k not in valid_srcs]
    for k in stale:
        del captions[k]

    # 写回 captions.json（保留用户自定义标题）
    with open(CAPTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(captions, f, ensure_ascii=False, indent=2)

    meta_cats = [{"key": c, "name": n, "count": counts.get(c, 0)}
                 for c, n in CATEGORIES if counts.get(c, 0) > 0]

    payload = {"categories": meta_cats, "photos": photos}
    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("// 由 scan.py 自动生成，请勿手动编辑。\n")
        f.write("// 重新运行 `python scan.py` 可在新增/删除照片后更新本文件。\n")
        f.write("window.PHOTO_DATA = ")
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write(";\n")

    total = len(photos)
    print("\n" + "=" * 48)
    print(f"完成：共 {total} 张照片")
    for c in meta_cats:
        print(f"  {c['name']:<4} {c['count']:>3} 张")
    if removed or stale:
        print(f"已清理：{removed} 个孤儿缩略图，{len(stale)} 条失效标题")
    print(f"已写入 {os.path.relpath(OUTPUT_JS, ROOT)} 和 "
          f"{os.path.relpath(CAPTIONS_FILE, ROOT)}")
    print("=" * 48)


if __name__ == "__main__":
    main()
