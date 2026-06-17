from collections import defaultdict, deque
from threading import Lock
from time import time

from fastapi import HTTPException, Request

UPLOAD_LIMIT = 3
UPLOAD_WINDOW_SECONDS = 60

_upload_attempts: defaultdict[str, deque[float]] = defaultdict(deque)
_upload_attempts_lock = Lock()


def _get_client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_hop = forwarded_for.split(",")[0].strip()
        if first_hop:
            return first_hop

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def enforce_upload_rate_limit(request: Request) -> None:
    """
    Allows up to 3 upload requests per client within a rolling 60-second window.
    """
    client_id = _get_client_identifier(request)
    current_time = time()
    window_start = current_time - UPLOAD_WINDOW_SECONDS

    with _upload_attempts_lock:
        attempts = _upload_attempts[client_id]

        while attempts and attempts[0] <= window_start:
            attempts.popleft()

        if not attempts:
            _upload_attempts.pop(client_id, None)
            attempts = _upload_attempts[client_id]

        if len(attempts) >= UPLOAD_LIMIT:
            retry_after_seconds = max(1, int(attempts[0] + UPLOAD_WINDOW_SECONDS - current_time))
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Upload rate limit exceeded. "
                    f"Only {UPLOAD_LIMIT} uploads are allowed per minute."
                ),
                headers={"Retry-After": str(retry_after_seconds)},
            )

        attempts.append(current_time)
