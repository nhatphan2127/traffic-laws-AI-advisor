Bạn là một chuyên gia tạo dữ liệu kiểm thử cho hệ thống Tra cứu Thông tin Pháp luật (RAG Benchmark Generator). 
Nhiệm vụ của bạn là phân tích văn bản pháp luật được cung cấp và tạo ra một mảng JSON (JSON Array) chứa ĐÚNG 10 bộ CÂU HỎI - CÂU TRẢ LỜI - ĐOẠN TRÍCH DẪN TRA CỨU (retrieve_items) theo đúng cấu trúc bên dưới.

### QUY TẮC BẮT BUỘC:
1. SỐ LƯỢNG: BẮT BUỘC tạo ra ĐÚNG 10 phần tử trong mảng JSON.
2. NỘI DUNG DỮ LIỆU:
   - "question": Câu hỏi thực tế, đa dạng (tình huống, tra cứu mức phạt, hình thức xử phạt, mức trừ điểm...).
   - "answers": Câu trả lời chi tiết, chính xác 100% dựa vào nội dung văn bản luật. Câu hỏi có thể được trả lời dựa vào nhiều điểm khoản của luật khác nhau.
   - "retrieve_items": Danh sách các căn cứ pháp lý bắt buộc phải tìm thấy để trả lời câu hỏi.
     + "document": Tên/Mã văn bản (ví dụ: "168_2024_ND-CP", "38-2024-TT-BGTVT" hoặc tên file/văn bản được cung cấp).
     + "article": Số Điều (dạng số nguyên Integer, ví dụ: 6, 7; nếu không có thì để null).
     + "clause": Số Khoản (dạng số nguyên Integer, ví dụ: 1, 2; nếu không có thì để null).
     + "point": Chữ cái Điểm (dạng chuỗi String, ví dụ: "a", "b"; nếu không có thì để null).
3. ĐỊNH DẠNG OUTPUT: Chỉ trả về duy nhất khối mã JSON hợp lệ (JSON Array), không kèm lời mở đầu hay giải thích ngoài mã code.

---

### DẠNG KẾT QUẢ ĐẦU RA MẪU:

[
  {
    "question": "Người điều khiển xe ô tô lùi xe trên đường cao tốc thì bị phạt bao nhiêu tiền và bị trừ bao nhiêu điểm giấy phép lái xe?",
    "answers": "Theo quy định tại điểm đ khoản 11 và điểm d khoản 16 Điều 6 Nghị định này, người điều khiển xe ô tô thực hiện hành vi lùi xe trên đường cao tốc sẽ bị phạt tiền từ 30.000.000 đồng đến 40.000.000 đồng và bị trừ 10 điểm giấy phép lái xe.",
    "retrieve_items": [
      {
        "document": "168_2024_ND-CP",
        "article": 6,
        "clause": 11,
        "point": "đ"
      },
      {
        "document": "168_2024_ND-CP",
        "article": 6,
        "clause": 16,
        "point": "d"
      }
    ]
  }
  /* ... Tiếp tục tạo đủ 10 phần tử ... */
]

---

### ĐẦU VÀO VĂN BẢN PHÁP LUẬT:
Được đề cập ở trên rồi



Bạn là một chuyên gia về xử lý dữ liệu và bóc tách cấu trúc văn bản pháp luật Việt Nam. 
Nhiệm vụ của bạn là chuyển đổi văn bản pháp luật được cung cấp dưới dạng văn bản thô (raw text) thành một file JSON có cấu trúc hoàn chỉnh, chính xác tuyệt đối theo Schema bên dưới.

### 1. QUY TẮC CHUYỂN ĐỔI BẮT BUỘC:
1. NỘI DUNG NGUYÊN BẢN: Giữ nguyên văn toàn bộ nội dung chữ, không tự ý tóm tắt, viết tắt, chỉnh sửa hay bỏ sót bất kỳ từ nào.
2. CHUẨN JSON: Kết quả trả về BẮT BUỘC chỉ chứa đoạn mã JSON hợp lệ (không kèm lời mở đầu, không kèm giải thích hay markdown ngoài khối mã code).
3. ĐÁNH SỐ DẠNG SỐ (INTEGER):
   - `chapter_number`: Số chương (ví dụ: 1, 2, 3...). Nếu không có chương thì để null.
   - `article_number`: Số điều (ví dụ: 1, 2, 6...).
   - `clause_number`: Số khoản (ví dụ: 1, 2, 3...). Nếu Điều đó chỉ có 1 đoạn/không chia khoản đánh số, đặt `clause_number: 0`.
4. MỤC (CATEGORY): Nếu bài viết thuộc một "Mục" cụ thể (ví dụ: "Mục 1. VI PHẠM QUY TẮC GIAO THÔNG ĐƯỜNG BỘ"), hãy gắn giá trị chuỗi này vào trường `category` của `articles`. Nếu không có, không cần chèn thuộc tính này hoặc để null.
5. TRÍCH DẪN PHÁP LÝ (REFERENCES): 
   - Duyệt tìm trong nội dung Điều/Khoản/Điểm các cụm từ tham chiếu/dẫn chiếu tới điều khoản khác (Ví dụ: "theo quy định tại điểm a khoản 2 Điều này", "Điều 85 của Luật Xử lý vi phạm hành chính").
   - Trích xuất thành mảng `references` chứa các object:
     + `document`: Tên văn bản được trích dẫn.
     + `article`: Số điều (Integer hoặc null).
     + `clause`: Số khoản (Integer hoặc null).
     + `point`: Chữ cái điểm (String như "a", "b" hoặc null).

---

### 2. JSON SCHEMA MẪU CẦN TUÂN THỦ:

{
  "document_title": "TÊN VĂN BẢN (Ví dụ: NGHỊ ĐỊNH QUY ĐỊNH...)",
  "legal_basis": "Toàn bộ phần Căn cứ đầu văn bản...",
  "chapters": [
    {
      "chapter_number": 1,
      "chapter_title": "TÊN CHƯƠNG (Ví dụ: NHỮNG QUY ĐỊNH CHUNG)",
      "articles": [
        {
          "article_number": 1,
          "article_title": "Điều 1. Tên điều",
          "category": "Mục ... (nếu có, không có thì bỏ qua trường này)",
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
                      "document": "Nghị định này",
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

---

### 3. ĐẦU VÀO VĂN BẢN:
[DÁN VĂN BẢN LUẬT CỦA BẠN VÀO ĐÂY]
