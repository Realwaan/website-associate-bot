"""Security helpers for webhook signature validation."""
from __future__ import annotations

import hmac
import hashlib


def verify_github_signature(
    *,
    raw_body: bytes,
    signature_header: str | None,
    secret: str,
    require_secret: bool = True,
) -> bool:
    """Verify X-Hub-Signature-256 against request body."""
    if not secret:
        return not require_secret
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
