"""Integration-ish unit tests for webhook helpers.

These tests intentionally avoid importing the full bot (main.py) to keep them
fast and environment-agnostic.
"""

import hashlib
import hmac
import unittest

from webhook_security import verify_github_signature


class TestWebhookSignature(unittest.TestCase):
    def test_valid_signature(self):
        secret = "test-secret"
        body = b"{\"hello\": \"world\"}"
        sig = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        self.assertTrue(
            verify_github_signature(
                raw_body=body,
                signature_header=sig,
                secret=secret,
                require_secret=True,
            )
        )

    def test_invalid_signature(self):
        secret = "test-secret"
        body = b"{}"
        sig = "sha256=" + ("0" * 64)
        self.assertFalse(
            verify_github_signature(
                raw_body=body,
                signature_header=sig,
                secret=secret,
                require_secret=True,
            )
        )

    def test_missing_signature_header_when_required(self):
        self.assertFalse(
            verify_github_signature(
                raw_body=b"{}",
                signature_header=None,
                secret="test-secret",
                require_secret=True,
            )
        )

    def test_secret_not_required_allows_missing(self):
        self.assertTrue(
            verify_github_signature(
                raw_body=b"{}",
                signature_header=None,
                secret="",
                require_secret=False,
            )
        )


if __name__ == "__main__":
    unittest.main()
