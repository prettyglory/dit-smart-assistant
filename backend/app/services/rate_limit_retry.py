from __future__ import annotations

import re
from time import sleep
from typing import Callable, TypeVar


T = TypeVar("T")

RETRY_SECONDS_PATTERN = re.compile(
    r"try again in\s+([0-9]+(?:\.[0-9]+)?)s",
    re.IGNORECASE,
)


def _retry_delay_seconds(
    error: Exception,
    fallback_seconds: float,
) -> float:
    match = RETRY_SECONDS_PATTERN.search(
        str(error)
    )

    if match:
        try:
            return max(
                1.0,
                float(match.group(1)) + 1.0,
            )
        except ValueError:
            pass

    return max(
        1.0,
        fallback_seconds,
    )


def run_with_rate_limit_retry(
    operation: Callable[[], T],
    *,
    max_retries: int = 3,
    fallback_seconds: float = 25.0,
    label: str = "Groq request",
) -> T:
    """Retry Groq TPM rate-limit failures while preserving other errors.

    The helper intentionally retries only errors whose class name is
    ``RateLimitError``. Prompt-size/API validation failures are not retried.
    """

    attempts = 0

    while True:
        try:
            return operation()

        except Exception as error:
            if type(error).__name__ != "RateLimitError":
                raise

            if attempts >= max_retries:
                raise

            attempts += 1
            delay = _retry_delay_seconds(
                error,
                fallback_seconds,
            )

            print(
                f"{label} hit the Groq rate limit. "
                f"Retry {attempts}/{max_retries} after {delay:.1f}s."
            )
            sleep(delay)
