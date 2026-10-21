import logging
from typing import Optional
from urllib.parse import urlparse

import requests
from logger import log_event

logger = logging.getLogger(__name__)

# Healthchecks.io accepts up to 100 KB; the run summary is far smaller
MAX_BODY_CHARS = 10_000


def ping(
    url: Optional[str],
    signal: str = "",
    body: Optional[str] = None,
    timeout: int = 10
) -> bool:
    """
    Pings a Healthchecks.io check. signal: "start", "" (success) or "fail".
    Never raises: a monitoring failure must not break the backup.
    The URL is not logged because its UUID is what authorizes the ping.
    """
    if not url:
        return False

    ping_url = f"{url.rstrip('/')}/{signal}" if signal else url.rstrip("/")

    try:
        if body is None:
            response = requests.get(ping_url, timeout=timeout)
        else:
            response = requests.post(
                ping_url,
                data=body[:MAX_BODY_CHARS].encode("utf-8"),
                timeout=timeout
            )
        response.raise_for_status()

    except Exception as exc:
        # requests puts the URL in its messages, so no traceback here
        log_event(
            logger, "healthcheck.ping.failed", logging.WARNING,
            signal=signal or "success",
            error=_redact(str(exc), url),
            error_type=type(exc).__name__
        )
        return False

    log_event(
        logger, "healthcheck.ping.ok",
        signal=signal or "success", status_code=response.status_code
    )
    return True


def _redact(message: str, url: str) -> str:
    check_path = urlparse(url).path.strip("/")
    if not check_path:
        return message
    return message.replace(check_path, "<redacted>")
