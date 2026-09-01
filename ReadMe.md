# Hệ Thống RAG Hỏi Đáp Văn Bản Pháp Luật Giao Thông Việt Nam

## 1. Giới thiệu (Introduction)

Hệ thống **Vietnamese Legal Document RAG (Retrieval-Augmented Generation)** được xây dựng nhằm hỗ trợ người dùng tra cứu và giải đáp các thắc mắc về pháp luật giao thông đường bộ tại Việt Nam. Hệ thống tập trung xử lý dữ liệu của **Nghị định 168/2024/NĐ-CP** (văn bản quy định mức xử phạt VPHC trong lĩnh vực giao thông với nhiều hình phạt mang tính răn đe cao hơn).

Mục tiêu chính của hệ thống là đảm bảo tính **chính xác**, **đầy đủ ngữ cảnh pháp lý** (bao gồm hình phạt chính, hình phạt bổ sung và các điều khoản tham chiếu) và tránh tình trạng "bốc phét" (hallucination) của Mô hình ngôn ngữ lớn (LLM).

---

## 2. Chuẩn hóa dữ liệu (Data Standardization)

Dữ liệu gốc ban đầu ở định dạng Microsoft Word (`.docx`). Để phục vụ quá trình tự động hóa chunking và truy vấn, dữ liệu được chuyển đổi sang định dạng **JSON** lưu trữ cấu trúc phân cấp của văn bản quy phạm pháp luật.

### 2.1. Cấu trúc JSON dữ liệu gốc

```json
{
  "document_title": "TÊN VĂN BẢN",
  "legal_basis": "Toàn bộ phần Căn cứ đầu văn bản...",
  "chapters": [
    {
      "chapter_number": 1,
      "chapter_title": "TÊN CHƯƠNG",
      "articles": [
        {
          "article_number": 1,
          "article_title": "Điều 1. Phạm vi điều chỉnh",
          "category": "Mục ...",
          "clauses": [
            {
              "clause_number": 1,
              "content": "Nội dung của khoản 1...",
              "points": [
                {
                  "point": "a",
                  "content": "Nội dung điểm a...",
                  "references": [
                    {
                      "document": "168/2024/NĐ-CP",
                      "article": 6,
                      "clause": 2,
                      "point": "a"
                    }
                  ]
                }
              ],
              "references": []
            }
          ]
        }
      ]
    }
  ]
}
```

### 2.2. Ý nghĩa các trường dữ liệu

| Trường dữ liệu | Ý nghĩa |
| :--- | :--- |
| `document_title` | Tên đầy đủ của văn bản quy phạm pháp luật |
| `legal_basis` | Phần căn cứ pháp lý ở đầu văn bản |
| `chapters` | Danh sách các chương thuộc văn bản |
| `chapter_number` / `chapter_title` | Số thứ tự và tiêu đề chương |
| `articles` | Danh sách các Điều thuộc Chương |
| `article_number` / `article_title` | Số hiệu và tiêu đề của Điều |
| `category` | Mục chứa Điều (nếu văn bản có phân chia theo Mục) |
| `clauses` | Danh sách các Khoản thuộc Điều |
| `clause_number` / `content` | Số thứ tự và nội dung chính của Khoản |
| `points` | Danh sách các Điểm (a, b, c...) thuộc Khoản |
| `point` / `content` | Ký hiệu Điểm và nội dung chi tiết của Điểm |
| `references` | Trích dẫn tham chiếu tới các Điều, Khoản, Điểm hoặc văn bản khác |

---

## 3. Chiến lược phân đoạn dữ liệu (Chunking Strategy)

Từ dữ liệu JSON phân cấp, hệ thống thực hiện tách nhỏ dữ liệu (chunking) theo nguyên tắc giữ nguyên ngữ cảnh:

1. **Nguyên tắc tách**:
   - Khoản không có Điểm $\rightarrow$ Tạo thành 1 Chunk riêng.
   - Khoản có các Điểm $\rightarrow$ Tách riêng từng Điểm thành từng Chunk, nhưng **luôn giữ kèm nội dung của Khoản cha và Điều cha** để không bị mất ngữ cảnh chung.
2. **Định dạng Chunk**:

```json
{
  "text": "[Văn bản: Nghị định 168/2024/NĐ-CP]\n[Chương I: NHỮNG QUY ĐỊNH CHUNG]\n[Điều 1. Phạm vi điều chỉnh]\nKhoản 1: Nội dung của khoản...",
  "metadata": {
    "document_title": "Nghị định ...",
    "document_short_name": "Nghị định 168/2024/NĐ-CP",
    "chapter_number": 1,
    "chapter_title": "NHỮNG QUY ĐỊNH CHUNG",
    "article_number": 1,
    "article_title": "Điều 1. Phạm vi điều chỉnh",
    "article_category": "",
    "clause_number": 1,
    "is_point": false,
    "point": null,
    "references": []
  }
}
```

