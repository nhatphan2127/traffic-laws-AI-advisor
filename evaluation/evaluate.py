import sys
import json
import math
import logging
import argparse
from pathlib import Path

# Add root directory to sys.path to allow module imports
sys.path.append(str(Path(__file__).parent.parent))

from retrieval.retrieval import retrieval
from tools.qdrant_filter import extract_relevant_clause_point

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger("evaluate_retrieval")


def is_match(chunk_metadata: dict, gt_item: dict) -> bool:
    """Check whether a retrieved chunk matches a ground-truth item."""
    doc_short_name = chunk_metadata.get("document_short_name", "")
    gt_doc = gt_item.get("document", "")

    clean_doc_short = str(doc_short_name).lower().replace("/", "_").replace("đ", "d")
    clean_gt_doc = str(gt_doc).lower().replace("/", "_").replace("đ", "d")

    # Document matching logic
    doc_match = (
        ("168" in clean_doc_short and "2024" in clean_doc_short)
        or (clean_gt_doc in clean_doc_short)
        or (clean_doc_short in clean_gt_doc)
        or not gt_doc
        or not doc_short_name
    )
    if not doc_match:
        return False

    # Article matching logic
    if chunk_metadata.get("article_number") != gt_item.get("article"):
        return False

    # Clause matching logic
    if chunk_metadata.get("clause_number") != gt_item.get("clause"):
        return False

    # Point matching logic
    gt_point = gt_item.get("point")
    if gt_point is not None:
        chunk_point = chunk_metadata.get("point")
        if chunk_point is None or str(chunk_point).strip().lower() != str(gt_point).strip().lower():
            return False

    return True


def _get_doc_key(doc) -> tuple:
    """Extract a unique key from metadata to avoid duplicates in document lists."""
    meta = getattr(doc, "metadata", {})
    return (
        meta.get("document_short_name"),
        meta.get("article_number"),
        meta.get("clause_number"),
        meta.get("point"),
    )


def compute_retrieval_metrics(docs: list, gt_items: list[dict], k_values=(3, 5, 10)) -> dict:
    """Compute Initial Retrieval metrics: MRR, Recall@K, and NDCG@K."""
    results = {}
    if not gt_items:
        results["mrr"] = 0.0
        for k in k_values:
            results[f"recall@{k}"] = 0.0
            results[f"ndcg@{k}"] = 0.0
        return results

    rel_flags = [
        any(is_match(getattr(doc, "metadata", {}), gt) for gt in gt_items)
        for doc in docs
    ]

    # Calculate Reciprocal Rank (MRR)
    first_rel_idx = next((i for i, rel in enumerate(rel_flags) if rel), None)
    results["mrr"] = 1.0 / (first_rel_idx + 1) if first_rel_idx is not None else 0.0

    # Calculate Recall@K and NDCG@K
    for k in k_values:
        top_k_docs = docs[:k]

        # Recall@K: Number of unique GT items matched in top K / total GT items
        matched_gt_indices = {
            gt_idx
            for gt_idx, gt in enumerate(gt_items)
            for doc in top_k_docs
            if is_match(getattr(doc, "metadata", {}), gt)
        }
        recall = len(matched_gt_indices) / len(gt_items)

        # NDCG@K
        dcg = sum(
            1.0 / math.log2(i + 2)
            for i, rel in enumerate(rel_flags[:k])
            if rel
        )
        idcg = sum(
            1.0 / math.log2(i + 2)
            for i in range(min(k, len(gt_items)))
        )
        ndcg = dcg / idcg if idcg > 0 else 0.0

        results[f"recall@{k}"] = round(recall, 4)
        results[f"ndcg@{k}"] = round(ndcg, 4)

    results["mrr"] = round(results["mrr"], 4)
    return results


def compute_expansion_metrics(retrieved_docs: list, combined_docs: list, gt_items: list[dict]) -> dict:
    """Compute Expansion metrics: final_recall (Recall@ALL) and rescue_rate."""
    total_gt = len(gt_items)
    if total_gt == 0:
        return {
            "final_recall": 0.0,
            "rescue_rate": 0.0
        }

    # 1. Determine ground-truth items matched by initial retrieval
    initial_matched_gt = {
        gt_idx
        for gt_idx, gt in enumerate(gt_items)
        for doc in retrieved_docs
        if is_match(getattr(doc, "metadata", {}), gt)
    }

    # 2. Determine ground-truth items matched by combined (expanded) docs
    final_matched_gt = {
        gt_idx
        for gt_idx, gt in enumerate(gt_items)
        for doc in combined_docs
        if is_match(getattr(doc, "metadata", {}), gt)
    }

    # 3. Compute Final Recall (Recall@ALL)
    final_recall = len(final_matched_gt) / total_gt

    # 4. Compute Rescue Rate
    initial_missed_gt = set(range(total_gt)) - initial_matched_gt
    rescued_gt = final_matched_gt - initial_matched_gt

    if len(initial_missed_gt) > 0:
        rescue_rate = len(rescued_gt) / len(initial_missed_gt)
    else:
        # Initial retrieval found all ground-truth items, no items needed rescuing
        rescue_rate = 0.0

    return {
        "final_recall": round(final_recall, 4),
        "rescue_rate": round(rescue_rate, 4),
    }


