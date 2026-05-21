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

def parse_legal_document(text):
    data = {
        "document_title": "",
        "legal_basis": "",
        "chapters": []
    }
    
    # Regex patterns
    chapter_pattern = re.compile(r'^Chương\s+([IVXLCDM]+)', re.IGNORECASE)
    section_pattern = re.compile(r'^Mục\s+(\d+)\.\s+(.*)', re.IGNORECASE)
    article_pattern = re.compile(r'^Điều\s+(\d+)\.\s+(.*)', re.IGNORECASE)
    clause_pattern = re.compile(r'^(\d+)\.\s+(.*)')
    point_pattern = re.compile(r'^([a-zđ]+)\)\s+(.*)', re.IGNORECASE)

    # 1. Parse Preamble (Title & Legal Basis)
    try:
        chapter_1_idx = text.find("Chương I")
        preamble_text = text[:chapter_1_idx] if chapter_1_idx != -1 else text
        
        title_lines = []
        basis_lines = []
        
        for line in preamble_text.split('\n'):
            line = line.strip()
            if not line: continue
            
            # Identify legal basis lines
            if line.startswith("Căn cứ") or line.startswith("Theo đề nghị") or line.startswith("Chính phủ ban hành"):
                basis_lines.append(line)
            # Identify Title (Skip header boilerplate)
            elif "NGHỊ ĐỊNH" in line or "QUY ĐỊNH XỬ PHẠT" in line:
                title_lines.append(line)
                
        data["document_title"] = " ".join(title_lines)
        data["legal_basis"] = "\n".join(basis_lines)
        
        # Cut text to start from Chapter I
        if chapter_1_idx != -1:
            text = text[chapter_1_idx:]
    except Exception:
        pass

    # 2. Parse Body Structure
    lines = text.split('\n')
    
    current_chapter = None
    current_article = None
    current_clause = None
    current_point = None
    current_section = None
    
    state = "BODY"
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Check Chapter
        chap_match = chapter_pattern.match(line)
        if chap_match:
            chapter_num = roman_to_int(chap_match.group(1))
            current_chapter = {
                "chapter_number": chapter_num,
                "chapter_title": "", 
                "articles": []
            }
            data["chapters"].append(current_chapter)
            current_section = None # Reset category on new chapter
            
            # The next non-empty line is usually the chapter title
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines):
                current_chapter["chapter_title"] = lines[i].strip()
            i += 1
            continue

        # Check Section (Mục)
        sec_match = section_pattern.match(line)
        if sec_match:
            current_section = line
            i += 1
            continue

        # Check Article (Điều)
        art_match = article_pattern.match(line)
        if art_match:
            current_article = {
                "article_number": int(art_match.group(1)),
                "article_title": line,
                "category": current_section if current_section else None,
                "clauses": []
            }
            if current_chapter:
                current_chapter["articles"].append(current_article)
            
            current_clause = None
            current_point = None
            i += 1
            continue

        # Check Clause (Khoản)
        clause_match = clause_pattern.match(line)
        if clause_match and current_article:
            current_clause = {
                "clause_number": int(clause_match.group(1)),
                "content": clause_match.group(2),
                "points": []
            }
            current_article["clauses"].append(current_clause)
            current_point = None
            i += 1
            continue

        # Check Point (Điểm)
        point_match = point_pattern.match(line)
        if point_match and current_clause:
            current_point = {
                "point": point_match.group(1),
                "content": point_match.group(2)
            }
            current_clause["points"].append(current_point)
            i += 1
            continue

        # Handle Multiline text continuation
        if current_point:
            current_point["content"] += " " + line
        elif current_clause:
            current_clause["content"] += " " + line
        elif current_article:
            # If an article has text before a numbered clause (or just a single paragraph)
            if not current_article["clauses"]:
                current_article["clauses"].append({
                    "clause_number": 0,
                    "content": line,
                    "points": []
                })
                current_clause = current_article["clauses"][0]
            else:
                current_article["clauses"][-1]["content"] += " " + line

        i += 1

    # Cleanup empty points array to match your schema precisely
    for ch in data["chapters"]:
        for art in ch["articles"]:
            for cl in art["clauses"]:
                if not cl["points"]:
                    del cl["points"]
            if art["category"] is None:
                del art["category"]

    return data

# --- Streamlit UI ---
st.set_page_config(page_title="Legal Text to JSON Converter", layout="wide")

st.title("🇻🇳 Convert Vietnamese Legal Document to JSON")
st.markdown("Dán toàn bộ văn bản Nghị định vào ô bên trái, hệ thống sẽ tự động phân tích bóc tách **Chương, Mục, Điều, Khoản, Điểm** và xuất ra JSON ở bên phải.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Input Raw Text")
    raw_text = st.text_area("Paste text here...", height=600)
    process_btn = st.button("Convert to JSON 🚀", type="primary")

with col2:
    st.subheader("⚙️ Output JSON")
    if process_btn and raw_text:
        with st.spinner("Đang xử lý phân tích cú pháp..."):
            parsed_data = parse_legal_document(raw_text)
            json_result = json.dumps(parsed_data, ensure_ascii=False, indent=4)
            
            st.download_button(
                label="📥 Tải xuống file JSON",
                file_name="nghi_dinh_168.json",
                mime="application/json",
                data=json_result
            )
            
            st.json(parsed_data)
    elif process_btn and not raw_text:
        st.warning("Vui lòng dán văn bản vào ô Input trước!")