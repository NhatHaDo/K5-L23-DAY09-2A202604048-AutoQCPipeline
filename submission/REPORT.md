# Báo cáo Day 09 — Đỗ Thị Huyền, 2A202604048

## 1. Kết luận trước
Pipeline kết luận **Hold** (mã thoát 10). Vào 224 ảnh, cửa vào loại 21, còn **203 ảnh** được QC và xuất ra `submission/export/clean_v1` (bản nháp, chưa phát hành). Sau autofix và 80 ảnh người duyệt, **0 lỗi bắt buộc** còn lại, nhưng **38/203 ảnh (18.7%)** vẫn còn cảnh báo chưa ai xem, vượt ngưỡng Hold 10%. Nguyên nhân chính: hàng đợi duyệt có 125 ảnh, ngân sách chỉ 80.

## 2. Lỗi và phân việc
Số từ `01_intake` và `02_error_list_v1` (mẫu số: 224 ảnh ở cửa vào, 203 ảnh ở QC).

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| DUP_IMAGE_EXACT / DUP_IMAGE_NEAR | 8 / 3 ảnh | máy (loại ở cửa vào) | trùng byte / phash ≤ 8: giữ lại sẽ lệch phân bố, dễ rò rỉ |
| LEAK_TEST | 5 ảnh | máy (loại) | ảnh trùng kho test/val: giữ lại thì mAP test bị thổi phồng |
| CORRUPT_IMAGE / BAD_SIZE | 2 / 3 ảnh | máy (loại) | không mở được / cạnh ngắn < 250px |
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX | 3 + 6 + 4 + 7 dòng | máy (`drop_line`, 20 fix) | lỗi cú pháp, không có cách sửa đúng nên xoá dòng |
| BOX_OUT_OF_IMAGE | 8 dòng | máy (`clip_box`, 8 fix) | cắt về [0,1], giữ nguyên lớp |
| BAD_CLASS_NAME | 2 dòng (data.yaml) | máy (`rename_classes`) | ghi lại `names` theo guideline |
| MISSING_LABEL_FILE | 6 ảnh | **người** (`needs_label`) | máy không bịa nhãn; file rỗng nghĩa là "ảnh nền", khác "chưa gán" |
| POSSIBLE_MISSING / WRONG_CLASS / LOOSE_BOX / FALSE_POS | 52 / 18 / 24 / 27 ảnh | **người** | lỗi ngữ nghĩa; model lớn cũng có thể sai nên chỉ cảnh báo |
| EMPTY_LABEL, BOX_TINY, BOX_HUGE, CLASS_RARE | 12 / 4 / 3 / 1 ảnh | **người** | cần mắt người để phân biệt ảnh nền hay thiếu nhãn, vật nhỏ thật hay box sai |

Toàn bộ 35 thay đổi của máy có dấu vết trước → sau trong `03_fixes.csv`; `data/raw` không bị sửa.

**Hàng đợi (`05_review_queue.csv`, 125 ảnh):** ảnh thiếu file nhãn (`NEEDS_LABEL`) và ảnh vừa bị máy xoá dòng lên đầu (img_0020, img_0031, img_0053…), vì nếu không gán thì chắc chắn Rework. Tiếp theo là ảnh có nhiều cảnh báo và conf model cao. Với ngân sách 80 ảnh, người duyệt xem được 80 ảnh, trong đó 74 ảnh có cảnh báo ngữ nghĩa. Còn 45 ảnh không được xem, và 38 trong số đó vẫn mang cảnh báo ở `07_error_list_v3` (21 FALSE_POS, 20 LOOSE_BOX, 12 MISSING, 3 WRONG_CLASS, cùng 4 EMPTY_LABEL, 5 BOX_TINY, 3 BOX_HUGE; một ảnh có thể dính nhiều mã).

## 3. Calibration (2 ngưỡng)
Số từ `submission/calibration/calibration_report.md` (bộ calib 39 ảnh).

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | **8** | DUP_IMAGE_NEAR: 1.00 / 0.50 → 1.00 / 0.67 (EXACT giữ 1.00 / 1.00) | Recall tăng mà precision giữ 1.00. 8 nằm giữa vùng ổn định 4–14 (cùng F1 0.80), không đứng sát mép. Không chọn 16 dù F1 calib cao nhất (0.91), lý do ở đoạn dưới |
| `second_opinion.conf` | 0.25 | **0.6** | WRONG_CLASS 0.56 / 0.83 → 0.62 / 0.83; MISSING 0.50 / 1.00 → 0.57 / 1.00; LOOSE_BOX 0.29 / 0.40 → 0.20 / 0.20 | Giữ recall MISSING = 1.00: thiếu nhãn hại train nhiều nhất. Precision MISSING và WRONG_CLASS tăng, hàng đợi giảm 143 → 125 ảnh. Đánh đổi: LOOSE_BOX recall giảm. Không lên 0.8 (sẽ ra Release) vì MISSING recall rơi còn 0.75, tức bỏ sót 1/4 ảnh thiếu nhãn |

