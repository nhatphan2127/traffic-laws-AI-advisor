import sys
import os
import json
import logging
from pathlib import Path

# Add root directory to sys.path to allow module imports
sys.path.append(str(Path(__file__).parent.parent))

# Import retrieval function
from retrieval.retrieval import retrieval


# ============================================================
# Logging
# ============================================================

# Set up logging to stdout with UTF-8 support
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)

logger = logging.getLogger("evaluate_retrieval")


# ============================================================
# Ground Truth Matching
# ============================================================

def is_match(chunk_metadata: dict, gt_item: dict) -> bool:
    """
    Check whether a retrieved chunk matches a ground-truth item.

    Matching is based on:
        1. Document
        2. Article
        3. Clause
        4. Point (if provided in ground truth)
    """

    # --------------------------------------------------------
    # Document matching
    # --------------------------------------------------------

    doc_short_name = chunk_metadata.get("document_short_name", "")
    gt_doc = gt_item.get("document", "")

    clean_doc_short = (
        str(doc_short_name)
        .lower()
        .replace("/", "_")
        .replace("đ", "d")
    )

    clean_gt_doc = (
        str(gt_doc)
        .lower()
        .replace("/", "_")
        .replace("đ", "d")
    )

    doc_match = False

    # Special case for document 168/2024
    if "168" in clean_doc_short and "2024" in clean_doc_short:
        doc_match = True

    # Normal document matching
    elif clean_gt_doc in clean_doc_short:
        doc_match = True

    elif clean_doc_short in clean_gt_doc:
        doc_match = True

    # If document information is missing,
    # do not reject the document based on document name.
    elif not gt_doc or not doc_short_name:
        doc_match = True

    if not doc_match:
        return False

    # --------------------------------------------------------
    # Article matching
    # --------------------------------------------------------

    if chunk_metadata.get("article_number") != gt_item.get("article"):
        return False

    # --------------------------------------------------------
    # Clause matching
    # --------------------------------------------------------

    if chunk_metadata.get("clause_number") != gt_item.get("clause"):
        return False

    # --------------------------------------------------------
    # Point matching
    # --------------------------------------------------------

    gt_point = gt_item.get("point")

    if gt_point is not None:

        chunk_point = chunk_metadata.get("point")

        if chunk_point is None:
            return False

        if (
            str(chunk_point).strip().lower()
            != str(gt_point).strip().lower()
        ):
            return False

    return True


# ============================================================
# Evaluate One Query
# ============================================================

def evaluate_query(question: str, gt_items: list[dict]) -> dict:
    """
    Run retrieval for one query and calculate:

        Precision@3
        Precision@5
        Precision@10

        Recall@3
        Recall@5
        Recall@10
    """

    # --------------------------------------------------------
    # Retrieve documents
    # --------------------------------------------------------

    retrieved_docs = retrieval(question)

    results = {}

    # --------------------------------------------------------
    # Evaluate at K = 3, 5, 10
    # --------------------------------------------------------

    for k in [3, 5, 10]:

        # Take top K documents
        top_k_docs = retrieved_docs[:k]

        # Number of retrieved documents that are relevant
        relevant_retrieved_count = 0

        # Ground-truth items that were successfully retrieved
        matched_gt_indices = set()

        # ----------------------------------------------------
        # Check every retrieved document
        # ----------------------------------------------------

        for doc in top_k_docs:

            is_doc_relevant = False

            for gt_idx, gt in enumerate(gt_items):

                if is_match(doc.metadata, gt):

                    is_doc_relevant = True
                    matched_gt_indices.add(gt_idx)

            if is_doc_relevant:
                relevant_retrieved_count += 1

        # ----------------------------------------------------
        # Precision@K
        #
        # Precision@K =
        # relevant documents in top K / K
        # ----------------------------------------------------

        precision = (
            relevant_retrieved_count / k
            if k > 0
            else 0.0
        )

        # ----------------------------------------------------
        # Recall@K
        #
        # Recall@K =
        # relevant GT documents retrieved / total GT documents
        # ----------------------------------------------------

        recall = (
            len(matched_gt_indices) / len(gt_items)
            if len(gt_items) > 0
            else 0.0
        )

        results[f"precision@{k}"] = precision
        results[f"recall@{k}"] = recall

    # --------------------------------------------------------
    # Store retrieved documents
    # --------------------------------------------------------

    results["retrieved"] = [
        {
            "text": doc.text[:150] + "...",
            "metadata": doc.metadata,
            "score": doc.total_score,
        }
        for doc in retrieved_docs
    ]

    return results


# ============================================================
# Main Evaluation
# ============================================================

