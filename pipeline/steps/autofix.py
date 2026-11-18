"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.

Test:  pytest tests/test_autofix.py -q
drop_line: BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX · clip_box: BOX_OUT_OF_IMAGE (hết diện tích -> drop_line)
needs_label: MISSING_LABEL_FILE (không tạo file) · rename_classes: BAD_CLASS_NAME
remove_image: DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE.  Không động tới WARN.
"""
from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line

DROP = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
CLIP = {"BOX_OUT_OF_IMAGE"}
REMOVE = {"DUP_IMAGE_EXACT", "DUP_IMAGE_NEAR", "LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def _fx(image, line, action, before, after):
    return {"image": image, "line": line, "action": action, "before": before, "after": after}


def _clip(text):
    """Cắt box về [0,1]; trả None nếu sau khi cắt không còn diện tích."""
    c, x, y, w, h = parse_yolo_line(text)
    x1, x2 = max(0.0, x - w / 2), min(1.0, x + w / 2)
    y1, y2 = max(0.0, y - h / 2), min(1.0, y + h / 2)
    if x2 <= x1 or y2 <= y1:
        return None
    return f"{c} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}"


def fix(ds, issues, cfg):
    errors = [i for i in issues if i.severity == ERROR]
    fixes = []

    # 1) Xoá ảnh trước, để các lỗi dòng của ảnh đó được bỏ qua êm
    removed = set()
    for i in errors:
        if i.code in REMOVE and i.image not in removed:
            removed.add(i.image)
            img = ds.image_path(i.image)
            if img is not None:
                img.unlink()
            lab = ds.label_path(i.image)
            if lab.exists():
                lab.unlink()
            fixes.append(_fx(i.image, None, "remove_image", img.name if img else i.image, f"đã xoá ({i.code})"))

    # 2) Sửa data.yaml một lần nếu tên lớp sai
    if any(i.code == "BAD_CLASS_NAME" for i in errors):
        d = {}
        if ds.yaml_path.exists():
            d = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
        before = d.get("names")
        d["names"] = {k: n for k, n in enumerate(cfg["classes"])}
        ds.yaml_path.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
        fixes.append(_fx("data.yaml", None, "rename_classes", str(before), str(d["names"])))

    # 3) Gom lỗi dòng theo file, sửa theo số dòng GỐC rồi ghi lại một lần
    by_file = defaultdict(dict)  # stem -> {line: "drop" | "clip"}
    for i in errors:
        if i.image in removed or i.line is None:
            continue
        if i.code in DROP:
            by_file[i.image][i.line] = "drop"            # xoá dòng luôn thắng
        elif i.code in CLIP:
            by_file[i.image].setdefault(i.line, "clip")

    for stem in sorted(by_file):
        p = ds.label_path(stem)
        if not p.exists():
            continue
        src = p.read_text(encoding="utf-8", errors="replace").splitlines()
        out = []
        for n, text in enumerate(src, 1):
            act = by_file[stem].get(n)
            if act == "clip":
                try:
                    new = _clip(text)
                except ValueError:
                    new = None
                if new is None:
                    act = "drop"
                else:
                    out.append(new)
                    fixes.append(_fx(stem, n, "clip_box", text, new))
                    continue
            if act == "drop":
                fixes.append(_fx(stem, n, "drop_line", text, "(đã xoá)"))
                continue
            out.append(text)
        p.write_text("".join(ln + "\n" for ln in out), encoding="utf-8")

    # 4) Ảnh chưa có nhãn: máy không bịa nhãn, chuyển người gán
    for i in errors:
        if i.code == "MISSING_LABEL_FILE" and i.image not in removed:
            fixes.append(_fx(i.image, None, "needs_label", "(không có file)", "chuyển người gán"))

    return fixes
