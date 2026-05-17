from __future__ import annotations

from tools.diretest.core.harness import safe_delete


def safe_smoke_delete(*objects, max_attempts=3, max_retries=None, retry_delay=0.1, recurse=True):
    if max_retries is not None:
        max_attempts = max_retries

    failures = []
    for obj in reversed(list(objects or [])):
        ok, failure = safe_delete(obj, max_attempts=max_attempts, retry_delay=retry_delay, recurse=recurse)
        if not ok and failure:
            failures.append(failure)
    return failures