**Chỗ calibration đánh lừa:** trên calib, `phash_dist = 16` có F1 tốt nhất (0.91 so với 0.80). Nhưng calib chỉ có 6 cặp trùng gần đúng, và chạy trên lô raw thì số ảnh bị loại ở cửa vào nhảy từ **21 (pd=8) lên 31 (pd=16)**: 10 ảnh thêm bị coi là trùng, trong khi pd từ 4 đến 12 chỉ dao động 19–22. Lô raw có nhiều cảnh đường phố na ná nhau, nên ngưỡng lỏng sẽ loại nhầm ảnh khác nhau. Tối ưu F1 trên 39 ảnh calib sẽ làm mất ~5% dữ liệu thật. Tương tự, `conf = 0.8` "đẹp" trên calib (WRONG_CLASS precision 1.00) và cho Release, nhưng đó là tối ưu cho cổng chứ không phải cho chất lượng nhãn.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
**(a) Gate chặn đúng.** Chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb`, tức không có người duyệt: 6 ảnh `MISSING_LABEL_FILE` (img_0031, img_0053, img_0126, img_0135, img_0170, img_0219) vẫn còn. Kết luận **REWORK — còn 6 lỗi bắt buộc**, mã thoát **20**, log in `KHÔNG xuất: còn lỗi bắt buộc`, và thư mục `work/exp_nb/clean_v1` **không được tạo**. Test e2e `test_export_on_rework_flag` cũng kiểm đúng điều này.

**(b) Điểm mù có bằng chứng:**
- **Box lỏng nhẹ:** trên calib, `POSSIBLE_LOOSE_BOX` ở conf 0.6 chỉ có recall 0.20 (bắt 1/5). Box lệch ít, IoU với model ≥ 0.5, thì máy coi là khớp.
- **Ảnh trùng biến đổi mạnh:** `DUP_IMAGE_NEAR` recall 0.67, bỏ sót 2/6 cặp trên calib (cắt/xoay mạnh làm phash khác xa). Nếu cặp đó lọt vào cả train lẫn test thì vẫn rò rỉ.
- **FALSE_POS nhiều báo động giả:** precision 0.31 (11 FP / 16 cờ trên calib). Model bỏ sót vật nhỏ/che khuất thì nhãn đúng bị cờ, tốn ngân sách người duyệt.
- **Nhầm lớp mà model lớn cũng nhầm** (truck ↔ bus/car): không có ý kiến thứ hai khác nên không bắt được (WRONG_CLASS bỏ sót 1/6 trên calib).

**Lỗi tự nhìn thấy khi xem `viz_labels.py`:**
- <<ĐIỀN: ảnh img_XXXX — lỗi gì>>
- <<ĐIỀN: ảnh img_XXXX — lỗi gì>>
- <<ĐIỀN: ảnh img_XXXX — lỗi gì>>

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Chưa chạy. Phần train trên Colab là tùy chọn; bài nộp chỉ gồm phần lõi (`make check-core`). Bản export `clean_v1` đã commit sẵn để train sau.

## 6. Quyết định và ghi chú AI
**(a) Quyết định:** **Hold**. Không còn lỗi bắt buộc nhưng 18.7% ảnh còn cảnh báo chưa duyệt. Điều kiện để thành Release: duyệt thêm ít nhất ~18 trong 38 ảnh còn cảnh báo (đưa tỉ lệ xuống < 10%), tức tăng ngân sách duyệt từ 80 lên khoảng 100 ảnh, ưu tiên các ảnh POSSIBLE_MISSING còn lại. Không hạ ngưỡng conf chỉ để qua cổng.

**(b) Dùng AI:**
- Prompt chính: viết 4 module theo docstring + test có sẵn, giữ ngưỡng đọc từ `cfg`.
- Cách kiểm: chạy `pytest` từng module rồi toàn bộ (79 passed), chạy `make run` và đọc `02/07_error_list`, chạy thử nhiều cặp ngưỡng trên raw để kiểm số ảnh bị loại.