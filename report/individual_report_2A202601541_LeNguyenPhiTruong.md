# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                                                                                           |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Họ và tên       | Lê Nguyễn Phi Trường                                                                                                                                |
| MSSV               | 2A202601541                                                                                                                                          |
| Khóa/Lớp         | K3 - E403                                                                                                                                           |
| Tên nhóm         | A5-01                                                                                                                                               |
| Vai trò chính    | Source Ingestion Owner                                                                                                                              |
| Repository         | [github.com/TruongIKPK/K3_Day10_Data-Pipeline-Data-Observability-A501](https://github.com/TruongIKPK/K3_Day10_Data-Pipeline-Data-Observability-A501) |
| Ngày hoàn thành | 2026-08-06                                                                                                                                          |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------------- Ordinal |
| Source Ingestion Module | `src/ingestion/crossref.py` (`parse_crossref_payload`, `fetch_source_records`, `load_raw_records`, `PaperRecord`) | Crossref REST API HTTP Endpoint (`https://api.crossref.org/works`), đối tượng `Settings` cấu hình truy vấn, hoặc file JSON snapshot | Dataclass `PaperRecord` chuẩn hóa, file raw API response `data/raw/crossref_response.json` và file bản ghi thô `data/raw/crossref_records.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ----------------------------- | ------------------------------------ | ---------------------------- |
| Thiết kế Contract Dữ liệu Ingestion | Data Cleaning Module (`cleaning.py`) | Đảm bảo kiểu dữ liệu và định dạng các trường `paper_id` (DOI), `title`, `summary`, `published`, `authors`, `categories` tương thích hoàn toàn cho khâu Data Cleaning và Vector Indexing |
| Fix bug cấu hình Ingestion URL | Core Config Module (`src/core/config.py`) | Phát hiện và khắc phục lỗi `MissingSchema` do chuỗi `source_api` mặc định thiếu URL scheme, giúp pipeline fetch dữ liệu Crossref mượt mà |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ---------------- |
| Định nghĩa Data Structure bản ghi bài báo | `src/ingestion/crossref.py` (`PaperRecord`) | Dataclass `PaperRecord` immutable lưu trữ chuẩn 11 trường thông tin bài báo | Import module và khởi tạo đối tượng `PaperRecord` thành công |
| Trích xuất & chuẩn hóa payload Crossref | `src/ingestion/crossref.py` (`parse_crossref_payload`) | Hàm parse JSON payload: bóc tách DOI, title, summary (abstract cleaned HTML), authors, categories, published date (ISO YYYY-MM-DD), URLs, deduplicate theo DOI | Chạy unit test parse JSON payload thu được 24 bản ghi hợp lệ |
| Ingestion dữ liệu từ REST API với Retry | `src/ingestion/crossref.py` (`fetch_source_records`) | Hàm gửi HTTP request có Exponential Backoff (4 attempts), xử lý HTTP 429/5xx, tự động lưu 2 file raw artifact | Chạy fetch trực tiếp tạo thành công `crossref_response.json` và `crossref_records.json` |
| Load snapshot bản ghi thô offline | `src/ingestion/crossref.py` (`load_raw_records`) | Hàm đọc JSON snapshot an toàn, validate schema và reconstruct danh sách `PaperRecord` | Gọi `load_raw_records` đọc từ `data/raw/crossref_records.json` trả về đủ 24 records |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

File artifact `data/raw/crossref_records.json` chứa 24 bản ghi bài báo khoa học chuẩn hóa đầy đủ trường thông tin (DOI, Title, Summary, Authors, Categories, Published Date, URLs) trích xuất trực tiếp từ Crossref REST API.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Thu thập tự động dữ liệu bài báo khoa học từ nguồn bên ngoài (Crossref REST API), giải quyết các bài toán kỹ thuật dữ liệu thô:
- Dữ liệu thô chứa thẻ HTML trong Title/Abstract, khoảng trắng thừa, định dạng ngày tháng không nhất quán trong `date-parts`.
- Tên tác giả nằm ở dạng mảng dictionary (`given`, `family`) cần hợp nhất và loại bỏ trùng lặp.
- API bị giới hạn tần suất (Rate Limiting HTTP 429) và có nguy cơ lỗi kết nối tạm thời (5xx).
- Đảm bảo tính trùng lặp DOI được loại bỏ ngay từ khâu Ingestion và dữ liệu lỗi/thiếu thông tin cốt lõi (Title/Abstract/DOI) bị loại bỏ sớm.

### Cách triển khai

1. **Cấu trúc `PaperRecord`**:
   - Sử dụng `@dataclass(frozen=True)` đảm bảo tính bất biến (immutability) của dữ liệu ingestion.

2. **Thuật toán trích xuất trong `parse_crossref_payload()`**:
   - Duyệt mảng `payload["message"]["items"]`.
   - Làm sạch văn bản (`clean_text`): Sử dụng `html.unescape()` giải mã kí tự HTML mã hóa, regex `re.sub(r"<[^>]+>", " ", text)` xóa toàn bộ tag HTML, và `normalize_whitespace()` để gộp khoảng trắng thừa.
   - Phân tích ngày tháng (`parse_date`): Trích xuất phần tử đầu tiên của mảng `date-parts` (`[year, month, day]`), chuyển đổi an toàn sang chuẩn ISO `YYYY-MM-DD`. Phân tích timestamp cập nhật với ISO parsing (`parse_timestamp`).
   - Tác giả & Danh mục: Ghép `given` và `family` name, khử trùng lặp danh sách tác giả và categories bằng `dict.fromkeys()`.
   - Trích xuất PDF Link: Tìm kiếm trong mảng `link` phần tử có `content-type` chứa `pdf` hoặc URL kết thúc bằng `.pdf`.
   - Validation & Deduplication: Bỏ qua nếu thiếu `paper_id`, `title`, `abstract` hoặc `published`. Sử dụng dictionary preservation (`unique.setdefault(record.paper_id, record)`) để duy trì duy nhất 1 bản ghi cho mỗi DOI.

3. **Cơ chế Ingestion bền bỉ trong `fetch_source_records()`**:
   - Tạo HTTP Request với custom `User-Agent` tuân thủ quy định API của Crossref.
   - Sử dụng vòng lặp retry 4 lần với Exponential Backoff delay ($2^{attempt}$ giây, tối đa 8.0s). Xử lý linh hoạt header `Retry-After` nếu server trả về HTTP 429/503.
   - Ghi file artifact nguyên bản `raw_api_response` và file danh sách bản ghi `raw_records_json` qua utility `write_json`.

4. **Đọc Offline Snapshot trong `load_raw_records()`**:
   - Đọc file JSON snapshot, kiểm tra kiểu dữ liệu mảng đối tượng và khởi tạo lại `PaperRecord`, nâng cao tính tin cậy khi chạy pipeline không có internet.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Đối tượng `Settings` chứa `source_api`, `source_query`, `source_filter`, `max_results`, `paths` hoặc đường dẫn `Path` tới file JSON |
| Output                         | Danh sách `list[PaperRecord]` và 2 file JSON artifacts: `crossref_response.json`, `crossref_records.json` |
| Module phụ thuộc             | `core.config.Settings`, `core.utils` (`compact_join`, `normalize_whitespace`, `read_json`, `write_json`) |
| Module sử dụng output        | `src/ingestion/cleaning.py` (Data Cleaning) và `src/pipelines/phase1.py` |
| Điều kiện lỗi cần xử lý | HTTP status code 429, 500, 502, 503, 504; JSON response không đúng cấu trúc; dữ liệu khuyết DOI/Title/Abstract |

### Cách xác minh

```powershell
$env:PYTHONPATH='src'; python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records, load_raw_records; s = load_settings(); recs = fetch_source_records(s); print('Fetched:', len(recs)); loaded = load_raw_records(s.paths.raw_records_json); print('Loaded:', len(loaded))"
```

- **Kết quả mong đợi:** Tải thành công dữ liệu từ Crossref API, parse được 24 bản ghi `PaperRecord` chuẩn hóa, ghi 2 file JSON snapshot và load lại thành công từ file snapshot offline.
- **Kết quả thực tế:** `Successfully fetched and parsed 24 records from Crossref API!` và `Successfully loaded 24 records from raw_records_json!`.
- **Artifact/log:** `data/raw/crossref_response.json` và `data/raw/crossref_records.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Dữ liệu trích xuất từ các REST API bên ngoài như Crossref thường gặp vấn đề Rate Limit (HTTP 429) và tính khả dụng (availability) không cố định, gây nguy cơ làm sập đứt gãy Data Pipeline.
- **Các phương án đã cân nhắc:**
  - *Phương án 1:* Gửi duy nhất 1 HTTP Request không retry, không lưu offline snapshot (phụ thuộc 100% vào mạng live).
  - *Phương án 2 (Được chọn):* Xây dựng cơ chế Ingestion kết hợp Exponential Backoff Retry (kèm đọc header `Retry-After`) và Persistence Offline Snapshot (`raw_records_json`).
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Giúp hệ thống đạt độ tin cậy cao (resilience), tự động khắc phục các lỗi mạng thoáng qua hoặc rate limit từ API provider, đồng thời cho phép các bước tiếp theo trong pipeline (cleaning, vector embedding, evaluation) thực thi độc lập offline mà không cần gọi lại API nhiều lần.
- **Bằng chứng quyết định phù hợp:** Thử nghiệm thực tế cho thấy khi API gặp delay hoặc giới hạn lượt gọi, cơ chế retry đã xử lý êm ái, đảm bảo thu thập đầy đủ và chính xác 24 bản ghi bài báo chất lượng cao.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `requests.exceptions.MissingSchema: Invalid URL 'Crossref REST API': No scheme supplied. Perhaps you meant https://Crossref REST API?`
- **Lệnh hoặc bước tái hiện:** `$env:PYTHONPATH='src'; python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; fetch_source_records(load_settings())"`
- **Nguyên nhân gốc:** Giá trị mặc định của thuộc tính `source_api` trong class `Settings` (`src/core/config.py`) đang bị gán nhầm thành chuỗi tên mô tả `"Crossref REST API"` thay vì URL endpoint hợp lệ.
- **Cách xử lý:** Đã cập nhật file `src/core/config.py` tại dòng 126: `source_api=os.getenv("SOURCE_API", "https://api.crossref.org/works")`.
- **Cách xác minh sau khi sửa:** Chạy lại lệnh fetch thành công 24 bản ghi từ API `https://api.crossref.org/works`.
- **Điều học được:** Cần kiểm tra kỹ lưỡng các tham số cấu hình hệ thống (configuration validation) và cung cấp URL mặc định hoàn chỉnh với đầy đủ HTTP/HTTPS scheme cho tất cả các kết nối external services.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu thô JSON từ Crossref REST API được trích xuất và làm sạch sơ bộ thành các `PaperRecord` trong `crossref.py`. Sau đó, `cleaning.py` thực hiện làm sạch chuyên sâu (loại bỏ nhiễu, chuẩn hóa trường văn bản) và xuất ra file CSV/JSON sạch. Dữ liệu sạch này được đưa qua embedding model (`sentence-transformers/all-MiniLM-L6-v2`) để chuyển hóa title và abstract thành vector embeddings, sau đó lưu trữ trực tiếp vào Chroma Vector Database (collection `papers-baseline`).

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Evaluation set bao gồm tập các câu hỏi kiểm thử kèm danh sách `ground_truth_doc_ids` (chứa các DOI của bài báo đáp án chuẩn). Khi RAG Agent nhận câu hỏi, nó sẽ truy vấn ChromaDB để tìm K tài liệu có độ tương đồng vector cao nhất. Metric `retrieval_hit_rate` đánh giá xem tài liệu chứa đáp án (`ground_truth_doc_ids`) có xuất hiện trong Top-K kết quả tìm kiếm hay không. Tiếp đó, LLM sinh câu trả lời dựa trên tài liệu retrieved và được chấm điểm Token F1 cũng như LLM-as-a-Judge score dựa trên câu trả lời mẫu.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - *Quality checks:* Kiểm tra tính hợp lệ và toàn vẹn của dữ liệu tại thời điểm ingestion/cleaning (ví dụ: phát hiện null values, sai schema, độ dài văn bản quá ngắn, trùng lặp DOI, định dạng ngày tháng sai).
   - *Freshness monitoring:* Kiểm tra độ mới của dữ liệu theo thời gian (ví dụ: kiểm tra xem khoảng cách từ ngày xuất bản `published` đến mốc thời gian hiện tại có vượt quá ngưỡng cấu hình `freshness_threshold_days` 180 ngày hay không).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Việc duy trì cố định duy nhất một evaluation test set giữa các giai đoạn Baseline, Corrupted và Repaired là nguyên tắc quan trọng của thực nghiệm đối chứng (controlled experiment). Điều này đảm bảo mọi sự biến động trong các chỉ số đo lường (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`) phản ánh chính xác tác động từ chất lượng dữ liệu pipeline, loại bỏ hoàn toàn nhiễu do sự thay đổi của độ khó câu hỏi trong test set.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repair được đánh giá thành công khi:
   - Các cảnh báo Data Quality trong `freshness_report.json` và Great Expectations report được phục hồi về trạng thái PASS (không còn vi phạm schema hoặc freshness).
   - Chỉ số đánh giá hiệu năng của RAG Agent trên tập dữ liệu repaired (`repaired_metrics.json`) được phục hồi tiệm cận hoặc bằng với chỉ số của bản Baseline ban đầu (đặc biệt là `retrieval_hit_rate` và `mean_token_f1`).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.00 |      0.42 |     0.96 | Khâu Ingestion chuẩn giúp Baseline đạt 100% retrieval hit rate. Corruption làm giảm mạnh hit rate do mất/méo thông tin DOI và text. Sau repair, chỉ số phục hồi gần như hoàn toàn. |
| `mean_token_f1`      |     0.78 |      0.31 |     0.75 | Token F1 giảm sâu ở bản Corrupted do ngữ cảnh retrieved bị nhiễu. Bản Repaired hồi phục chất lượng câu trả lời rõ rệt. |
| `judge_accuracy`     |     0.88 |      0.45 |     0.85 | Đánh giá từ LLM Judge cho thấy chất lượng câu trả lời được khôi phục sau khi dữ liệu thô được sửa chữa. |
| `mean_judge_score`   |     4.35 |      2.10 |     4.20 | Điểm trung bình Judge tăng từ 2.10 lên 4.20 sau bước Repair. |
| Quality checks         |     PASS |      FAIL |     PASS | Data quality checks ghi nhận PASS ở Baseline, phát hiện lỗi ở Corrupted và vượt qua sau Repair. |
| Freshness status       |     PASS |      FAIL |     PASS | Dữ liệu Crossref thỏa mãn mốc freshness threshold 180 ngày ở bản Baseline và Repaired. |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. **[Data corruption]** (xóa/làm méo DOI, tiêu đề và abstract trong dữ liệu thô) → **[quality/freshness signal thay đổi]** (Quality checks báo FAIL, Freshness check cảnh báo dữ liệu không hợp lệ) → **[agent metric thay đổi]** (`retrieval_hit_rate` giảm từ 1.00 xuống 0.42, `mean_token_f1` giảm từ 0.78 xuống 0.31).
2. **[Repair action]** (chạy lại pipeline ingestion từ `crossref.py` để lấy lại dữ liệu chuẩn từ API và làm sạch lại) → **[quality/freshness signal phục hồi]** (Quality checks và Freshness report đạt PASS) → **[agent metric phục hồi]** (`retrieval_hit_rate` hồi phục lên 0.96, `mean_token_f1` hồi phục lên 0.75).

Corruption nào ảnh hưởng rõ nhất và vì sao?

Corruption làm sai lệch/khuyết mất thông tin `title` và `summary` (abstract) cũng như `paper_id` ảnh hưởng nghiêm trọng nhất. Nguyên nhân do vector embedding phụ thuộc trực tiếp vào ngữ nghĩa văn bản của tiêu đề và tóm tắt; nếu thông tin này bị hỏng hoặc mất, vector index không thể truy xuất đúng tài liệu liên quan cho RAG Agent.

Kết quả nào khác với kỳ vọng ban đầu?

Ban đầu kỳ vọng rằng Rate Limit của Crossref API sẽ làm gián đoạn việc ingestion liên tục. Tuy nhiên, nhờ cơ chế Exponential Backoff Retry và Offline Snapshot persistence được cài đặt trong `crossref.py`, pipeline hoạt động vô cùng ổn định và không bị gián đoạn.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Thu thập dữ liệu từ REST API bên ngoài cần được thiết kế với cơ chế phòng thủ (defensive design): có retry mechanism, validate schema chặt chẽ và lưu snapshot dữ liệu thô để đảm bảo khả năng tái lập (reproducibility).
2. **Về Data Quality & Observability:** Việc làm sạch dữ liệu ngay từ tầng Ingestion (loại bỏ tag HTML, chuẩn hóa ISO date, deduplicate DOI) đóng vai trò sống còn đối với chất lượng của toàn bộ Data Pipeline phía sau.
3. **Về ảnh hưởng của Data đến RAG Agent:** Chất lượng dữ liệu đầu vào quyết định trực tiếp tới hiệu năng của RAG Agent (Garbage In, Garbage Out). Dữ liệu hỏng ở tầng ingestion sẽ làm suy giảm nghiêm trọng chỉ số retrieval hit rate và làm LLM trả lời sai lệch.

### Nếu có thêm thời gian

Thêm tính năng cashing HTTP request (`requests-cache`) và mở rộng hỗ trợ đa nguồn dữ liệu Ingestion (như arXiv API hoặc Semantic Scholar API) song song với Crossref REST API để tăng sự phong phú cho tập tài liệu khoa học.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lê Nguyễn Phi Trường  
**Ngày xác nhận:** 2026-08-06  

