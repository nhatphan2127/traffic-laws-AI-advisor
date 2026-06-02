import streamlit as st
import re
import json

def roman_to_int(s):
    roman = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    total = 0
    prev = 0
    for char in reversed(s.upper()):
        value = roman.get(char, 0)
        if value < prev:
            total -= value
        else:
            total += value
            prev = value
    return total

def is_table_row(line):
    """Nhận diện dòng chứa dữ liệu dạng bảng dựa trên khoảng trắng rộng hoặc tab."""
    parts = re.split(r'\t|\s{2,}', line.strip())
    if re.match(r'^(Chương|Điều|Khoản|Mục|Tiểu mục)\s', line.strip(), re.IGNORECASE):
        return False
    return len(parts) >= 2

def parse_table_block(lines, start_idx):
    """Gom nhóm liên tiếp các dòng bảng."""
    table_data = []
    idx = start_idx
    while idx < len(lines) and is_table_row(lines[idx]):
        parts = re.split(r'\t|\s{2,}', lines[idx].strip())
        table_data.append(parts)
        idx += 1
    return table_data, idx

def extract_references(text, current_art=None, current_cl=None):
    """Tự động phân tích các liên kết chéo pháp lý trong câu văn."""
    references = []
    text_lower = text.lower()
    
    law_ref = re.search(r'Điều\s+(\d+)\s+của\s+(Luật\s+[^,;.\n]+)', text, re.IGNORECASE)
    if law_ref:
        references.append({
            "document": law_ref.group(2).strip(),
            "article": int(law_ref.group(1)),
            "clause": None,
            "point": None
        })
        return references

    point_clause_art = re.search(r'điểm\s+([a-zđ])\s+khoản\s+(\d+)\s+Điều\s+(này|\d+)', text, re.IGNORECASE)
    if point_clause_art:
        art_val = current_art
        if point_clause_art.group(3).isdigit():
            art_val = int(point_clause_art.group(3))
        references.append({
            "document": "Nghị định này",
            "article": art_val,
            "clause": int(point_clause_art.group(2)),
            "point": point_clause_art.group(1)
        })
        return references

    clause_art = re.search(r'khoản\s+(\d+)\s+Điều\s+(này|\d+)', text, re.IGNORECASE)
    if clause_art:
        art_val = current_art
        if clause_art.group(2).isdigit():
            art_val = int(clause_art.group(2))
        references.append({
            "document": "Nghị định này",
            "article": art_val,
            "clause": int(clause_art.group(1)),
            "point": None
        })
        return references

    if "khoản này" in text_lower:
        points = re.findall(r'điểm\s+([a-zđ])', text, re.IGNORECASE)
        for p in points:
            references.append({
                "document": "Nghị định này",
                "article": current_art,
                "clause": current_cl,
                "point": p
            })
        return references

    return references

def clean_empty_nodes(d):
    """Hàm đệ quy loại bỏ hoàn toàn các nút/trường rỗng như [], {}, '' khỏi JSON."""
    if isinstance(d, dict):
        cleaned = {}
        for k, v in d.items():
            # Không thêm các trường rỗng, None hoặc chuỗi rỗng
            if v is None or v == "" or v == [] or v == {}:
                continue
            cleaned[k] = clean_empty_nodes(v)
        return cleaned
    elif isinstance(d, list):
        return [clean_empty_nodes(v) for v in d]
    else:
        return d

