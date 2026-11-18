"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework.

Test:  pytest tests/test_gate.py -q
  còn >= 1 lỗi bắt buộc (ERROR)                                   -> "Rework"
  không còn ERROR nhưng tỉ lệ ẢNH còn cảnh báo >= warn_ratio_hold -> "Hold"
  còn lại                                                         -> "Release"
"""
from ..common import ERROR, WARN  # noqa: F401


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    stems = set(image_stems)
    reviewed = set(reviewed)
    hold_ratio = cfg["gate"]["warn_ratio_hold"]

    # Lỗi bắt buộc: đếm TẤT CẢ (kể cả cấp dataset, kể cả ảnh đã duyệt) — không được bỏ qua
    n_errors = sum(1 for i in issues if i.severity == ERROR)
    warn_images = {i.image for i in issues
                   if i.severity == WARN and i.image in stems and i.image not in reviewed}
    n_images = len(stems)
    ratio = round(len(warn_images) / n_images, 4) if n_images else 0.0

    if n_errors:
        decision = "Rework"
        reasons = [f"còn {n_errors} lỗi bắt buộc (ERROR) chưa sửa"]
    elif ratio >= hold_ratio:
        decision = "Hold"
        reasons = [f"{len(warn_images)}/{n_images} ảnh ({ratio:.1%}) còn cảnh báo chưa duyệt, >= ngưỡng {hold_ratio:.0%}"]
    else:
        decision = "Release"
        reasons = [f"0 lỗi bắt buộc; {len(warn_images)}/{n_images} ảnh ({ratio:.1%}) còn cảnh báo, < ngưỡng {hold_ratio:.0%}"]

    return {"decision": decision, "n_errors": n_errors, "n_warn_images": len(warn_images),
            "n_images": n_images, "warn_ratio": ratio, "reasons": reasons}