def evaluate_query(question: str, gt_items: list[dict], k_values=(1, 3, 5)) -> dict:
    """Execute retrieval, apply document expansion, and evaluate both stages."""
    # 1. Initial Retrieval
    retrieved_docs = retrieval(question)

    # 2. Document Expansion & Deduplication
    combined_docs = []
    seen_keys = set()

    for doc in retrieved_docs:
        doc_key = _get_doc_key(doc)
        if doc_key not in seen_keys:
            seen_keys.add(doc_key)
            combined_docs.append(doc)

        # Call reference expansion tool
        try:
            metadata = getattr(doc, "metadata", {})
            article_raw = metadata.get("article_number")
            clause_raw = metadata.get("clause_number")

            article_number = int(article_raw) if article_raw is not None else None
            clause = int(clause_raw) if clause_raw is not None else None
            point = metadata.get("point") if metadata.get("is_point") else None

            if (not article_number) and (not clause) and (not point):
                continue

            extracted = extract_relevant_clause_point(
                article=article_number,
                clause=clause,
                point=point
            )
            if extracted:
                for rel_doc in extracted:
                    rel_key = _get_doc_key(rel_doc)
                    if rel_key not in seen_keys:
                        seen_keys.add(rel_key)
                        combined_docs.append(rel_doc)
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Metadata extraction warning for document: {e}")
        except Exception as e:
            logger.error(f"Unexpected error extracting clause/point: {e}", exc_info=True)

    # 3. Calculate Metrics
    retrieval_metrics = compute_retrieval_metrics(retrieved_docs, gt_items, k_values=k_values)
    expansion_metrics = compute_expansion_metrics(retrieved_docs, combined_docs, gt_items)

    return {
        "question": question,
        "retrieval_metrics": retrieval_metrics,
        "expansion_metrics": expansion_metrics,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate RAG Retrieval and Expansion metrics.")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="data/processed/evals_168_2024.json",
        help="Path to evaluation dataset file (JSON)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="evaluation/evaluation_results.json",
        help="Path to save output evaluation report",
    )
    args = parser.parse_args()

    eval_file_path = Path(args.input)
    if not eval_file_path.exists():
        logger.error(f"Evaluation dataset file not found: {eval_file_path}")
        return

    logger.info(f"Loading evaluation dataset from: {eval_file_path}")
    with open(eval_file_path, "r", encoding="utf-8") as f:
        evals = json.load(f)

    logger.info(f"Starting evaluation on {len(evals)} queries...")

    k_values = (1,3,5)
    retrieval_keys = ["mrr"] + [f"recall@{k}" for k in k_values] + [f"ndcg@{k}" for k in k_values]
    expansion_keys = ["final_recall", "rescue_rate"]

    retrieval_sums = {k: 0.0 for k in retrieval_keys}
    expansion_sums = {k: 0.0 for k in expansion_keys}

    detailed_results = []

    for idx, item in enumerate(evals):
        question = item["question"]
        gt_items = item.get("retrieve_items", [])

        logger.info(f"[{idx + 1}/{len(evals)}] Evaluating query: '{question}'")
        res = evaluate_query(question, gt_items, k_values=k_values)

        for k in retrieval_keys:
            retrieval_sums[k] += res["retrieval_metrics"][k]
        for k in expansion_keys:
            expansion_sums[k] += res["expansion_metrics"][k]

        detailed_results.append(res)

    num_queries = len(evals)

    avg_retrieval_metrics = (
        {k: round(retrieval_sums[k] / num_queries, 4) for k in retrieval_keys}
        if num_queries > 0
        else {k: 0.0 for k in retrieval_keys}
    )
    avg_expansion_metrics = (
        {k: round(expansion_sums[k] / num_queries, 4) for k in expansion_keys}
        if num_queries > 0
        else {k: 0.0 for k in expansion_keys}
    )

    summary = {
        "total_queries": num_queries,
        "retrieval_metrics": avg_retrieval_metrics,
        "expansion_metrics": avg_expansion_metrics,
    }

    report = {
        "summary": summary,
        "results": detailed_results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info("=== EVALUATION REPORT SUMMARY ===")
    logger.info(f"Total Queries Evaluated: {num_queries}")
    logger.info("--- Initial Retrieval Metrics ---")
    for k, v in avg_retrieval_metrics.items():
        logger.info(f"  {k}: {v:.4f}")

    logger.info("--- Expansion Metrics ---")
    for k, v in avg_expansion_metrics.items():
        logger.info(f"  {k}: {v:.4f}")

    logger.info(f"Report successfully written to: {output_path}")


if __name__ == "__main__":
    main()
    # python -m evaluation.evaluate --input evaluation/data/evals_168_2024.json --output evaluation/result/evaluation_results.json