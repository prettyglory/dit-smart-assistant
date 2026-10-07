from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.agent_evaluation import (  # noqa: E402
    evaluate_live_result,
    evaluate_offline_case,
    load_eval_cases,
    summarize_results,
)
from app.services.rate_limit_retry import (  # noqa: E402
    run_with_rate_limit_retry,
)


def _print_result(result: dict) -> None:
    marker = "PASS" if result.get("passed") else "FAIL"
    print(
        f"[{marker}] {result.get('id', '')} "
        f"({result.get('category', 'uncategorized')})"
    )

    if not result.get("passed"):
        print(
            json.dumps(
                result.get("checks", {}),
                indent=2,
                sort_keys=True,
            )
        )


def run_offline(cases: list[dict]) -> list[dict]:
    results = []

    for case in cases:
        result = evaluate_offline_case(
            case
        )
        results.append(result)
        _print_result(result)

    return results


def run_live(cases: list[dict]) -> list[dict]:
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError(
            "GROQ_API_KEY is required for --mode live."
        )

    from app.services.execution_trace import agent_traces
    from app.services.traced_agent_service import run_traced_dit_agent

    results = []

    for case in cases:
        case_id = case.get(
            "id",
            "case",
        )

        def execute_case():
            return run_traced_dit_agent(
                question=case.get(
                    "question",
                    "",
                ),
                student_state=case.get(
                    "student_state",
                    {},
                ),
                session_id=(
                    "eval-"
                    + case_id
                ),
            )

        answer, _, trace_id = run_with_rate_limit_retry(
            execute_case,
            max_retries=3,
            fallback_seconds=25.0,
            label=f"Live eval {case_id}",
        )

        trace = agent_traces.get(
            trace_id
        ) or {}

        result = evaluate_live_result(
            case=case,
            answer=answer,
            trace=trace,
        )
        results.append(result)
        _print_result(result)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate DIT Smart Assistant planning, tooling and grounding safety."
        )
    )
    parser.add_argument(
        "--mode",
        choices=(
            "offline",
            "live",
        ),
        default="offline",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Optional path to a JSON evaluation dataset.",
    )

    args = parser.parse_args()

    cases = load_eval_cases(
        args.dataset
    )

    if args.mode == "live":
        results = run_live(cases)
    else:
        results = run_offline(cases)

    summary = summarize_results(
        results
    )

    print("\nEvaluation summary")
    print(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