def main():

    # --------------------------------------------------------
    # Evaluation dataset
    # --------------------------------------------------------

    eval_file_path = Path(
        "data/processed/evals_168_2024.json"
    )

    if not eval_file_path.exists():

        logger.error(
            f"Evaluation file not found: {eval_file_path}"
        )

        return

    logger.info(
        f"Loading evaluation queries from {eval_file_path}"
    )

    # --------------------------------------------------------
    # Load JSON
    # --------------------------------------------------------

    with open(
        eval_file_path,
        "r",
        encoding="utf-8"
    ) as f:

        evals = json.load(f)

    logger.info(
        f"Starting evaluation of {len(evals)} queries..."
    )

    # ========================================================
    # Initialize totals
    # ========================================================

    total_p3 = 0.0
    total_p5 = 0.0
    total_p10 = 0.0

    total_r3 = 0.0
    total_r5 = 0.0
    total_r10 = 0.0

    # Detailed results for every query
    detailed_results = []

    # ========================================================
    # Evaluate every query
    # ========================================================

    for idx, item in enumerate(evals):

        question = item["question"]
        gt_items = item["retrieve_items"]

        logger.info(
            f"[{idx + 1}/{len(evals)}] "
            f"Evaluating query: '{question}'"
        )

        # ----------------------------------------------------
        # Evaluate query
        # ----------------------------------------------------

        res = evaluate_query(
            question,
            gt_items
        )

        # ----------------------------------------------------
        # Get metrics
        # ----------------------------------------------------

        p3 = res["precision@3"]
        p5 = res["precision@5"]
        p10 = res["precision@10"]

        r3 = res["recall@3"]
        r5 = res["recall@5"]
        r10 = res["recall@10"]

        # ----------------------------------------------------
        # Accumulate totals
        # ----------------------------------------------------

        total_p3 += p3
        total_p5 += p5
        total_p10 += p10

        total_r3 += r3
        total_r5 += r5
        total_r10 += r10

        # ----------------------------------------------------
        # Store detailed result
        # ----------------------------------------------------

        detailed_results.append(
            {
                "question": question,

                "ground_truth": gt_items,

                "metrics": {
                    "precision@3": p3,
                    "precision@5": p5,
                    "precision@10": p10,

                    "recall@3": r3,
                    "recall@5": r5,
                    "recall@10": r10,
                },

                "retrieved_items": res["retrieved"],
            }
        )

    # ========================================================
    # Calculate averages
    # ========================================================

    num_queries = len(evals)

    if num_queries > 0:

        avg_p3 = total_p3 / num_queries
        avg_p5 = total_p5 / num_queries
        avg_p10 = total_p10 / num_queries

        avg_r3 = total_r3 / num_queries
        avg_r5 = total_r5 / num_queries
        avg_r10 = total_r10 / num_queries

    else:

        avg_p3 = 0.0
        avg_p5 = 0.0
        avg_p10 = 0.0

        avg_r3 = 0.0
        avg_r5 = 0.0
        avg_r10 = 0.0

    # ========================================================
    # Summary
    # ========================================================

    summary = {
        "total_queries": num_queries,

        "metrics": {
            "average_precision@3": avg_p3,
            "average_precision@5": avg_p5,
            "average_precision@10": avg_p10,

            "average_recall@3": avg_r3,
            "average_recall@5": avg_r5,
            "average_recall@10": avg_r10,
        },
    }

    # ========================================================
    # Complete report
    # ========================================================

    report = {
        "summary": summary,
        "results": detailed_results,
    }

    # ========================================================
    # Save report
    # ========================================================

    output_dir = Path("evaluation")

    output_dir.mkdir(
        exist_ok=True
    )

    report_file_path = (
        output_dir / "evaluation_results.json"
    )

    with open(
        report_file_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================
    # Print summary
    # ========================================================

    logger.info(
        "=== EVALUATION REPORT SUMMARY ==="
    )

    logger.info(
        f"Total evaluated queries: {num_queries}"
    )

    logger.info(
        f"Average Precision@3:  {avg_p3:.4f}"
    )

    logger.info(
        f"Average Precision@5:  {avg_p5:.4f}"
    )

    logger.info(
        f"Average Precision@10: {avg_p10:.4f}"
    )

    logger.info(
        f"Average Recall@3:     {avg_r3:.4f}"
    )

    logger.info(
        f"Average Recall@5:     {avg_r5:.4f}"
    )

    logger.info(
        f"Average Recall@10:    {avg_r10:.4f}"
    )

    logger.info(
        f"Full report saved to {report_file_path}"
    )


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()