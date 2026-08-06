# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                                                                                           |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Họ và tên       | Nguyễn Khánh Toàn                                                                                                                                |
| MSSV               | 2A202601843                                                                                                                                          |
| Khóa/Lớp         | K3                                                                                                                                                  |
| Tên nhóm         | A5-01                                                                                                                                               |
| Vai trò chính    | Corruption & Integration Owner                                                                                                                      |
| Repository         | [github.com/TruongIKPK/K3_Day10_Data-Pipeline-Data-Observability-A501](https://github.com/TruongIKPK/K3_Day10_Data-Pipeline-Data-Observability-A501) |
| Ngày hoàn thành | 2026-08-06                                                                                                                                          |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------- |
| Data corruption simulation | `src/ingestion/corruption.py` / `corrupt_clean_dataframe` | Clean `pd.DataFrame` (16 cột theo Clean Schema) | Corrupted `pd.DataFrame` + `data/results/corruption_log.json` | Hoàn thành |
| Corruption → Evaluate → Repair → Compare orchestration | `src/pipelines/corruption_flow.py` / `main` | Baseline artifacts (`clean.json`, `baseline_metrics.json`), `raw_records.json` | `papers_clean_corrupted/repaired.{csv,json}`, `corrupted/repaired_metrics.json`, `quality_corrupted/repaired.json`, `freshness_corrupted/repaired.json` | Một phần — mọi bước tới repair+evaluate+quality/freshness đã verify; bước cuối (sinh `corruption_report.md`) đang blocked, xem mục 6 |
| LLM call timeout hardening | `src/retrieval/llm.py` / `build_llm` (nhánh Gemini) | `Settings` | `ChatGoogleGenerativeAI` với `timeout=30.0` | Hoàn thành |

Phần việc của tôi nằm ở cuối pipeline: nhận clean dataframe và baseline artifact từ Thành viên 2 (`cleaning.py`, `testset.py`), mô phỏng lỗi dữ liệu thực tế trên bản sao, đánh giá lại bằng chính module evaluation/index của Thành viên 3–4, sau đó repair bằng cách rebuild từ raw records và so sánh ba trạng thái baseline/corrupted/repaired.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ----------------------------- | ------------------------------------ | ---------------------------- |
| Debug lỗi `build_test_set` luôn raise `ValueError: At least four complete documents...` | Thành viên phụ trách `evaluation/testset.py`, `ingestion/cleaning.py` | Xác định root cause: Crossref API không trả trường `subject` cho bất kỳ record nào (đã kiểm tra thực nghiệm với 100 record), khiến `categories_joined` luôn rỗng. Kết quả cuối được teammate merge chính thức bằng fallback `"Uncategorized"` trong `cleaning.py` (commit `277112b`), thay cho patch tạm thời của tôi. |
| Fix môi trường cài đặt `pip install -e .` | Toàn nhóm | Máy chạy Python 3.14 không tương thích `requires-python = ">=3.11,<3.14"`; tạo `.venv` bằng Python 3.13, cài đặt thành công toàn bộ dependency. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ---------------- |
| Implement 6 loại corruption có kiểm soát, seed cố định để tái lập được | `src/ingestion/corruption.py` / `corrupt_clean_dataframe` | Corrupted DataFrame (24 dòng) + `data/results/corruption_log.json` liệt kê từng hành động và `paper_id` bị ảnh hưởng | `.venv/bin/python script/run_corruption_flow.py` rồi `cat data/results/corruption_log.json` |
| Ghép orchestration corrupt → evaluate → repair → evaluate | `src/pipelines/corruption_flow.py` / `main` | `data/clean/papers_clean_corrupted.{csv,json}`, `papers_clean_repaired.{csv,json}`, `corrupted_metrics.json`, `repaired_metrics.json`, `quality_corrupted.json`, `quality_repaired.json`, `freshness_corrupted.json`, `freshness_repaired.json` | Đọc trực tiếp các file JSON trên, đối chiếu số liệu với `baseline_metrics.json`/`quality_baseline.json` |
| Thêm `timeout=30.0` cho `ChatGoogleGenerativeAI` để tránh treo vô hạn khi quota API hết | `src/retrieval/llm.py` / `build_llm` | LLM client raise exception có kiểm soát thay vì treo, `_judge_answer` fallback về heuristic đúng thiết kế | Gọi `build_llm(settings).invoke('Say OK')` trực tiếp với API key thật, đo thời gian tới khi exception được raise |

**Output cụ thể:** `data/results/corruption_log.json` ghi nhận 6 loại corruption, mỗi loại tác động 2/24 record (drop 2 record mới nhất, blank summary 2 record, inject noise 2 record, truncate title 2 record, làm cũ ngày publish 2 record, duplicate 2 record). Kết quả đo được: `quality_corrupted.json` chuyển từ 9/9 PASS (baseline) xuống 5/9 PASS (FAIL 4 check: `paper_id_unique`, `title_not_truncated`, `summary_present`, `freshness_threshold`); `freshness_corrupted.json` chuyển từ FRESH sang STALE (`stale_rows=2`, `stale_ratio=0.083`); `corrupted_metrics.json` cho `retrieval_hit_rate` giảm từ 1.0 xuống 0.5. Sau khi repair (rebuild từ `raw_records.json`), `repaired_metrics.json` khớp chính xác `baseline_metrics.json`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Bài lab cần một cách có kiểm soát, tái lập được để mô phỏng các lỗi dữ liệu thực tế thường gặp trong data pipeline (record bị mất, field bị blank, text bị nhiễu, field bị truncate, dữ liệu cũ đi, record trùng lặp), từ đó đo mức độ suy giảm chất lượng retrieval/answer khi dữ liệu bị hỏng, và chứng minh rằng repair (rebuild từ raw source) khôi phục lại chất lượng ban đầu. Đồng thời cần ghép các module do các thành viên khác viết (cleaning, evaluation, quality/freshness, index) thành một pipeline `corruption_flow.py` chạy được end-to-end.

### Cách triển khai

**`corrupt_clean_dataframe()`** dùng `random.Random(seed=42)` để mọi lần chạy cho ra cùng tập record bị ảnh hưởng (bắt buộc để so sánh công bằng giữa các lần chạy). Mỗi loại corruption tác động ngẫu nhiên ~10% số dòng (tối thiểu 1 dòng), các loại được lấy mẫu độc lập nên một dòng có thể bị ảnh hưởng bởi nhiều loại cùng lúc — mô phỏng đúng thực tế lỗi dữ liệu không loại trừ lẫn nhau:

1. `drop_latest_records` — sort theo `published` giảm dần, drop các record **mới nhất** (không xuống dưới 4 dòng để không vi phạm ràng buộc tối thiểu của baseline). Đây là loại corruption duy nhất khiến document biến mất hoàn toàn khỏi index.
2. `blank_summary` — set `summary=""` trên vài dòng, vi phạm check `summary_present`.
3. `inject_noise` — nối chuỗi nhiễu cố định vào summary còn nội dung, mô phỏng lỗi encoding/scrape mà không làm summary rỗng hẳn.
4. `truncate_title` — cắt `title` còn 5 ký tự, vi phạm check `title_not_truncated` (yêu cầu ≥ 8 ký tự trong `quality.py`).
5. `stale_published_date` — set `published` lùi 3650 ngày và `age_days=3650`, vượt xa `freshness_threshold_days=180`.
6. `duplicate_rows` — nối thêm bản sao của vài dòng, vi phạm check `paper_id_unique`.

Sau khi mutate, `text_for_embedding` và `summary_chars` được **rebuild lại** theo đúng công thức trong `cleaning.py`, để corrupted row cho ra embedding "hợp lý nhưng sai" thay vì text cũ không khớp field đã sửa. Toàn bộ hành động + `paper_id` bị ảnh hưởng được ghi vào `corruption_log.json` để truy vết.

**`corruption_flow.main()`** đọc lại artifact baseline đã có trên đĩa (`clean.json`, `baseline_metrics.json`) thay vì fetch lại từ Crossref, giữ tính tái lập và không phụ thuộc network; gọi `corrupt_clean_dataframe`, ghi CSV/JSON, build lại Chroma index riêng cho corrupted (collection name khác nhờ `_derive_collection_name` trong `index.py`), evaluate bằng **cùng** `test_set.json` với baseline. Bước repair đọc lại `raw_records.json` (chưa từng bị corrupt) và chạy lại `build_clean_dataframe` — y hệt cách baseline được tạo — thay vì "vá" trực tiếp bản corrupted (xem quyết định ở mục 5).

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | `corrupt_clean_dataframe`: `pd.DataFrame` (Clean Schema) + `Path output_log_path`. `corruption_flow.main`: không tham số, đọc `Settings` + artifact trên đĩa |
| Output | `corrupt_clean_dataframe`: `pd.DataFrame` cùng schema (số dòng đổi do drop/duplicate) + JSON log. `corruption_flow.main`: 2 bộ CSV/JSON, 2 bộ metrics/answers, 2 bộ quality/freshness report |
| Module phụ thuộc | `ingestion.cleaning` (`build_clean_dataframe` cho bước repair), `ingestion.crossref` (`load_raw_records`), `evaluation.metrics` (`evaluate_pipeline`), `observability.quality` (`run_data_quality_checks`, `build_freshness_report`), `retrieval.index` (`LocalEmbeddingIndex`), `observability.reporting` (`generate_corruption_report` — hiện là stub, xem mục 6) |
| Module sử dụng output | `script/run_corruption_flow.py`; dự kiến `generate_corruption_report` để sinh `data/reports/corruption_report.md` |
| Điều kiện lỗi cần xử lý | Baseline artifact chưa tồn tại → raise `RuntimeError` yêu cầu chạy `run_phase1.py` trước; DataFrame rỗng → ghi log rỗng, trả nguyên bản; số dòng còn lại sau `drop_latest_records` không xuống dưới 4 |

### Cách xác minh

```bash
.venv/bin/python script/run_phase1.py
.venv/bin/python script/run_corruption_flow.py
cat data/results/corruption_log.json
cat data/quality/quality_corrupted.json data/quality/quality_repaired.json
```

- **Kết quả mong đợi:** corrupted quality FAIL (một số check fail do corruption), repaired quality PASS bằng baseline; metrics corrupted giảm, repaired quay về đúng bằng baseline.
- **Kết quả thực tế:** Đúng như mong đợi cho tới bước sinh `corruption_report.md` — bước này raise `NotImplementedError` vì `generate_corruption_report` trong `reporting.py` hiện là stub, không thuộc phạm vi commit của tôi (xem mục 6). Toàn bộ artifact JSON/CSV trước bước đó đã ghi thành công và số liệu khớp kỳ vọng.
- **Artifact/log:** `data/results/corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `data/quality/quality_corrupted.json`, `quality_repaired.json`, `freshness_corrupted.json`, `freshness_repaired.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi implement bước "repair" trong `corruption_flow.py`, cần chọn cách khôi phục dữ liệu sau corruption.
- **Các phương án đã cân nhắc:**
  - (A) Patch trực tiếp trên corrupted DataFrame — viết logic riêng để phát hiện và sửa từng loại lỗi (bù summary rỗng, khôi phục title bị cắt, loại duplicate...).
  - (B) Bỏ qua bản corrupted, rebuild hoàn toàn từ `raw_records.json` bằng chính `build_clean_dataframe` đã dùng cho baseline.
- **Phương án đã chọn:** (B) Rebuild từ raw records.
- **Lý do:** `raw_records.json` chưa từng bị `corrupt_clean_dataframe` chạm vào (corruption chỉ tác động lên bản sao của clean dataframe), nên đây là nguồn duy nhất đảm bảo khôi phục đúng 100% dữ liệu gốc — patch dữ liệu đã hỏng (phương án A) không thể "đoán lại" nội dung đã bị blank/truncate, và luôn có rủi ro thiếu sót nếu xuất hiện loại corruption mới không lường trước. Phương án B còn tái sử dụng được hàm đã test qua baseline, giảm code trùng lặp.
- **Bằng chứng quyết định phù hợp:** `repaired_metrics.json` khớp chính xác `baseline_metrics.json` (`retrieval_hit_rate=1.0`, `mean_token_f1=0.75`, `judge_accuracy=0.75`, `mean_judge_score=4` ở cả hai); `quality_repaired.json` = 9/9 PASS giống `quality_baseline.json`; `freshness_repaired.json` có `is_fresh=true`, `stale_rows=0` giống `freshness_report.json` — chứng minh repair khôi phục hoàn toàn, không lệch dù chỉ một số liệu.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Chạy `script/run_corruption_flow.py` với `GOOGLE_API_KEY` thật trong `.env`, tiến trình treo hơn 30 phút không có thêm log nào sau dòng `Loading weights: 100%`. Kiểm tra bằng `ps -p <pid> -o etime,pcpu` cho thấy `0.0% CPU`, tiến trình đang chờ I/O chứ không tính toán.
- **Lệnh hoặc bước tái hiện:** `.venv/bin/python script/run_corruption_flow.py` (đã set `GOOGLE_API_KEY` hợp lệ về format trong `.env`) → theo dõi bằng `ps` sau vài phút thấy tiến trình không tiến triển.
- **Nguyên nhân gốc:** `ChatGoogleGenerativeAI` trong `build_llm()` (`src/retrieval/llm.py`) không set `timeout`. Khi Google API trả lỗi `429 RESOURCE_EXHAUSTED` (key hết quota), client SDK tự retry với exponential backoff không giới hạn tổng thời gian; `try/except` trong `_judge_answer` (`evaluation/metrics.py`) chỉ bắt được exception cuối cùng sau khi toàn bộ chuỗi retry kết thúc, nên fallback về heuristic bị trì hoãn rất lâu thay vì kích hoạt ngay.
- **Cách xử lý:** Thêm `timeout=30.0` (giây) vào constructor `ChatGoogleGenerativeAI` trong `src/retrieval/llm.py`, giới hạn từng lần gọi request để lỗi được raise nhanh và rơi vào fallback heuristic của `_judge_answer` đúng như thiết kế ban đầu.
- **Cách xác minh sau khi sửa:** Gọi trực tiếp `build_llm(settings).invoke('Say OK')` với API key thật → raise `ChatGoogleGenerativeAIError` (`429 RESOURCE_EXHAUSTED`, tức key đã hết quota) sau **36.5 giây** thay vì treo vô hạn.
- **Điều học được:** Khi tích hợp LLM client bên thứ ba vào pipeline có bước fallback, phải luôn set `timeout` tường minh — cơ chế retry/backoff mặc định của SDK có thể "nuốt" toàn bộ thời gian chạy pipeline mà không phát sinh exception nào để `except` bắt kịp thời.

Nếu chưa xử lý xong (`generate_corruption_report`):

- **Phạm vi bị ảnh hưởng:** `corruption_flow.main()` chạy hết các bước corrupt → evaluate → repair → evaluate → quality/freshness thành công, nhưng dừng ở lệnh gọi `generate_corruption_report(...)` cuối hàm do hàm này trong `src/observability/reporting.py` hiện là stub `raise NotImplementedError`. `data/reports/corruption_report.md` không được (re)generate trong lần chạy hiện tại.
- **Những gì đã loại trừ:** Không phải lỗi ở `corrupt_clean_dataframe` hay `corruption_flow.py` orchestration — toàn bộ artifact JSON/CSV trước bước đó (corrupted/repaired metrics, quality, freshness) đều ghi đúng và số liệu khớp kỳ vọng (đối chiếu ở mục 3, 8). Traceback chỉ trỏ đúng một dòng `raise NotImplementedError` bên trong `reporting.py`, xác nhận đây là phần chưa được implement, không phải lỗi logic ở phần tôi phụ trách.
- **Bước tiếp theo:** Đồng bộ với thành viên phụ trách `reporting.py` để implement `generate_corruption_report`; sau đó chạy lại `.venv/bin/python script/run_corruption_flow.py` để có `corruption_report.md` hoàn chỉnh.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   `crossref.py` gọi Crossref REST API, parse thành `list[PaperRecord]`, lưu raw JSON vào `data/raw/`. `cleaning.py` chuẩn hoá thành `pd.DataFrame` 16 cột (bao gồm `text_for_embedding`, và `categories_joined` dùng fallback `"Uncategorized"` khi Crossref không trả `subject`). `index.py` (`LocalEmbeddingIndex.build`) đọc `text_for_embedding`, encode bằng `sentence-transformers/all-MiniLM-L6-v2`, lưu vào ChromaDB collection persist tại `data/chroma`, đồng thời ghi manifest JSON (`embeddings.json`) chứa toàn bộ documents + metadata để load lại mà không cần re-embed.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   `testset.py` chọn 4 paper đầu đủ 5 trường bắt buộc, sinh 4 loại câu hỏi/paper (summary/authors/date/categories) kèm `ground_truth` và `ground_truth_doc_ids=[paper_id]`. `evaluate_pipeline` (`metrics.py`) chạy `answer_question` cho từng câu, so `retrieved_doc_ids` với `ground_truth_doc_ids` để tính `retrieval_hit_rate`, so `answer` với `ground_truth` để tính `token_f1` và điểm judge (LLM thật hoặc fallback heuristic dựa trên `token_f1`).

3. **Quality checks khác freshness monitoring ở điểm nào?**
   `run_data_quality_checks` đo tính đúng đắn/toàn vẹn tại một thời điểm: completeness (`paper_id`/`title`/`summary` không rỗng), uniqueness (`paper_id` không trùng), validity (`title` đủ dài, `published` parse được). `build_freshness_report` đo riêng chiều "recency" — `age_days` so với `freshness_threshold_days` (180 ngày). Một dataset có thể pass hết quality checks (đúng định dạng) nhưng vẫn STALE nếu `published` quá cũ, và ngược lại — hai trục này độc lập nhau.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để so sánh công bằng (apples-to-apples). Nếu test set đổi giữa các lần chạy, chênh lệch `retrieval_hit_rate`/`token_f1` có thể do câu hỏi khác nhau chứ không phải do corruption/repair. `corruption_flow.py` cố tình tái sử dụng `paths.eval_testset` (`test_set.json`) đã ghi từ lúc chạy baseline cho cả evaluate corrupted lẫn repaired.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Dựa trên ba nhóm bằng chứng đối chiếu với baseline: (a) `quality_repaired.json` status = PASS, số check pass bằng `quality_baseline.json` (9/9); (b) `freshness_repaired.json` có `is_fresh=true`, `stale_rows=0` giống `freshness_report.json`; (c) `repaired_metrics.json` khớp chính xác `baseline_metrics.json` (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`). Trong lần chạy đã verify, cả ba nhóm đều khớp tuyệt đối — repair được xem là thành công toàn phần.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.0 | 0.5 | 1.0 | Giảm đúng 50%: 2/24 record bị `drop_latest_records` biến mất hẳn khỏi index nên bất kỳ câu hỏi nào trỏ tới chúng chắc chắn miss; các loại corruption khác (blank/noise) chỉ làm lệch embedding chứ không xoá document |
| `mean_token_f1` | 0.75 | 0.390 | 0.75 | Giảm gần một nửa, tương ứng tỉ lệ record bị corruption chạm tới (~8/24) |
| `judge_accuracy` | 0.75 | 0.375 | 0.75 | Fallback heuristic judge (không có LLM thật khả dụng — xem mục 6), tính từ ngưỡng `token_f1` |
| `mean_judge_score` | 4 | 2.5 | 4 | Rơi vào giữa thang điểm 1–5 vì chỉ ~1/3 tổng số câu hỏi (16 câu, tương ứng 4 paper) bị ảnh hưởng trực tiếp bởi corruption, không phải toàn bộ |
| Quality checks | 9/9 PASS | 5/9 PASS (FAIL: `paper_id_unique`, `title_not_truncated`, `summary_present`, `freshness_threshold`) | 9/9 PASS | Đúng 4 loại corruption có chủ đích vi phạm check (`duplicate_rows`, `truncate_title`, `blank_summary`, `stale_published_date`); `inject_noise` và `drop_latest_records` không tự vi phạm quality check nào (chỉ ảnh hưởng retrieval) |
| Freshness status | FRESH (stale=0) | STALE (stale=2, ratio 8.3%) | FRESH (stale=0) | Đúng bằng số record bị `stale_published_date` tác động (2/24) |

### Kết luận từ số liệu

1. `drop_latest_records` (loại 2 record mới nhất) + `blank_summary`/`inject_noise` (làm nhiễu 4 record khác) → `quality_corrupted.json` chuyển 9/9 → 5/9 PASS, `freshness_corrupted.json` chuyển FRESH → STALE → `retrieval_hit_rate` giảm 1.0 → 0.5, `mean_token_f1` giảm 0.75 → 0.39, `judge_accuracy` giảm 0.75 → 0.375.
2. Repair (rebuild từ `raw_records.json`) → `quality_repaired.json` quay lại 9/9 PASS, `freshness_repaired.json` quay lại FRESH → `repaired_metrics.json` phục hồi khớp 100% `baseline_metrics.json`.

Corruption nào ảnh hưởng rõ nhất và vì sao? **`drop_latest_records`** — đây là loại duy nhất khiến document biến mất hoàn toàn khỏi index thay vì chỉ suy giảm chất lượng embedding. Bất kỳ câu hỏi nào có `ground_truth_doc_ids` trỏ tới 2 `paper_id` bị drop chắc chắn miss ở `retrieval_hit_rate`, trong khi `blank_summary`/`inject_noise`/`truncate_title`/`stale_published_date`/`duplicate_rows` vẫn giữ document trong index nên chỉ làm giảm dần chất lượng chứ không gây miss tuyệt đối.

Kết quả nào khác với kỳ vọng ban đầu? Ban đầu tôi kỳ vọng `mean_judge_score` corrupted sẽ giảm gần về mức tối thiểu (1/5) tương tự mức giảm mạnh của `retrieval_hit_rate`. Thực tế điểm chỉ giảm về mức giữa thang (2.5/5) vì `_judge_answer` (fallback heuristic) tính điểm theo ngưỡng `token_f1` cho từng câu riêng lẻ (5 nếu f1≥0.95, 3 nếu f1≥0.5, 1 nếu thấp hơn) — do corruption chỉ chạm tới ~8/24 record (không phải toàn bộ 24), nên khoảng một nửa trong 16 câu hỏi vẫn trả lời đúng, kéo điểm trung bình về giữa thay vì cực trị. Tôi đã kiểm tra bằng cách đối chiếu trực tiếp `corrupted_answers.json` với `corruption_log.json` để xác nhận đúng những câu hỏi liên quan `paper_id` bị corruption mới có `token_f1` thấp.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Raw data (chưa qua transform) là nguồn duy nhất đáng tin cậy để "repair".** Patch trực tiếp trên dữ liệu đã hỏng luôn kém tin cậy hơn rebuild từ source of truth, vì không thể đoán lại nội dung đã mất (vd. summary bị blank).
2. **Quality checks và freshness monitoring là hai trục độc lập trong data observability.** Một dataset có thể pass hết quality (đúng định dạng) nhưng vẫn fail freshness (dữ liệu cũ), và ngược lại — cần theo dõi cả hai để chẩn đoán đúng loại lỗi.
3. **Không phải mọi loại corruption ảnh hưởng RAG agent như nhau.** Mất hẳn document (drop) gây miss retrieval tuyệt đối và không thể phục hồi bằng cách "sửa" — trong khi nhiễu/blank field chỉ gây suy giảm dần (degradation). Khi debug RAG kém chất lượng, cần phân biệt rõ "document biến mất khỏi index" với "document còn nhưng embedding kém".

### Nếu có thêm thời gian

Hoàn thiện `generate_corruption_report` (hiện là stub gây blocker ở mục 6) để có báo cáo markdown so sánh tự động đầy đủ giữa baseline/corrupted/repaired. Đo bằng cách chạy lại `.venv/bin/python script/run_corruption_flow.py` và kiểm tra `data/reports/corruption_report.md` được sinh ra không lỗi, đối chiếu số liệu trong report khớp với các file JSON gốc (`corrupted_metrics.json`, `repaired_metrics.json`, `quality_*.json`, `freshness_*.json`).

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Khánh Toàn
**Ngày xác nhận:** 2026-08-06