def parse_legal_document_to_schema(text):
    data = {
        "document_title": "",
        "legal_basis": "",
        "chapters": []
    }
    
    # Phân tách tiêu đề và căn cứ pháp lý
    try:
        chapter_1_idx = text.find("Chương I")
        preamble_text = text[:chapter_1_idx] if chapter_1_idx != -1 else text
        title_lines, basis_lines = [], []
        
        for line in preamble_text.split('\n'):
            line = line.strip()
            if not line: continue
            if any(line.startswith(x) for x in ["Căn cứ", "Theo đề nghị", "Chính phủ ban hành"]):
                basis_lines.append(line)
            elif "NGHỊ ĐỊNH" in line or "QUY ĐỊNH" in line or "LUẬT" in line:
                title_lines.append(line)
                
        data["document_title"] = " ".join(title_lines)
        data["legal_basis"] = "\n".join(basis_lines)
        if chapter_1_idx != -1:
            text = text[chapter_1_idx:]
    except Exception:
        pass

    lines = text.split('\n')
    current_chapter = None
    current_article = None
    current_clause = None
    current_point = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # 1. Chương
        chap_match = re.compile(r'^Chương\s+([IVXLCDM]+)', re.IGNORECASE).match(line)
        if chap_match:
            chapter_num = roman_to_int(chap_match.group(1))
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            chapter_title = lines[i].strip() if i < len(lines) else ""
            
            current_chapter = {
                "chapter_number": chapter_num,
                "chapter_title": chapter_title,
                "articles": []
            }
            data["chapters"].append(current_chapter)
            current_article = None
            current_clause = None
            current_point = None
            i += 1
            continue

        # 2. Điều
        art_match = re.compile(r'^Điều\s+(\d+)\.\s+(.*)', re.IGNORECASE).match(line)
        if art_match:
            current_article = {
                "article_number": int(art_match.group(1)),
                "article_title": line,
                "article_intro": "", 
                "clauses": [],
                "else_elements": []
            }
            if current_chapter:
                current_chapter["articles"].append(current_article)
            current_clause = None
            current_point = None
            i += 1
            continue

        # 3. Khoản
        clause_match = re.compile(r'^(\d+)\.\s+(.*)').match(line)
        if clause_match and current_article:
            cl_num = int(clause_match.group(1))
            cl_content = clause_match.group(2)
            
            current_clause = {
                "clause_number": cl_num,
                "content": cl_content,
                "points": [],
                "else_elements": []
            }
            
            refs = extract_references(cl_content, current_article["article_number"], cl_num)
            if refs:
                current_clause["references"] = refs
                
            current_article["clauses"].append(current_clause)
            current_point = None
            i += 1
            continue

        # 4. Điểm
        point_match = re.compile(r'^([a-zđ]\))\s+(.*)', re.IGNORECASE).match(line)
        if point_match and current_clause:
            p_letter = point_match.group(1).replace(")", "")
            p_content = point_match.group(2)
            
            current_point = {
                "point": p_letter,
                "content": p_content,
                "else_elements": []
            }
            
            refs = extract_references(p_content, current_article["article_number"], current_clause["clause_number"])
            if refs:
                current_point["references"] = refs
                
            current_clause["points"].append(current_point)
            i += 1
            continue

        # 5. Xử lý Bảng biểu (Được tách thành header và content)
        if is_table_row(line):
            table_rows, next_idx = parse_table_block(lines, i)
            if table_rows:
                header = table_rows[0]
                content = table_rows[1:] if len(table_rows) > 1 else []
                
                table_element = {
                    "type": "table",
                    "header": header,
                    "content": content
                }
                
                if current_point:
                    current_point["else_elements"].append(table_element)
                elif current_clause:
                    current_clause["else_elements"].append(table_element)
                elif current_article:
                    current_article["else_elements"].append(table_element)
            i = next_idx
            continue

        # 6. Xử lý văn bản nối tiếp (bao gồm cả các câu Trích dẫn nằm trong ngoặc kép)
        if current_point:
            current_point["content"] += " " + line
            refs = extract_references(current_point["content"], current_article["article_number"], current_clause["clause_number"])
            if refs:
                current_point["references"] = refs
        elif current_clause:
            current_clause["content"] += " " + line
            refs = extract_references(current_clause["content"], current_article["article_number"], current_clause["clause_number"])
            if refs:
                current_clause["references"] = refs
        elif current_article:
            current_article["article_intro"] = (current_article["article_intro"] + " " + line).strip()

        i += 1

    # Làm sạch các trường dữ liệu rỗng trước khi xuất JSON
    cleaned_data = clean_empty_nodes(data)
    return cleaned_data

# --- Streamlit UI ---
st.set_page_config(page_title="Smart Legal Parser", layout="wide")

st.title("🇻🇳 Convert Vietnamese Legal Document to JSON")
st.markdown("Hệ thống bóc tách Chương, Điều, Khoản, Điểm tự động. Nhận diện bảng biểu thành tiêu đề (`header`) và dữ liệu (`content`) [1].")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Input Raw Text")
    raw_text = st.text_area("Paste text here...", height=600)
    process_btn = st.button("Convert to JSON 🚀", type="primary")

with col2:
    st.subheader("⚙️ Output JSON")
    if process_btn and raw_text:
        with st.spinner("Đang xử lý phân tích cú pháp..."):
            parsed_data = parse_legal_document_to_schema(raw_text)
            json_result = json.dumps(parsed_data, ensure_ascii=False, indent=4)
            
            st.download_button(
                label="📥 Tải xuống file JSON",
                file_name="structured_law.json",
                mime="application/json",
                data=json_result
            )
            
            st.json(parsed_data)
            
    elif process_btn and not raw_text:
        st.warning("Vui lòng dán văn bản vào ô Input trước!")