3. **Biểu diễn dữ liệu**: Trường `text` của mỗi Chunk được đưa qua mô hình để sinh ra cả **Dense Embedding** (ngữ nghĩa) và **Sparse Embedding** (từ khóa BM25/SPLADE), phục vụ cho cơ chế **Hybrid Retrieval**.

---

## 4. Kiến trúc hệ thống (System Architecture)

![Alt text](system.png)

Hệ thống hoạt động qua 5 giai đoạn chính:

1. **Query Normalization (Chuẩn hóa câu hỏi)**:
   - Mở rộng từ khóa thông thường sang **thuật ngữ pháp lý đồng nghĩa**.
   - *Ví dụ*: "xe máy" $\rightarrow$ "xe mô tô, xe gắn máy"; "vượt đèn đỏ" $\rightarrow$ "không chấp hành hiệu lệnh của đèn tín hiệu giao thông".
   - Giúp nâng cao khả năng khớp dữ liệu ở bước Retrieval.

2. **Retrieval Stage (Truy vấn kết hợp Hybrid Retrieval)**:
   - Truy xuất các đoạn văn bản (chunks) liên quan dựa trên sự kết hợp giữa Dense Vector Search và Sparse Keyword Search.

3. **Reference Expansion (Mở rộng điều khoản tham chiếu)**:
   - Trong văn bản luật, các hình phạt bổ sung hoặc định nghĩa thường dẫn chiếu tới Điều/Khoản khác (ví dụ: *"Bị xử phạt theo quy định tại Điểm a Khoản 2 Điều 6"*).
   - Bước này tự động trích xuất metadata và truy xuất thêm các Điều/Khoản được tham chiếu.
   - **Ưu điểm**: Hạn chế tối đa việc bỏ sót thông tin pháp lý quan trọng (tăng tính đầy đủ).
   - **Hạn chế**: Làm tăng độ dài Context (Context Length), có thể làm loãng thông tin nếu bước Retrieval ban đầu lấy nhầm tài liệu không liên quan.

4. **Response Generation (Sinh câu trả lời với LLM)**:
   - Tổng hợp các đoạn văn bản từ bước Retrieval và Expansion làm Context cho LLM để tạo câu trả lời chính xác, kèm trích dẫn Điều/Khoản cụ thể.

5. **Logging & History (Lưu trữ tương tác)**:
   - Toàn bộ lịch sử truy vấn, context trích xuất và câu trả lời của hệ thống được ghi nhận vào cơ sở dữ liệu **MongoDB** để phục vụ việc giám sát và đánh giá.

---

## 5. Đánh giá hệ thống (Evaluation & Metrics)

### 5.1. Khái niệm và Công thức các độ đo

Hệ thống được đánh giá qua 2 giai đoạn: **Initial Retrieval** (Truy vấn ban đầu) và **Document Expansion** (Mở rộng điều khoản).

Một chunk được coi là **khớp (Match)** với tập dữ liệu chuẩn (Ground Truth - GT) nếu thỏa mãn đồng thời: `Tên văn bản` + `Điều` + `Khoản` + `Điểm` (nếu có).

#### Giai đoạn 1: Đánh giá truy vấn ban đầu (Initial Retrieval Metrics)
- **MRR (Mean Reciprocal Rank)**:
  - *Ý nghĩa*: Đánh giá vị trí xuất hiện của tài liệu đúng **đầu tiên** trong danh sách kết quả. Vị trí đúng càng gần top 1 thì điểm MRR càng tiến gần 1.
- **Recall@K ($K = 1, 3, 5$)**:
  - *Ý nghĩa*: Tỷ lệ các tài liệu đúng (Ground Truth) được hệ thống tìm thấy nằm trong **Top K** kết quả đầu tiên.
- **NDCG@K ($K = 1, 3, 5$) (Normalized Discounted Cumulative Gain)**:
  - *Ý nghĩa*: Đánh giá chất lượng xếp hạng của Top K kết quả. Tài liệu đúng xuất hiện ở thứ hạng càng cao thì điểm NDCG càng cao (có tính đến yếu tố vị trí phạt).

#### Giai đoạn 2: Đánh giá mở rộng ngữ cảnh (Expansion Metrics)
- **Final Recall (Recall@ALL)**:
  - *Ý nghĩa*: Tỷ lệ tài liệu đúng tìm được trên tổng số Ground Truth sau khi đã thực hiện mở rộng các điều khoản tham chiếu.

---

### 5.2. Kết quả đánh giá chi tiết

Đánh giá được thực hiện trên tập dữ liệu thử nghiệm chuẩn `evals_168_2024.json` với **100 câu truy vấn** thực tế:

#### Evaluation
| Độ đo | Top 1 ($K=1$) | Top 3 ($K=3$) | Top 5 ($K=5$) |
| :--- | :---: | :---: | :---: |
| **Recall@K** | 0.5950 | 0.7350 | 0.7433 |
| **NDCG@K** | 0.7700 | 0.7382 | 0.7469 |
| **MRR** |0.8495 | - | - |
| **Final Recall** | **0.9350** | - | - |


