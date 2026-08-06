# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trần Duy Trường |
| MSSV | 2A202601247 |
| Khóa/Lớp | K3 - E403 |
| Tên nhóm | A5-01 |
| Vai trò chính | Data Observability Owner |
| Repository | [github.com/TruongIKPK/K3_Day10_Data-Pipeline-Data-Observability-A501](https://github.com/TruongIKPK/K3_Day10_Data-Pipeline-Data-Observability-A501) |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data quality checks | `src/observability/quality.py` — `run_data_quality_checks()` | Clean DataFrame, `Settings`, tên report | Structured quality payload và `data/quality/quality_<state>.json` | Hoàn thành cho baseline, đã chạy tích hợp |
| Freshness monitoring | `src/observability/quality.py` — `build_freshness_report()` | DataFrame, `Settings`, output path | Latest/oldest date, stale count/ratio, threshold và freshness status | Hoàn thành cho baseline, đã chạy tích hợp |
| Baseline Markdown reporting | `src/observability/reporting.py` — `generate_phase1_report()` | Source summary, metrics, quality, freshness | `data/reports/phase1_report.md` | Hoàn thành chức năng Phase 1 |
| Corruption comparison reporting | `src/observability/reporting.py` — `generate_corruption_report()` | Baseline/corrupted/repaired metrics, quality và freshness | Báo cáo so sánh ba trạng thái | Chưa hoàn thành; hàm hiện còn `NotImplementedError` |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Xác minh baseline end-to-end | `src/pipelines/phase1.py` | Quality, freshness và Markdown artifacts được tạo trong cùng lần chạy với metrics |
| Cung cấp observability contract cho corruption flow | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py` | Đã có schema quality/freshness dùng chung; phần comparison report cần hoàn thiện khi Phase 2 có artifacts |

Tôi chỉ nhận ownership trực tiếp đối với `quality.py` và `reporting.py`. Các metrics retrieval/answer và orchestration được sử dụng làm input hoặc bằng chứng tích hợp, không phải phần code tôi nhận sở hữu.

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Xây dựng schema chung cho từng quality check | `run_data_quality_checks()` | Mỗi check có `name`, `dimension`, `expectation`, `observed`, `success`, `affected_rows` | Đọc `data/quality/quality_baseline.json` |
| Kiểm tra quy mô và document identity | `row_count`, `paper_id_not_null`, `paper_id_unique` | Xác minh tối thiểu 4 rows, ID hiện diện và duy nhất | Baseline có 24 rows, cả 3 checks PASS |
| Kiểm tra title, summary và embedding text | `title_present`, `title_not_truncated`, `summary_present`, `embedding_text_present` | Phát hiện blank fields và title dưới 8 ký tự | Baseline có 0 affected rows cho các checks này |
| Kiểm tra ngày và freshness | `published_parseable`, `freshness_threshold` | Phát hiện ngày không parse được, `age_days` thiếu, âm hoặc vượt ngưỡng cấu hình | Baseline có 0 invalid/stale rows |
| Tổng hợp quality status | `run_data_quality_checks()` | Tính số checks pass/fail và status tổng thể | `checks_passed=9`, `checks_failed=0`, `status=PASS` |
| Tạo freshness artifact độc lập | `build_freshness_report()` | Latest/oldest published, stale rows/ratio, threshold và `is_fresh` | `data/quality/freshness_report.json` |
| Tạo baseline report | `generate_phase1_report()` | Tổng hợp source, evaluation metrics, quality checks, freshness và interpretation | `data/reports/phase1_report.md` |
| Bảo đảm claim có evidence | Phần Interpretation của baseline report | Nhắc rằng nhận định retrieval/answer phải đối chiếu metrics và answers cùng run | Đọc phần cuối Phase 1 report |

Các commit liên quan trực tiếp tới module observability: `6e301fb031c095c09b224dd45daa9aa5c604a687` và `9dfd152c17cc6e1bc64f3f7a5d29c0c4238c7eae`, cùng có commit message `update observability`.

Output cụ thể của lần chạy xác minh gần nhất:

- Tổng số clean rows được kiểm tra: 24.
- Quality checks: 9/9 PASS, 0 failed checks.
- Freshness: 0/24 stale rows, stale ratio 0.0, threshold 180 ngày.
- Khoảng ngày xuất bản: từ `2026-02-12` đến `2026-08-01`.
- Baseline Markdown report đã được sinh tại `data/reports/phase1_report.md`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline có thể chạy hết mà dữ liệu vẫn sai hoặc xuống cấp. Retrieval metrics chỉ phản ánh khả năng trả lời trên evaluation set, không trực tiếp cho biết document ID có trùng, trường bắt buộc có rỗng, title có bị truncate, ngày có hợp lệ hoặc dữ liệu đã stale hay chưa. Vì vậy cần một lớp observability tạo signal có cấu trúc và artifact độc lập để phát hiện lỗi trước khi diễn giải chất lượng agent.

### Cách triển khai quality checks

1. Tạo helper `add_check()` để mọi check dùng chung schema và ép kiểu kết quả về JSON-safe values.
2. Đo completeness qua row count, ID, title, summary và embedding text.
3. Đo uniqueness qua duplicate `paper_id` với `keep=False` để đếm toàn bộ rows liên quan.
4. Đo validity qua title tối thiểu 8 ký tự và khả năng parse `published`.
5. Đo freshness bằng `age_days`; coi giá trị thiếu, âm hoặc lớn hơn `freshness_threshold_days` là stale.
6. Tổng hợp số check pass/fail; chỉ trả `PASS` khi toàn bộ checks thành công.
7. Ghi payload theo tên trạng thái, ví dụ `quality_baseline.json`, để về sau có thể tách baseline, corrupted và repaired.

### Cách triển khai freshness và reporting

1. Parse toàn bộ `published`, bỏ giá trị invalid khi tính min/max.
2. Tính `stale_rows`, `stale_ratio`, `threshold_days` và `is_fresh` trong artifact freshness riêng.
3. `generate_phase1_report()` nhận các payload đã sinh thay vì đọc lại dữ liệu nguồn, giúp report phản ánh đúng artifacts của cùng lần chạy.
4. Sinh bảng source summary, evaluation metrics, từng quality check và freshness status.
5. Trạng thái Ragas được ghi là `skipped` nếu pipeline chưa bật lượt đánh giá Ragas.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Quality input | Clean `pandas.DataFrame`, `Settings` chứa paths/threshold, và `report_name` |
| Quality output | Dict có `report_name`, timestamp, row count, tổng pass/fail, status và danh sách checks; đồng thời ghi JSON |
| Freshness input | DataFrame có `published`, `age_days`; threshold lấy từ `Settings` |
| Freshness output | Dict/JSON có latest, oldest, stale rows/ratio, total rows, threshold và `is_fresh` |
| Reporting input | Source summary, evaluation metrics, quality payload và freshness payload |
| Reporting output | Markdown report ở đường dẫn pipeline truyền vào |
| Module phụ thuộc | `core.config.Settings`, `core.utils.now_utc`, `write_json`, `write_text`, `pandas` |
| Module sử dụng output | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, báo cáo nhóm và người đánh giá |
| Điều kiện lỗi cần xử lý | DataFrame rỗng; thiếu cột; ID/title/summary blank; duplicate ID; ngày invalid; `age_days` thiếu, âm hoặc vượt threshold |

### Cách xác minh

Lệnh PowerShell đã chạy tại repository root:

```powershell
$env:REFRESH_SOURCE='false'
$env:REFRESH_TEST_SET='false'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe script\run_phase1.py
```

- **Kết quả mong đợi:** Pipeline tạo quality JSON, freshness JSON và baseline Markdown report; các giá trị giữa ba artifacts phải nhất quán.
- **Kết quả thực tế:** Exit code 0; 24 clean rows; 16 evaluation samples; quality 9/9 PASS; freshness 0 stale rows.
- **Artifact/log:** `data/quality/quality_baseline.json`, `data/quality/freshness_report.json`, `data/reports/phase1_report.md`, `data/results/baseline_metrics.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Một cờ PASS/FAIL tổng thể không đủ để debug vì không cho biết dimension nào hỏng và bao nhiêu rows bị ảnh hưởng.
- **Các phương án đã cân nhắc:** Chỉ trả về boolean; ném exception ngay khi gặp lỗi đầu tiên; hoặc thu thập toàn bộ checks vào structured payload.
- **Phương án đã chọn:** Thu thập mọi check với `dimension`, expectation, observed value, success và affected rows; sau đó tính status tổng thể.
- **Lý do:** Structured payload dễ lưu JSON, dễ dựng Markdown report, cho phép xem nhiều lỗi trong một lượt chạy và có thể tái sử dụng cho baseline/corrupted/repaired. Trade-off là pipeline không tự dừng chỉ vì status FAIL; orchestration phải quyết định policy fail-fast.
- **Bằng chứng quyết định phù hợp:** `quality_baseline.json` chứa đủ 9 checks thuộc completeness, uniqueness, validity và freshness; report hiển thị từng check thay vì chỉ ghi PASS chung.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Starter code của `run_data_quality_checks()`, `build_freshness_report()` và `generate_phase1_report()` dừng bằng `NotImplementedError`, khiến Phase 1 không thể tạo observability artifacts.
- **Bước tái hiện:** Chạy baseline trên phiên bản starter trước các commit observability; pipeline dừng khi gọi hàm quality/reporting chưa triển khai.
- **Nguyên nhân gốc:** Đây là các hàm bài tập được để stub, chưa có logic tính signal và ghi artifact.
- **Cách xử lý:** Triển khai 9 quality checks, freshness aggregation, JSON persistence và Markdown baseline report.
- **Cách xác minh sau khi sửa:** Chạy `script/run_phase1.py` offline; pipeline hoàn tất và sinh đủ ba artifacts observability với số liệu nhất quán.
- **Điều học được:** Observability cần được tích hợp như một output bắt buộc của pipeline, không phải thao tác kiểm tra thủ công sau cùng.

Blocker còn lại:

- **Phạm vi bị ảnh hưởng:** `generate_corruption_report()` và báo cáo comparison của Phase 2.
- **Những gì đã loại trừ:** Baseline quality, baseline freshness và Phase 1 report đều đã sinh được; blocker không nằm ở raw/clean data.
- **Bước tiếp theo:** Triển khai comparison report sau khi corruption flow cung cấp đầy đủ corrupted/repaired metrics, quality và freshness. Đồng thời bổ sung dòng Markdown separator cho bảng Freshness trong Phase 1 report để bảo đảm bảng render chuẩn trên GitHub.

## 7. Hiểu biết về luồng end-to-end

1. Crossref response được lưu raw và parse thành records. Cleaning chuẩn hóa records, tạo `age_days` và `text_for_embedding`. Embedding model mã hóa text, ChromaDB lưu vector cùng document ID để QA truy xuất context.
2. Evaluation set chứa `question`, `ground_truth` và `ground_truth_doc_ids`. Retrieval hit kiểm tra document đúng có xuất hiện trong kết quả hay không; token F1 và judge đánh giá câu trả lời so với ground truth.
3. Quality checks đo completeness, uniqueness, validity và freshness ở mức dữ liệu. Freshness report đi sâu vào phạm vi thời gian, stale count/ratio và trạng thái theo threshold. Hai loại signal bổ sung cho nhau nhưng không thay thế retrieval metrics.
4. Baseline, corrupted và repaired phải dùng cùng test set để metric delta phản ánh thay đổi dữ liệu. Nếu đổi câu hỏi, không thể quy nguyên nhân giảm điểm cho corruption.
5. Repair thành công khi repaired quality/freshness phục hồi, record/document IDs phù hợp baseline và agent metrics trên cùng test set trở lại gần baseline. Hiện chưa có corrupted/repaired artifacts nên chưa thể xác nhận kết quả repair.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0 | Chưa có artifact | Chưa có artifact | Baseline retrieval tìm đúng ground-truth document cho 16/16 samples |
| `mean_token_f1` | 1.0 | Chưa có artifact | Chưa có artifact | Exact lookup đang trả đúng trường metadata tương ứng |
| `judge_accuracy` | 1.0 | Chưa có artifact | Chưa có artifact | Judge đang dùng fallback khi chưa cấu hình LLM thật |
| `mean_judge_score` | 5.0 | Chưa có artifact | Chưa có artifact | Điểm xác nhận wiring baseline, chưa đủ để kết luận chất lượng generative QA |
| Quality checks | 9/9 PASS | Chưa có artifact | Chưa có artifact | Không có affected rows trong 9 baseline checks |
| Freshness status | PASS; 0/24 stale | Chưa có artifact | Chưa có artifact | Stale ratio 0.0 với threshold 180 ngày |

### Kết luận từ số liệu

Tại thời điểm báo cáo, chuỗi có bằng chứng đầy đủ là:

1. Clean baseline 24 rows → quality 9/9 PASS và freshness PASS → retrieval/answer metrics đạt 1.0 trên 16 samples.
2. Corruption/repair → chưa có quality, freshness và metrics artifacts → chưa được phép kết luận mức giảm hoặc phục hồi.

Chưa thể xác định corruption nào ảnh hưởng rõ nhất. Khi Phase 2 hoàn thành, cần đối chiếu `affected_rows` của từng check với delta retrieval/F1 trên cùng test set để tránh suy luận chỉ từ aggregate score.

Kết quả cần diễn giải thận trọng là các agent metrics đều hoàn hảo trong khi Ragas bị skip và LLM judge dùng fallback. Điều này chứng minh pipeline, document identity và evaluator đang nối đúng, nhưng không thay thế kiểm thử chất lượng trả lời bằng LLM thật.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data observability cần signal có cấu trúc, dimension và affected-row count; một cờ PASS chung không đủ để tìm nguyên nhân.
2. Freshness là một thuộc tính động phụ thuộc run date và threshold, nên phải lưu timestamp/threshold cùng artifact để kết quả có thể audit.
3. Quality PASS không đồng nghĩa agent tốt; cần đặt quality/freshness cạnh retrieval và answer metrics mới thấy được chuỗi tác động từ dữ liệu tới RAG.

### Nếu có thêm thời gian

Tôi sẽ hoàn thiện `generate_corruption_report()`, sửa Markdown table separator, rồi bổ sung unit tests với DataFrame rỗng, thiếu required columns, duplicate IDs, invalid dates và stale ages. Cải thiện được đo bằng test coverage, khả năng phát hiện từng injected corruption và sự nhất quán tự động giữa JSON artifacts với số liệu trong Markdown report.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Duy Trường

**Ngày xác nhận:** 2026-08-06
