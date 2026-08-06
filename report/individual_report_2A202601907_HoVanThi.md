# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                                                                                           |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Họ và tên       | Hồ Văn Thi                                                                                                                                        |
| MSSV               | 2A202601907                                                                                                                                          |
| Khóa/Lớp         | K3 - E403                                                                                                                                           |
| Tên nhóm         | A5-01                                                                                                                                               |
| Vai trò chính    | Data Model & Eval Set Owner                                                                                                                         |
| Repository         | [github.com/TruongIKPK/K3_Day10_Data-Pipeline-Data-Observability-A501](https://github.com/TruongIKPK/K3_Day10_Data-Pipeline-Data-Observability-A501) |
| Ngày hoàn thành | 2026-08-06                                                                                                                                          |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable        | File/hàm phụ trách                               | Input nhận vào                                    | Output bàn giao                              | Trạng thái  |
| ------------------------- | -------------------------------------------------- | -------------------------------------------------- | --------------------------------------------- | ------------ |
| Data Cleaning & Modeling  | `src/ingestion/cleaning.py` / `build_clean_dataframe` | `list[PaperRecord]` từ `crossref.py`, `run_date` | `pd.DataFrame` với schema chuẩn (Clean Schema) | Hoàn thành  |
| Evaluation Set Builder    | `src/evaluation/testset.py` / `build_test_set`    | Cleaned DataFrame                                  | `data/eval/testset.json`                      | Hoàn thành  |

Phần việc của tôi nằm ở giữa pipeline: nhận raw records từ Thành viên 1 (crossref.py), biến đổi thành cleaned dataframe theo Clean Schema chuẩn, sau đó tạo bộ câu hỏi evaluation phục vụ cho Thành viên 3 (quality.py) và Thành viên 4 (phase1.py, corruption_flow.py) sử dụng để đánh giá agent.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                          | Thành viên/module được hỗ trợ          | Kết quả                                              |
| --------------------------------------------------- | --------------------------------------- | ----------------------------------------------------- |
| Xác minh Clean Schema contract khớp với index.py  | Thành viên 4 / `phase1.py`            | Schema đã thống nhất, đủ cột cho embedding và eval   |
| Hỗ trợ debug git conflict khi push lên main        | Toàn nhóm / repository                | Hướng dẫn dùng `git pull --rebase` để tránh merge commit |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                      | File/hàm/artifact liên quan                          | Kết quả bàn giao                              | Cách xác minh                                       |
| ----------------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------- | ---------------------------------------------------- |
| Implement pipeline làm sạch raw records thành DataFrame    | `src/ingestion/cleaning.py` / `build_clean_dataframe` | DataFrame với 16 cột theo Clean Schema        | Kiểm tra cột bằng `df.columns`, kiểm tra `df.shape` |
| Normalize title, summary, authors, categories, HTML entity | `clean_text()`, `clean_list()` trong cleaning.py      | Text sạch, không HTML tag, whitespace chuẩn   | Đọc `data/clean/clean_records.csv`                   |
| Tính `age_days`, `text_for_embedding`, dedup               | `build_clean_dataframe()`                             | DataFrame đã sort, dedup theo `paper_id`       | Kiểm tra `paper_id` unique, sort theo `published`    |
| Tạo evaluation set với 4 loại câu hỏi                     | `src/evaluation/testset.py` / `build_test_set`        | `data/eval/testset.json` (16 samples)         | `type data\eval\testset.json` và kiểm tra schema   |

**Output cụ thể:** File `data/eval/testset.json` chứa **16 câu hỏi** (4 paper × 4 loại: summary, authors, date, categories), mỗi sample có đủ `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`. Ví dụ paper đầu tiên: `10.1111/exsy.70341` (Hi‐RAG framework, tác giả Wei Tian & Yuhao Zhou, published 2026-08-01). Pipeline đã clean thành công **24 records** từ Crossref API (query: *agentic retrieval augmented generation large language model*, filter: from-pub-date:2026-02-07). Đây là artifact cố định dùng chung cho cả ba trạng thái baseline, corrupted và repaired.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Raw records từ Crossref API chứa nhiễu: HTML entities (`&amp;`, `&lt;`), HTML tags (`<p>`, `<i>`), whitespace không nhất quán, ngày tháng không chuẩn định dạng, và danh sách tác giả/danh mục có thể trùng lặp hoặc rỗng. Pipeline cần biến dữ liệu thô này thành schema nhất quán, sẵn sàng để embedding và evaluation.

### Cách triển khai

**`build_clean_dataframe()`** hoạt động theo 6 bước:

1. **Normalize text** — Hàm `clean_text()` dùng `html.unescape()` để decode HTML entities, sau đó dùng regex `re.sub(r"<[^>]+>", " ", text)` để xóa HTML tags, cuối cùng `normalize_whitespace()` chuẩn hóa khoảng trắng.

2. **Normalize list fields** — Hàm `clean_list()` xử lý authors và categories: lọc item rỗng, deduplicate bằng `dict.fromkeys()` để giữ thứ tự ban đầu.

3. **Parse và validate ngày tháng** — Dùng `pd.to_datetime(errors="coerce")` để parse `published`; nếu kết quả là `NaT` thì bỏ record đó (invalid date → drop).

4. **Tính freshness** — `age_days = (run_day - parsed_published.date()).days` tính số ngày từ ngày xuất bản đến ngày chạy pipeline.

5. **Tạo `text_for_embedding`** — Ghép các trường có ngữ nghĩa cao (Title, Authors, Categories, Published, Summary) thành một đoạn text duy nhất, dùng để embedding vào ChromaDB.

6. **Dedup và sort** — `drop_duplicates(subset=["paper_id"])` loại bản ghi trùng, sort theo `published` giảm dần (paper mới nhất lên đầu) và `paper_id` tăng dần làm tiebreaker.

**`build_test_set()`** chọn 4 paper đầu tiên đủ điều kiện (không rỗng ở 5 trường cần thiết) và tạo 4 câu hỏi/paper theo template cố định, ghi ra JSON.

### Input, output và contract

| Thành phần                   | Mô tả                                                                                                                         |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| Input (cleaning)               | `list[PaperRecord]` — dataclass frozen từ `ingestion.crossref`; `run_date: datetime` — thời điểm chạy pipeline             |
| Output (cleaning)              | `pd.DataFrame` với 16 cột: `paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`, `published`, `updated`, `abs_url`, `pdf_url`, `comment`, `authors_joined`, `categories_joined`, `summary_chars`, `age_days`, `text_for_embedding` |
| Input (testset)                | Cleaned DataFrame (output của cleaning); `output_path: Path` — nơi ghi JSON                                                  |
| Output (testset)               | `list[dict]` và file `data/eval/testset.json` với schema: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` |
| Module phụ thuộc             | `ingestion.crossref` (PaperRecord), `core.utils` (compact_join, normalize_whitespace, first_sentence, write_json)            |
| Module sử dụng output        | `retrieval/index.py` (dùng `text_for_embedding`), `evaluation/metrics.py` (dùng testset.json), `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Record thiếu `paper_id`/`title`/`summary`/`published` → skip; `published` không parse được → skip; DataFrame thiếu < 4 candidate → raise ValueError |

### Cách xác minh

```powershell
# Chạy baseline pipeline đầy đủ
uv run python script/run_phase1.py

# Đọc metrics kết quả
type data\results\baseline_metrics.json

# Đọc phase1 report
type data\reports\phase1_report.md
```

- **Kết quả mong đợi:** 24 records fetched, 24 clean rows, testset 16 samples, tất cả quality checks PASS, freshness FRESH.
- **Kết quả thực tế:** Đúng như mong đợi — `data/results/baseline_metrics.json` ghi nhận `retrieval_hit_rate: 1.0`, `mean_token_f1: 1.0`, `judge_accuracy: 1.0`, `mean_judge_score: 5`. Phase1 report xác nhận tất cả 9 quality checks PASS và freshness FRESH (latest paper: 2026-08-01, threshold: 180 days, stale rows: 0).
- **Artifact/log:** `data/clean/clean_records.csv`, `data/eval/testset.json`, `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi tạo `text_for_embedding`, cần quyết định nên ghép những trường nào và theo thứ tự nào để embedding có chất lượng tốt nhất cho RAG.
- **Các phương án đã cân nhắc:**
  - (A) Chỉ dùng `summary` — đơn giản nhưng mất thông tin tác giả và danh mục.
  - (B) Ghép tất cả 16 trường — quá dài, gây noise cho embedding model.
  - (C) Ghép có chọn lọc: Title, Authors, Categories, Published, Summary theo thứ tự có ngữ nghĩa.
- **Phương án đã chọn:** Phương án C.
- **Lý do:** Embedding model `all-MiniLM-L6-v2` hoạt động tốt nhất với văn bản có cấu trúc và độ dài vừa phải. Thêm Authors và Categories giúp model phân biệt paper theo chủ đề và tác giả. Title đặt đầu vì mang nhiều thông tin nhận dạng nhất. Published giúp trả lời câu hỏi về ngày tháng.
- **Bằng chứng quyết định phù hợp:** Evaluation set có cả 4 loại câu hỏi (summary, authors, date, categories) — nếu thiếu trường trong `text_for_embedding` thì `retrieval_hit_rate` cho loại câu hỏi đó sẽ giảm rõ rệt.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```
  ! [rejected] main -> main (fetch first)
  error: failed to push some refs to 'github.com:TruongIKPK/...'
  hint: Updates were rejected because the remote contains work that you do not have locally.
  ```
- **Lệnh hoặc bước tái hiện:** Chạy `git push origin main` sau khi commit mà không pull trước.
- **Nguyên nhân gốc:** Thành viên khác đã push commit mới lên `main` trong khoảng thời gian giữa lần pull cuối và lần push của tôi. Git từ chối push vì lịch sử local không phải fast-forward của remote.
- **Cách xử lý:** Chạy `git pull origin main --rebase` để đặt commit của mình lên trên commit mới nhất của remote, sau đó `git push origin main`.
- **Cách xác minh sau khi sửa:** `git log --oneline -5` cho thấy commit của tôi nằm trên cùng, `git push` thành công với `main -> main`.
- **Điều học được:** Trong môi trường làm việc nhóm với shared branch, luôn cần `git pull --rebase` trước khi push để tránh reject. Dùng `--rebase` thay vì merge thông thường giúp lịch sử commit tuyến tính và dễ đọc hơn.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Crossref API trả về JSON chứa metadata paper. `crossref.py` parse thành `list[PaperRecord]` và lưu vào `data/raw/`. `cleaning.py` nhận list này, normalize text, loại record không hợp lệ, tính `age_days` và tạo `text_for_embedding`, xuất ra DataFrame rồi lưu CSV vào `data/clean/`. `index.py` đọc DataFrame, dùng model `all-MiniLM-L6-v2` để embed cột `text_for_embedding`, lưu vector vào ChromaDB collection ở `data/embeddings/`.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   `testset.json` chứa câu hỏi và `ground_truth_doc_ids` là `paper_id` của paper tương ứng. Khi evaluate, agent nhận câu hỏi → retrieval trả về top-k documents → kiểm tra xem `ground_truth_doc_ids` có trong kết quả trả về không (`retrieval_hit_rate`). LLM judge so sánh câu trả lời của agent với `ground_truth` để tính `token_f1` và `judge_accuracy`.

3. **Quality checks khác freshness monitoring ở điểm nào?**
   Quality checks (trong `quality.py`) kiểm tra tính toàn vẹn và nhất quán của dữ liệu: completeness (không null), validity (định dạng đúng), uniqueness (không trùng). Freshness monitoring theo dõi chiều thời gian: `age_days` của các record, xem dataset có đủ paper mới không theo ngưỡng định sẵn. Quality check là điều kiện đủ để dữ liệu "đúng"; freshness là điều kiện để dữ liệu "còn có giá trị".

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để so sánh công bằng. Nếu test set thay đổi, không thể biết sự thay đổi của metric đến từ chất lượng dữ liệu hay từ sự khác biệt của câu hỏi. Dùng cùng `testset.json` đảm bảo mọi thay đổi metric phản ánh đúng tác động của corruption/repair lên dữ liệu và index.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repair thành công khi: (a) `data/quality/` cho thấy quality checks trở về Pass như baseline; (b) freshness status trở về Fresh; (c) `retrieval_hit_rate` và `mean_token_f1` trong `data/results/repaired_metrics.json` phục hồi về gần với `baseline_metrics.json`. Nếu cả ba đều khớp, repair được xem là thành công toàn phần.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                              |
| ---------------------- | -------: | --------: | -------: | ---------------------------------------------------------------------------------- |
| `retrieval_hit_rate` |      1.0 |       0.5 |      1.0 | Corruption làm giảm 50% hit rate; repair phục hồi lại hoàn toàn (1.0).           |
| `mean_token_f1`      |     0.75 |    0.3902 |     0.75 | Giảm mạnh do không lấy đúng context, phục hồi 100% về mức baseline (0.75) sau repair. |
| `judge_accuracy`     |     0.75 |     0.375 |     0.75 | Tương quan trực tiếp với hit rate — sai context dẫn đến LLM trả lời sai.         |
| `mean_judge_score`   |        4 |       2.5 |        4 | Điểm giảm 1.5 khi corrupted, trở lại mức baseline (4) sau repair.                  |
| Quality checks         |  9/9 PASS |  5/9 PASS |  9/9 PASS | Corrupted fail 4 lỗi (paper_id_unique, title, summary, freshness); repair sửa hết.|
| Freshness status       |    FRESH |   STALE  |    FRESH | Dữ liệu cũ bị phát hiện STALE, sau khi repair đã lấy lại data mới.               |

> **Về LLM judge:** `baseline_answers.json` ghi `"reasoning": "Fallback heuristic judge used because the LLM evaluator was unavailable."` — đây là do không có API key LLM judge được cấu hình. Score phản ánh độ chính xác của heuristic (exact match / token overlap), không phải LLM evaluation thực sự.

### Kết luận từ số liệu

1. [Baseline sạch với 24 records đủ schema] → [9/9 quality checks PASS, freshness FRESH] → [retrieval_hit_rate = 1.0] — xác nhận pipeline cleaning và testset builder của tôi tạo ra foundation chất lượng tốt.
2. [Corruption tạo lỗi trên summary, title, id, date] → [Quality/Freshness báo FAIL/STALE, Retrieval giảm xuống 0.5, Accuracy giảm còn 0.375].
3. [Repair từ raw source] → [quality/freshness signal phục hồi 9/9 PASS và FRESH] → [tất cả metrics của agent phục hồi 100% về baseline].

Corruption nào ảnh hưởng rõ nhất: **Blank summary** (hoặc hỏng summary) — vì `text_for_embedding` phụ thuộc nhiều vào summary (chiếm phần lớn nội dung), khi bị blank thì vector embedding trở nên giống nhau và retrieval không phân biệt được paper đúng, dẫn đến hit rate rớt thảm hại (còn 0.5).

Kết quả khác với kỳ vọng ban đầu: Tất cả 24 records từ Crossref đều không có `categories` (Crossref không expose subject categories như arXiv), nên toàn bộ dùng fallback `"Uncategorized"`. Điều này chứng minh fallback category trong `cleaning.py` là thiết yếu — nếu không có, `categories_joined` sẽ rỗng và `testset.py` lọc ra mọi paper, gây ValueError.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline phải có schema contract rõ ràng ngay từ đầu.** Khi cleaning.py và index.py được viết bởi hai người khác nhau, nếu không thống nhất tên cột trước (ví dụ `authors_joined` vs `authors`), integration sẽ fail. Data contract là công cụ giao tiếp quan trọng nhất trong team.

2. **Cleaning không chỉ là "xóa null" — còn là chuẩn hóa để downstream có thể tin tưởng dữ liệu.** HTML entities, encoding sai, whitespace thừa đều có thể làm embedding model tạo ra vector sai, dẫn đến retrieval kém chất lượng mà không có error message rõ ràng.

3. **Evaluation set phải bất biến (frozen) khi so sánh baseline vs corrupted vs repaired.** Nếu test set thay đổi giữa các lần chạy, không thể kết luận gì về tác động của corruption. `write_json` ghi một lần và không overwrite là quyết định đúng.

### Nếu có thêm thời gian

Cải thiện `build_test_set()` để tạo câu hỏi đa dạng hơn: hiện tại template câu hỏi cố định (`"What is the summary of..."`). Có thể dùng LLM để sinh câu hỏi tự nhiên hơn từ nội dung paper, sau đó đo xem `retrieval_hit_rate` thay đổi ra sao khi câu hỏi phức tạp hơn. Đo bằng cách so sánh hit rate giữa template-based questions và LLM-generated questions trên cùng ground truth.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hồ Văn Thi
**Ngày xác nhận:** 2026-08-06
