import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.rate_limit_retry import (  # noqa: E402
    run_with_rate_limit_retry,
)


RateLimitError = type(
    "RateLimitError",
    (Exception,),
    {},
)


class RateLimitRetryTests(unittest.TestCase):

    @patch("app.services.rate_limit_retry.sleep")
    def test_retries_rate_limit_using_provider_delay(
        self,
        mock_sleep,
    ):
        calls = {"count": 0}

        def operation():
            calls["count"] += 1
            if calls["count"] == 1:
                raise RateLimitError(
                    "Rate limit reached. Please try again in 20.5s."
                )
            return "ok"

        result = run_with_rate_limit_retry(
            operation,
            max_retries=2,
            fallback_seconds=25.0,
        )

        self.assertEqual(result, "ok")
        self.assertEqual(calls["count"], 2)
        mock_sleep.assert_called_once_with(21.5)

    @patch("app.services.rate_limit_retry.sleep")
    def test_uses_fallback_when_retry_delay_is_missing(
        self,
        mock_sleep,
    ):
        calls = {"count": 0}

        def operation():
            calls["count"] += 1
            if calls["count"] == 1:
                raise RateLimitError(
                    "Rate limit reached."
                )
            return 42

        result = run_with_rate_limit_retry(
            operation,
            max_retries=1,
            fallback_seconds=9.0,
        )

        self.assertEqual(result, 42)
        mock_sleep.assert_called_once_with(9.0)

    @patch("app.services.rate_limit_retry.sleep")
    def test_non_rate_limit_error_is_not_retried(
        self,
        mock_sleep,
    ):
        def operation():
            raise ValueError("bad request")

        with self.assertRaises(ValueError):
            run_with_rate_limit_retry(
                operation,
                max_retries=3,
            )

        mock_sleep.assert_not_called()

    @patch("app.services.rate_limit_retry.sleep")
    def test_stops_after_retry_budget(self, mock_sleep):
        def operation():
            raise RateLimitError(
                "Please try again in 1s."
            )

        with self.assertRaises(RateLimitError):
            run_with_rate_limit_retry(
                operation,
                max_retries=2,
            )

        self.assertEqual(
            mock_sleep.call_count,
            2,
        )


if __name__ == "__main__":
    unittest.main()
