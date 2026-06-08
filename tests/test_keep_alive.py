"""Unit tests for the keep-alive server."""
import unittest
from unittest.mock import MagicMock
from keep_alive import app, set_github_webhook_handler, _github_webhook_handler


class TestKeepAliveServer(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['PROPAGATE_EXCEPTIONS'] = False
        self.client = app.test_client()
        # Clean up webhook handler before each test
        set_github_webhook_handler(None)

    def test_security_headers_are_present(self):
        """Verify that HTTP security headers are added to the responses."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.headers.get('X-Frame-Options'), 'DENY')
        self.assertEqual(response.headers.get('X-XSS-Protection'), '1; mode=block')
        self.assertEqual(
            response.headers.get('Content-Security-Policy'),
            "default-src 'none'; frame-ancestors 'none'"
        )

    def test_root_get_alive(self):
        """Verify GET to root returns 'Bot is alive!'."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode('utf-8'), "Bot is alive!")

    def test_health_check(self):
        """Verify health check returns ok."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode('utf-8'), "ok")

    def test_payload_size_limit_ok(self):
        """Verify standard sized payload is accepted by webhook endpoint."""
        mock_handler = MagicMock(return_value=(202, "Webhook accepted"))
        set_github_webhook_handler(mock_handler)
        
        response = self.client.post(
            '/webhook/github',
            data='{"ref": "refs/heads/main"}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 202)
        mock_handler.assert_called_once()

    def test_payload_size_limit_exceeded(self):
        """Verify payload exceeding the limit is rejected with 413."""
        # We must set a handler so the route doesn't exit early with 503
        set_github_webhook_handler(MagicMock())
        # Generate data larger than 10MB (e.g., 10.5 MB)
        oversized_data = b"a" * (10 * 1024 * 1024 + 1024)
        
        response = self.client.post(
            '/webhook/github',
            data=oversized_data,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 413)
        # Check custom JSON message is returned
        json_data = response.get_json()
        self.assertFalse(json_data['ok'])
        self.assertIn("Payload too large", json_data['message'])

    def test_internal_server_error_handler(self):
        """Verify internal server errors are caught and return custom JSON."""
        mock_handler = MagicMock(side_effect=Exception("Database failure"))
        set_github_webhook_handler(mock_handler)

        response = self.client.post(
            '/webhook/github',
            data='{"test": "data"}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 500)
        json_data = response.get_json()
        self.assertFalse(json_data['ok'])
        self.assertEqual(json_data['message'], "An internal server error occurred.")


if __name__ == '__main__':
    unittest.main()
