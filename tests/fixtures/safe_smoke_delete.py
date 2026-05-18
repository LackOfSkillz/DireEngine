from __future__ import annotations

from tools.diretest.core.harness import _is_canonical_protected
from tools.diretest.core.harness import _log_canonical_protection
from tools.diretest.core.harness import safe_delete


class SafeSmokeDeleteResult(list):
    def __init__(self):
        super().__init__()
        self.deleted_count = 0
        self.filtered_count = 0


def safe_smoke_delete(*objects, max_attempts=3, max_retries=None, retry_delay=0.1, recurse=True):
    if max_retries is not None:
        max_attempts = max_retries

    failures = SafeSmokeDeleteResult()
    for obj in reversed(list(objects or [])):
        if _is_canonical_protected(obj):
            _log_canonical_protection(obj, "safe_smoke_delete")
            failures.filtered_count += 1
            continue
        ok, failure = safe_delete(obj, max_attempts=max_attempts, retry_delay=retry_delay, recurse=recurse)
        if ok:
            failures.deleted_count += 1
        if not ok and failure:
            failures.append(failure)
    return failures
