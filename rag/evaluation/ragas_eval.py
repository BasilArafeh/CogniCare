"""Evaluate CogniCare RAG with RAGAS (context precision & recall).

Run from repo root: ``python -m rag.evaluation.ragas_eval``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
from pathlib import Path
from typing import Any, TypedDict

from openai import OpenAI

import rag.config  # noqa: F401 — loads repo-root `.env` (OPENAI_API_KEY, DATABASE_URL, …)
from rag.rag_turn import run_rag_turn
from rag.retrieval import RetrievalTarget

from ragas import aevaluate
from ragas.dataset_schema import EvaluationDataset, EvaluationResult
from ragas.llms import llm_factory
from ragas.metrics import ContextPrecision, ContextRecall


logger = logging.getLogger(__name__)

_EVAL_DIR = Path(__file__).resolve().parent
_RESULTS_PATH = _EVAL_DIR / "results.json"
_GROUND_TRUTH_MEDICAL = _EVAL_DIR / "ground_truths_medical.json"
_GROUND_TRUTH_MEDICATIONS = _EVAL_DIR / "ground_truths_medications.json"

JUDGE_MODEL = "gpt-4o-mini"


class GroundTruthRow(TypedDict, total=False):
    question: str
    ground_truth: str
    retrieval_target: str
    medication_search_term: str | None


class SampleEnvelope(TypedDict, total=False):
    question: str
    retrieval_target: str
    medication_search_term: str | None
    ground_truth: str
    answer: str
    contexts: list[str]


def _load_json_rows(path: Path) -> list[GroundTruthRow]:
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError(f"Expected a JSON array in {path}")
    return raw


def _target_from_record(row: GroundTruthRow) -> RetrievalTarget:
    key = (row.get("retrieval_target") or "").strip().lower()
    mapping = {"medical": RetrievalTarget.MEDICAL, "medications": RetrievalTarget.MEDICATIONS}
    out = mapping.get(key)
    if out is None:
        raise ValueError(f"Unsupported retrieval_target: {key!r} (row={row})")
    return out


def _contexts_from_sources(sources: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for s in sources:
        txt = (s.get("content") or s.get("text") or "").strip()
        if txt:
            out.append(txt)
    return out


def _json_default(obj: Any) -> Any:
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


async def gather_samples() -> tuple[list[dict[str, Any]], list[SampleEnvelope]]:
    """Run the pipeline over all ground-truth rows; build RAGAS rows + envelopes."""
    ragas_rows: list[dict[str, Any]] = []
    envelopes: list[SampleEnvelope] = []

    files_and_labels: tuple[tuple[Path, str], ...] = (
        (_GROUND_TRUTH_MEDICAL, "medical"),
        (_GROUND_TRUTH_MEDICATIONS, "medications"),
    )

    for path, file_label in files_and_labels:
        rows = _load_json_rows(path)
        for i, row in enumerate(rows):
            question = row["question"]
            ground_truth = row["ground_truth"]
            target = _target_from_record(row)
            med_term = row.get("medication_search_term")
            med_kw = None if med_term is None else str(med_term).strip() or None

            logger.info(
                "rag turn [%s %s/%s] target=%s med_term=%s q=%s",
                file_label,
                i + 1,
                len(rows),
                target.value,
                med_kw,
                question[:120] + ("…" if len(question) > 120 else ""),
            )

            if target == RetrievalTarget.MEDICATIONS:
                result = await run_rag_turn(
                    question,
                    target,
                    medication_search_term=med_kw,
                )
            else:
                result = await run_rag_turn(question, target)

            contexts = _contexts_from_sources(result.sources)
            if not contexts:
                contexts = [""]
                logger.warning("No chunk text found for row; using empty context placeholder.")

            ragas_rows.append(
                {
                    "user_input": question,
                    "retrieved_contexts": contexts,
                    "reference": ground_truth,
                    "response": result.answer,
                }
            )

            envelopes.append(
                {
                    "question": question,
                    "retrieval_target": target.value,
                    "medication_search_term": med_kw,
                    "ground_truth": ground_truth,
                    "answer": result.answer,
                    "contexts": [c for c in contexts if c],
                }
            )

    return ragas_rows, envelopes


def _mean(vals: list[float]) -> float | None:
    clean = [v for v in vals if not (isinstance(v, float) and math.isnan(v))]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _print_report(
    eval_result: EvaluationResult,
    envelopes: list[SampleEnvelope],
    cp_key: str,
    cr_key: str,
) -> dict[str, Any]:
    scores = eval_result.scores
    cp_all: list[float] = []
    cr_all: list[float] = []

    medical_cp: list[float] = []
    medical_cr: list[float] = []
    meds_cp: list[float] = []
    meds_cr: list[float] = []

    rows_out: list[dict[str, Any]] = []

    for env, score_row in zip(envelopes, scores):
        cp = score_row.get(cp_key)
        cr = score_row.get(cr_key)

        tgt = env["retrieval_target"]
        if isinstance(cp, (int, float)):
            cp_f = float(cp)
            cp_all.append(cp_f)
            if tgt == "medical":
                medical_cp.append(cp_f)
            else:
                meds_cp.append(cp_f)
        else:
            cp_f = float("nan")

        if isinstance(cr, (int, float)):
            cr_f = float(cr)
            cr_all.append(cr_f)
            if tgt == "medical":
                medical_cr.append(cr_f)
            else:
                meds_cr.append(cr_f)
        else:
            cr_f = float("nan")

        line = (
            f"[{tgt}] precision={cp_f:.4f} recall={cr_f:.4f} | "
            f"Q: {env['question']}"
        )
        print(line)

        rows_out.append({**dict(env), "context_precision": cp_f, "context_recall": cr_f})

    avg_cp = _mean(cp_all)
    avg_cr = _mean(cr_all)

    summary: dict[str, Any] = {
        "overall": {"avg_context_precision": avg_cp, "avg_context_recall": avg_cr},
        "medical": {
            "avg_context_precision": _mean(medical_cp),
            "avg_context_recall": _mean(medical_cr),
            "count": len(medical_cp),
        },
        "medications": {
            "avg_context_precision": _mean(meds_cp),
            "avg_context_recall": _mean(meds_cr),
            "count": len(meds_cp),
        },
        "per_question": rows_out,
        "metric_columns": {"context_precision": cp_key, "context_recall": cr_key},
    }

    print()
    print("=== RAGAS summary ===")
    print(f"Judge model: {JUDGE_MODEL}")
    if avg_cp is not None:
        print(f"Average ContextPrecision (all): {avg_cp:.4f}")
    else:
        print("Average ContextPrecision (all): n/a")
    if avg_cr is not None:
        print(f"Average ContextRecall (all): {avg_cr:.4f}")
    else:
        print("Average ContextRecall (all): n/a")

    print()
    print("--- By retrieval_target ---")
    for label, blk in ("medical", summary["medical"]), ("medications", summary["medications"]):
        ap, ar = blk["avg_context_precision"], blk["avg_context_recall"]
        pc = blk["count"]
        ap_s = f"{ap:.4f}" if ap is not None else "n/a"
        ar_s = f"{ar:.4f}" if ar is not None else "n/a"
        print(f"{label}: n={pc} avg precision={ap_s} avg recall={ar_s}")

    return summary


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing; set it in cognicare root `.env`.")

    ragas_rows, envelopes = await gather_samples()

    dataset = EvaluationDataset.from_list(ragas_rows)

    judge = llm_factory(JUDGE_MODEL, client=OpenAI())
    metrics = [ContextPrecision(), ContextRecall()]
    cp_inst, cr_inst = metrics
    cp_key = cp_inst.name  # context_precision
    cr_key = cr_inst.name  # context_recall

    logger.info("Running RAGAS evaluate on %s rows…", len(ragas_rows))
    # Use async entry so we do not nest ``asyncio.run()`` (sync ``evaluate()`` would).
    eval_result: EvaluationResult = await aevaluate(
        dataset,
        metrics=metrics,
        llm=judge,
        show_progress=True,
    )

    summary = _print_report(eval_result, envelopes, cp_key, cr_key)

    payload = {
        "config": {"judge_model": JUDGE_MODEL, "metrics": [cp_key, cr_key]},
        "ragas_aggregate_repr": repr(eval_result),
        "summary": summary,
        "scores": eval_result.scores,
    }

    _RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _RESULTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=_json_default)
    logger.info("Wrote full results to %s", _RESULTS_PATH)


if __name__ == "__main__":
    asyncio.run(main())
