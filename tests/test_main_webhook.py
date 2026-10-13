"""Unit tests for GitHub webhook handler in main.py."""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import json
from main import github_webhook_handler, _process_github_push_payload


class TestMainWebhook(unittest.IsolatedAsyncioTestCase):
    def test_webhook_invalid_signature(self):
        """Webhooks with bad signatures return 401 Unauthorized."""
        with patch("webhook_security.verify_github_signature", return_value=False):
            code, msg = github_webhook_handler(b'{"action": "test"}', {"X-Hub-Signature-256": "bad"})
            self.assertEqual(code, 401)
            self.assertEqual(msg, "Invalid webhook signature")

    def test_webhook_ping_event(self):
        """GitHub ping event returns 200 pong."""
        with patch("webhook_security.verify_github_signature", return_value=True):
            code, msg = github_webhook_handler(b'{}', {"X-GitHub-Event": "ping"})
            self.assertEqual(code, 200)
            self.assertEqual(msg, "pong")

    @patch("main.bot")
    def test_webhook_push_event_scheduled(self, mock_bot):
        """GitHub push event dispatches payload to event loop."""
        mock_bot.loop = MagicMock()
        mock_bot.loop.is_closed.return_value = False

        payload = {
            "ref": "refs/heads/main",
            "repository": {"name": "repo", "owner": {"login": "owner"}},
            "commits": [{"id": "c123456", "message": "feat: hackathon ready"}],
        }
        body = json.dumps(payload).encode("utf-8")

        def _mock_schedule(coro, loop):
            coro.close()
            return MagicMock()

        with patch("webhook_security.verify_github_signature", return_value=True), \
             patch("asyncio.run_coroutine_threadsafe", side_effect=_mock_schedule):
            code, msg = github_webhook_handler(body, {"X-GitHub-Event": "push"})
            self.assertEqual(code, 200)
            self.assertEqual(msg, "Push event received and scheduled")

    @patch("main.get_setting")
    @patch("main.bot")
    @patch("repo_updates.post_push_commits_from_payload")
    async def test_process_push_payload_posts_commits(self, mock_post, mock_bot, mock_get_setting):
        """Verifies _process_github_push_payload finds channel and calls post_push_commits_from_payload."""
        mock_get_setting.return_value = "8888"
        mock_channel = MagicMock()
        mock_channel.name = "updates"
        mock_bot.get_channel.return_value = mock_channel
        mock_post.return_value = 1

        payload = {
            "ref": "refs/heads/main",
            "repository": {"name": "awesome-hackathon", "owner": {"login": "team"}},
            "commits": [{"id": "abc1234", "message": "feat: initial commit"}],
        }

        await _process_github_push_payload(payload)

        mock_post.assert_awaited_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["target_channel"], mock_channel)
        self.assertEqual(kwargs["repo_owner"], "team")
        self.assertEqual(kwargs["repo_name"], "awesome-hackathon")
        self.assertEqual(kwargs["branch"], "main")


if __name__ == "__main__":
    unittest.main()
