import sys
import os

# =========================================================================
# 1. ÉP UTF-8 NGAY TỪ DÒNG ĐẦU TIÊN (Trước khi import bất kỳ module nào khác)
# =========================================================================
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from pathlib import Path
import logging

# Add the root directory to sys.path to allow module imports
sys.path.append(str(Path(__file__).parent.parent))

# =========================================================================
# 2. IMPORT MODULE SAU KHI ĐÃ ÉP UTF-8
# =========================================================================
from functions.qdrant_filter import (
    extract_relevant_clause_point,
    extract_clause_point,
    extract_clause_point_references,
    format_records_for_llm
)

# =========================================================================
# 3. SETUP LOGGING VỚI THAM SỐ `force=True` (Xóa bỏ cấu hình lỗi cũ nếu có)
# =========================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True  # Rất quan trọng: Bắt buộc ghi đè lên các config cũ của qdrant_filter
)
logger = logging.getLogger('test_qdrant')


def test_extract_direct_content():
    print("=== TEST 1: DIRECT CONTENT QUERY (FUNCTION 2) ===")
    
    # Scenario 1: Article 6, Clause 1, Point a (Car sign violations)
    print("--- Scenario 1.1: Article 6, Clause 1, Point a ---")
    results = extract_clause_point(article=7, clause=2, point='đ')
    print(f"Found: {len(results)} records")
    if results:
        print(f"Records output:\n{format_records_for_llm(results)}")

    # # Scenario 2: Entire Article 2 (Applicable subjects)
    # print("--- Scenario 1.2: Entire Article 2 ---")
    # results = extract_clause_point(article=2)
    # print(f"Found: {len(results)} records")
    # # print(f"Records output:\n{format_records_for_llm(results)}") # Temporarily commented out

    # # Scenario 3: Article 13 (License plates)
    # print("--- Scenario 1.3: Article 13 ---")
    # results = extract_clause_point(article=13)
    # print(f"Found: {len(results)} records")

def test_extract_inbound_references():
    print("=== TEST 2: FIND INBOUND REFERENCES (FUNCTION 1) ===")
    
    # # Scenario: Which provisions mention Article 2 Clause 1
    # print("--- Scenario 2.1: Contents referencing Article 2 Clause 1 ---")
    # results = extract_relevant_clause_point(document="Nghị định này", article=6, clause=2, point='d')
    # print(f"Found: {len(results)} records referencing Article 2 Clause 1")
    # if results:
    #     print(f"Records output:\n{format_records_for_llm(results)}")

    # Scenario: Which violations lead to supplementary penalties in Article 6 Clause 11
    print("--- Scenario 2.2: Contents referencing Article 6 Clause 11 (Supplementary penalties) ---")
    results = extract_relevant_clause_point(document="Nghị định này", article=7, clause=2, point='đ')
    print(f"Found: {len(results)} records")
    if results:
        # Log the first 3 results
        print(f"Records output (first 3):\n{format_records_for_llm(results[:3])}")

def test_extract_outbound_content():
    print("=== TEST 3: GET CONTENT OF OUTBOUND REFERENCES (FUNCTION 3) ===")
    
    # Scenario: What is Article 2 Clause 2 referring to? (Refers to Article 2 Clause 1)
    print("--- Scenario 3.1: Actual content referenced by Article 2 Clause 2 ---")
    results = extract_clause_point_references(article=7, clause=12, point="b")
    print(f"Found: {len(results)} referenced records")
    if results:
        print(f"Records output:\n{format_records_for_llm(results)}")

    # Scenario: References of Article 6 Clause 11 (Revocation of Driver's License)
    print("--- Scenario 3.2: Contents referenced by Article 6 Clause 11 ---")
    results = extract_clause_point_references(article=6, clause=2, point='d')
    print(f"Found: {len(results)} referenced records")
    if results:
        print(f"Records output (first 3):\n{format_records_for_llm(results[:3])}")

if __name__ == "__main__":
    try:
        # test_extract_direct_content()
        # test_extract_inbound_references()
        test_extract_outbound_content()
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY.")
    except Exception as e:
        logger.error(f"❌ AN ERROR OCCURRED: {e}", exc_info=True)