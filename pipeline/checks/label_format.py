"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)

Test:  pytest tests/test_label_format.py -q
ERROR: BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, BOX_OUT_OF_IMAGE, DUP_BOX.  WARN: BOX_TINY, BOX_HUGE.
Ngưỡng đọc từ cfg["label_format"].
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line  # noqa: F401

NAME = "label_format"


def run(ds, cfg):
    p = cfg["label_format"]
    tol, min_px, max_frac, dup_iou = p["overflow_tol"], p["min_box_px"], p["max_box_frac"], p["dup_box_iou"]
    n_classes = len(ds.classes)
    issues = []

    for lab in ds.label_files():
        stem = lab.stem
        size = ds.image_size(stem) if ds.image_path(stem) else None
        seen = []  # (class_id, box) của các dòng hợp lệ phía trên

        for ln_no, text in ds.read_label_lines(stem) or []:
            try:
                c, x, y, w, h = parse_yolo_line(text)
            except ValueError as e:
                issues.append(Issue(NAME, ERROR, "BAD_FORMAT", stem, f"dòng sai định dạng: {e}", ln_no))
                continue
            if not 0 <= c < n_classes:
                issues.append(Issue(NAME, ERROR, "BAD_CLASS_ID", stem, f"id lớp {c} ngoài 0..{n_classes - 1}", ln_no))
                continue
            if w <= 0 or h <= 0:
                issues.append(Issue(NAME, ERROR, "BOX_ZERO", stem, f"box rỗng (w={w}, h={h})", ln_no))
                continue

            overflow = max(0.0, -(x - w / 2), (x + w / 2) - 1, -(y - h / 2), (y + h / 2) - 1)
            if overflow > tol:
                issues.append(Issue(NAME, ERROR, "BOX_OUT_OF_IMAGE", stem, f"box tràn ảnh {overflow:.4f}", ln_no,
                                    {"overflow": round(overflow, 6)}))

            box = (x, y, w, h)
            if any(pc == c and iou_xywh(pb, box) > dup_iou for pc, pb in seen):
                issues.append(Issue(NAME, ERROR, "DUP_BOX", stem, "box trùng với một dòng phía trên (cùng lớp)", ln_no))
            seen.append((c, box))

            if size:
                short_px = min(w * size[0], h * size[1])
                if short_px < min_px:
                    issues.append(Issue(NAME, WARN, "BOX_TINY", stem, f"cạnh ngắn {short_px:.1f}px < {min_px}px", ln_no))
            if w * h > max_frac:
                issues.append(Issue(NAME, WARN, "BOX_HUGE", stem, f"box chiếm {w * h:.2f} diện tích ảnh", ln_no))

    return issues
