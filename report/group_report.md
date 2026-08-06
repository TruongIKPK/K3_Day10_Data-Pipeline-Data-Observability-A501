# Group Report — Day 10: Data Pipeline & Data Observability

> Dùng mẫu này cho báo cáo chung của nhóm 3–5 thành viên. Thay toàn bộ nội dung trong dấu `[ ]` bằng thông tin và kết quả thực tế. Xóa các dòng hướng dẫn không còn cần thiết trước khi nộp.

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                                                                                                                                           |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Khóa/Lớp         | K3 - E403                                                                                                                                           |
| Tên nhóm         | A5-01                                                                                                                                               |
| Repository         | [github.com/TruongIKPK/K3_Day10_Data-Pipeline-Data-Observability-A501](https://github.com/TruongIKPK/K3_Day10_Data-Pipeline-Data-Observability-A501) |
| Ngày hoàn thành | 2026-08-06                                                                                                                                          |

### Thành viên và phân công

| STT | Họ và tên             | MSSV        | Vai trò chính                | Module/deliverable sở hữu                              |
| --: | ------------------------ | ----------- | ------------------------------ | -------------------------------------------------------- |
|   1 | Lê Nguyễn Phi Trường | 2A202601541 | Source Ingestion Owne          | `crossref.py`                                          |
|   2 | Trần Duy Trường       | 2A202601247 | Data Observability Owne        | `quality.py`, `reporting.py`                         |
|   3 | Nguyễn Khánh Toàn     | 2A202601843 | Corruption & Integration Owner | `corruption.py`, `phase1.py`, `corruption_flow.py` |
|   4 | Hồ Văn Thi             | 2A202601907 | Data Model & Eval Set Owne     | `cleaning.py`, `testset.py`                          |                          |

## 2. Tóm tắt kết quả

Viết từ 150–250 từ, trả lời ngắn gọn:

- Nhóm đã hoàn thành những phần nào?
- Baseline pipeline đã tạo ra các artifact nào?
- Corruption nào ảnh hưởng rõ nhất đến data quality hoặc agent?
- Repair đã phục hồi được chỉ số nào?
- Blocker hoặc giới hạn quan trọng nhất còn lại là gì?

**Tóm tắt của nhóm:**

- Nhóm đã hoàn thành toàn bộ pipeline từ thu thập dữ liệu (Crossref), làm sạch, tạo vector embedding, đến đánh giá agent (RAG). Nhóm cũng đã hoàn thành kịch bản mô phỏng corruption và repair.
- Baseline pipeline tạo ra các artifact: raw records, clean dataset (24 records), embedding index, testset (16 câu hỏi), và các báo cáo quality/freshness/baseline metrics.
- Blank summary và missing title là các corruption ảnh hưởng rõ nhất đến retrieval hit rate và data quality, khiến hit rate giảm mạnh từ 1.0 xuống 0.5.
- Đoạn mã repair đã phục hồi thành công dữ liệu từ nguồn gốc, giúp tất cả các chỉ số (quality, freshness, hit rate, f1, accuracy) phục hồi 100% về mức baseline.
- Giới hạn hiện tại là chưa dùng LLM evaluator (phải dùng fallback heuristic) do thiếu cấu hình API, và chưa có bộ test set sinh tự động đa dạng hơn.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

Điều chỉnh sơ đồ dưới đây nếu cách triển khai thực tế của nhóm khác starter:

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref API | Fetch JSON, parse thành PaperRecord   | data/raw/ | Lê Nguyễn Phi Trường |
| Cleaning          | list[PaperRecord]        | Unescape HTML, bỏ tags, parse date, tính age_days     | data/clean/ | Hồ Văn Thi |
| Embedding/index   | pd.DataFrame        | all-MiniLM-L6-v2, ChromaDB       | data/embeddings/ | Hồ Văn Thi |
| Evaluation        | ChromaDB index, testset.json        | 16 câu hỏi, hit rate, f1, accuracy     | data/results/baseline_metrics.json | Trần Duy Trường |
| Observability     | DataFrame        | 9 checks, threshold 180 days | data/quality/ | Trần Duy Trường |
| Corruption/repair | DataFrames        | Làm hỏng và sửa data    | data/reports/ | Nguyễn Khánh Toàn |
| Orchestration     | Các module        | run_phase1, run_corruption_flow           | Toàn bộ artifacts        | Nguyễn Khánh Toàn |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | N/A         |
| `LLM_MODEL`                | N/A         |
| Embedding model              | all-MiniLM-L6-v2         |
| Số lượng Crossref records | 24         |
| Retrieval`top_k`           | 3         |
| Freshness threshold          | 180         |
| Random seed, nếu có        | 42         |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

Chỉ giữ lại cách nhóm đã dùng.

```bash
uv sync
```

Hoặc:

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06                  | data/results/baseline_metrics.json |
| Corruption flow   | Thành công | 2026-08-06                  | data/results/baseline_metrics.json |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | https://api.crossref.org/works |
| Query/filter                | agentic retrieval augmented generation large language model, from-pub-date:2026-02-07,has-abstract:true                  |
| Thời điểm lấy dữ liệu | 2026-08-06                           |
| Số record nhận được    | 24                         |
| Cơ chế retry/backoff      | Sử dụng urllib/requests mặc định                       |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| paper_id | str | Có | ID duy nhất | Skip |
| title | str | Có | Tiêu đề | Skip |
| summary | str | Có | Tóm tắt | Skip |
| published | datetime | Có | Ngày xuất bản | Skip |
| authors_joined | str | Không | Tác giả ghép chuỗi | Để rỗng |
| text_for_embedding | str | Có | Chuỗi dùng để nhúng | Bắt buộc |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Bỏ HTML tags | Validity | 24 | Đọc file CSV |
| Parse chuỗi ngày tháng thành datetime | Validity | 24 | df.dtypes |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

`text_for_embedding` được tạo bằng cách ghép: Title, Authors, Categories, Published, Summary. `age_days` tính bằng (run_date - published.date()).days. Document ID là `paper_id`.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 16                 |
| Các`question_type`                    | summary, authors, date, categories                  |
| Ground-truth document ID                 | paper_id     |
| Embedding model                          | all-MiniLM-L6-v2                  |
| Vector store/collection                  | ChromaDB                 |
| Retrieval`top_k`                       | 3                   |
| LLM provider/model                       | N/A (Fallback heuristic)                   |
| Test set dùng chung cho ba trạng thái | data/eval/testset.json |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Dùng chung một bộ test set đảm bảo mọi sự thay đổi trong metrics đều phản ánh chính xác sự khác biệt do dữ liệu bị hỏng hoặc đã sửa, chứ không phải do câu hỏi khác nhau.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | OK |
| Cleaned dataset          | `data/clean/`                        | Có | OK |
| Embedding manifest/index | `data/embeddings/`                   | Có | OK |
| Evaluation set           | `data/eval/`                         | Có | OK |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | OK |
| Quality/freshness        | `data/quality/`                      | Có | OK |
| Baseline report          | `data/reports/phase1_report.md`      | Có | OK |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.0 | Agent luôn lấy đúng tài liệu top 1  |
| `mean_token_f1`      |     0.75 | Khớp từ vựng tốt                           |
| `judge_accuracy`     |     0.75 | Trả lời đúng 12/16 câu                           |
| `mean_judge_score`   |     4 | Score trung bình                           |
| Ragas, nếu có        | N/A | Không cấu hình API key |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| completeness | completeness | 24 | PASS (24) | phase1_report.md |
| paper_id_unique | uniqueness | 0 | PASS (0) | phase1_report.md |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | data/clean/clean_records.csv            |
| Timestamp mới nhất       | 2026-08-01                         |
| Ngưỡng freshness         | 180                         |
| Trạng thái baseline      | FRESH               |
| Lý do                     | Có bài báo xuất bản gần đây (vài ngày trước) |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| Blank Summary | Xóa cột summary | 12 | FAIL summary_present | Hit rate giảm mạnh | Lấy lại từ raw data |
| Truncate Title | Cắt ngắn title | 8 | FAIL title_not_truncated | Hit rate giảm | Lấy lại từ raw data |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log có ghi lại quá trình làm hỏng.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Repair thực hiện một phép JOIN (hoặc merge) bằng paper_id với bảng raw/clean ban đầu, nhờ đó lấy lại nguyên vẹn nội dung đúng từ API chứ không phải đoán hay sinh ngẫu nhiên.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |      1.0 |       0.5 |      1.0 |                      -0.5 |             +0.5 | Phục hồi hoàn toàn |
| `mean_token_f1`        |      0.75|       0.3902|     0.75 |                      -0.3598|            +0.3598| Phục hồi hoàn toàn |
| `judge_accuracy`       |      0.75|       0.375 |     0.75 |                      -0.375 |            +0.375 | Phục hồi hoàn toàn |
| `mean_judge_score`     |        4 |       2.5 |        4 |                      -1.5 |             +1.5 | Phục hồi hoàn toàn |
| Quality checks pass/fail | 9/9 PASS| 5/9 FAIL  | 9/9 PASS |                      -4 |               +4 | Phục hồi hoàn toàn |
| Freshness status         |    FRESH |   STALE  |    FRESH |                      - |             - | Phục hồi hoàn toàn |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. Corruption làm hỏng cột summary → Quality signal báo FAIL (summary_present) → Retrieval hit rate giảm do thiếu ngữ nghĩa để match.
2. Repair merge lại dữ liệu từ raw → Quality/freshness recovery (9/9 PASS) → Agent metric recovery (hit rate phục hồi về 1.0).

Không kết luận corruption “có tác động” nếu số liệu không cho thấy thay đổi. Nếu kết quả khác kỳ vọng, mô tả giả thuyết và cách nhóm đã kiểm tra.

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** Clean Schema không khớp giữa cleaning.py và phase1.py
- **Nguyên nhân:** Thiếu cột categories_joined
- **Cách xử lý:** Thống nhất lại tên cột và tạo fallback value cho categories
- **Cách xác minh:** Chạy lại script/run_phase1.py thành công

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Chưa có LLM Judge thực sự | Phải dùng fallback heuristic (exact match) | Cấu hình API key cho Ragas/LLM |
| Testset còn cố định | Đánh giá chưa phủ hết edge cases | Dùng LLM tự sinh câu hỏi đa dạng hơn |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
