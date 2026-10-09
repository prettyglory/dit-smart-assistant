from __future__ import annotations

import json
from pathlib import Path

from app.services.task_planner import build_request_plan


DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[2]
    / "evals"
    / "dit_agent_cases.json"
)


def load_eval_cases(
    dataset_path: str | Path | None = None,
) -> list[dict]:
    path = Path(
        dataset_path
        or DEFAULT_DATASET_PATH
    )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        cases = json.load(file)

    if not isinstance(cases, list):
        raise ValueError(
            "Evaluation dataset must contain a JSON list."
        )

    return cases


def _ready_tools_from_plan(
    plan: dict,
) -> set[str]:
    tools: set[str] = set()

    for task in plan.get(
        "tasks",
        [],
    ):
        if not task.get(
            "ready",
            True,
        ):
            continue

        tools.update(
            task.get(
                "required_tools",
                [],
            )
        )

    return tools


def evaluate_offline_case(
    case: dict,
) -> dict:
    plan = build_request_plan(
        question=case.get(
            "question",
            "",
        ),
        student_state=case.get(
            "student_state",
            {},
        ),
    )

    actual_task_ids = [
        task.get("id", "")
        for task in plan.get(
            "tasks",
            [],
        )
    ]

    expected_task_ids = case.get(
        "expected_plan_tasks",
        [],
    )

    actual_ready_tools = _ready_tools_from_plan(
        plan
    )

    required_tools = set(
        case.get(
            "required_tools",
            [],
        )
    )

    forbidden_tools = set(
        case.get(
            "forbidden_tools",
            [],
        )
    )

    checks = {
        "task_order": (
            actual_task_ids
            == expected_task_ids
        ),
        "required_tools": (
            required_tools
            <= actual_ready_tools
        ),
        "forbidden_tools": not (
            forbidden_tools
            & actual_ready_tools
        ),
    }

    return {
        "id": case.get("id", ""),
        "category": case.get(
            "category",
            "uncategorized",
        ),
        "passed": all(
            checks.values()
        ),
        "checks": checks,
        "actual_task_ids": actual_task_ids,
        "actual_ready_tools": sorted(
            actual_ready_tools
        ),
    }


def evaluate_live_result(
    case: dict,
    answer: str,
    trace: dict,
) -> dict:
    events = trace.get(
        "events",
        [],
    )

    attempted_tools = {
        event.get("tool_name")
        for event in events
        if event.get("type")
        in {
            "tool_call",
            "dependency_block",
        }
        and event.get("tool_name")
    }

    successful_tools = {
        event.get("tool_name")
        for event in events
        if event.get("type") == "tool_call"
        and event.get("success") is True
        and event.get("tool_name")
    }

    required_tools = set(
        case.get(
            "required_tools",
            [],
        )
    )

    forbidden_tools = set(
        case.get(
            "forbidden_tools",
            [],
        )
    )

    normalized_answer = (
        answer
        or ""
    ).lower()

    required_answer_phrases = [
        phrase.lower()
        for phrase in case.get(
            "required_answer_phrases",
            [],
        )
    ]

    forbidden_answer_phrases = [
        phrase.lower()
        for phrase in case.get(
            "forbidden_answer_phrases",
            [],
        )
    ]

    min_sources = int(
        case.get(
            "min_sources",
            0,
        )
    )

    checks = {
        "completed": (
            trace.get("status")
            == "completed"
        ),
        "required_tools_attempted": (
            required_tools
            <= attempted_tools
        ),
        "forbidden_tools_absent": not (
            forbidden_tools
            & attempted_tools
        ),
        "required_tools_succeeded_or_blocked_safely": all(
            (
                tool in successful_tools
                or tool in attempted_tools
            )
            for tool in required_tools
        ),
        "minimum_sources": (
            int(
                trace.get(
                    "source_count",
                    0,
                )
            )
            >= min_sources
        ),
        "required_answer_phrases_present": all(
            phrase in normalized_answer
            for phrase in required_answer_phrases
        ),
        "forbidden_claims_absent": not any(
            phrase in normalized_answer
            for phrase in forbidden_answer_phrases
        ),
    }

    return {
        "id": case.get("id", ""),
        "category": case.get(
            "category",
            "uncategorized",
        ),
        "passed": all(
            checks.values()
        ),
        "checks": checks,
        "attempted_tools": sorted(
            attempted_tools
        ),
        "successful_tools": sorted(
            successful_tools
        ),
        "source_count": trace.get(
            "source_count",
            0,
        ),
    }


def summarize_results(
    results: list[dict],
) -> dict:
    total = len(results)
    passed = sum(
        1
        for result in results
        if result.get("passed")
    )

    by_category: dict[str, dict] = {}

    for result in results:
        category = result.get(
            "category",
            "uncategorized",
        )

        bucket = by_category.setdefault(
            category,
            {
                "total": 0,
                "passed": 0,
            },
        )

        bucket["total"] += 1

        if result.get("passed"):
            bucket["passed"] += 1

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": (
            round(
                passed / total,
                4,
            )
            if total
            else 1.0
        ),
        "by_category": by_category,
    }
