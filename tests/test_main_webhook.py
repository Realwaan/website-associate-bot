"""Unit tests for GitHub webhook handler and bracket normalization in main.py."""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import json
from main import (
    github_webhook_handler,
    _process_github_push_payload,
    _process_github_pull_request_payload,
    _process_github_pr_review_payload,
    replay_dead_letter_event,
    _strip_leading_bracket_prefixes,
)


class TestMainWebhook(unittest.IsolatedAsyncioTestCase):
    def test_strip_leading_bracket_prefixes(self):
        """Strips single or stacked bracket tags cleanly."""
        self.assertEqual(_strip_leading_bracket_prefixes("[OPEN] Build Auth"), "Build Auth")
        self.assertEqual(_strip_leading_bracket_prefixes("[CRITICAL][OPEN] Build Auth"), "Build Auth")
        self.assertEqual(_strip_leading_bracket_prefixes("[PRIORITY] [IN PROGRESS] Fix API"), "Fix API")

    def test_webhook_invalid_signature(self):
        """Webhooks with bad signatures return 401 Unauthorized."""
        with patch("webhook_security.verify_github_signature", return_value=False):
            code, msg = github_webhook_handler(b'{"action": "test"}', {"X-Hub-Signature-256": "bad"})
            self.assertEqual(code, 401)
            self.assertEqual(msg, "Invalid webhook signature")

    def test_webhook_duplicate_delivery_ignored(self):
        """Duplicate X-GitHub-Delivery IDs are rejected safely as 200 duplicate ignored."""
        with patch("webhook_security.verify_github_signature", return_value=True), \
             patch("main.register_webhook_delivery", return_value=False):
            code, msg = github_webhook_handler(
                b'{}',
                {"X-GitHub-Event": "push", "X-GitHub-Delivery": "dup-delivery-123"},
            )
            self.assertEqual(code, 200)
            self.assertIn("Duplicate", msg)

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

    @patch("main.get_setting")
    @patch("main.bot")
    @patch("repo_updates.post_push_commits_from_payload")
    async def test_process_push_payload_ignores_deleted_branch(self, mock_post, mock_bot, mock_get_setting):
        """Branch deletion push events are ignored cleanly."""
        payload = {
            "deleted": True,
            "ref": "refs/heads/feat/old",
            "repository": {"name": "repo", "owner": {"login": "team"}},
            "commits": [{"id": "abc", "message": "unused"}],
        }
        await _process_github_push_payload(payload)
        mock_post.assert_not_called()

    @patch("main.bot")
    def test_webhook_pr_opened_and_review_scheduled(self, mock_bot):
        """Opened pull_request and submitted pull_request_review webhooks schedule handlers."""
        mock_bot.loop = MagicMock()
        mock_bot.loop.is_closed.return_value = False

        def _mock_schedule(coro, loop):
            coro.close()
            return MagicMock()

        pr_body = json.dumps({
            "action": "opened",
            "repository": {"name": "OTOG", "owner": {"login": "Realwaan"}},
            "pull_request": {"number": 19, "title": "feat: CAP-10 pay bills"},
        }).encode("utf-8")
        review_body = json.dumps({
            "action": "submitted",
            "repository": {"name": "OTOG", "owner": {"login": "Realwaan"}},
            "pull_request": {"number": 19, "title": "feat: CAP-10 pay bills"},
            "review": {"id": 55, "state": "approved", "body": "LGTM", "user": {"login": "qa"}},
        }).encode("utf-8")

        with patch("webhook_security.verify_github_signature", return_value=True), \
             patch("asyncio.run_coroutine_threadsafe", side_effect=_mock_schedule):
            code1, msg1 = github_webhook_handler(pr_body, {"X-GitHub-Event": "pull_request"})
            code2, msg2 = github_webhook_handler(review_body, {"X-GitHub-Event": "pull_request_review"})

        self.assertEqual(code1, 200)
        self.assertIn("opened", msg1)
        self.assertEqual(code2, 200)
        self.assertIn("review", msg2.lower())

    @patch("main.get_setting")
    @patch("main.bot")
    @patch("repo_updates.post_pull_request_from_payload", new_callable=AsyncMock)
    @patch("repo_updates.post_pr_review_from_payload", new_callable=AsyncMock)
    async def test_pr_and_review_payload_processors_and_dead_letter_replay(
        self, mock_review_post, mock_pr_post, mock_bot, mock_get_setting
    ):
        """PR/review processors and replay_dead_letter_event dispatch directly to card posters."""
        mock_get_setting.return_value = "8888"
        mock_channel = MagicMock()
        mock_channel.name = "project-updates"
        mock_bot.get_channel.return_value = mock_channel
        mock_pr_post.return_value = True
        mock_review_post.return_value = True

        pr_payload = {
            "action": "closed",
            "repository": {"name": "OTOG", "owner": {"login": "Realwaan"}},
            "pull_request": {"number": 7, "title": "feat: CAP-07 wallet", "merged": True},
            "sender": {"login": "Realwaan"},
        }
        review_payload = {
            "action": "submitted",
            "repository": {"name": "OTOG", "owner": {"login": "Realwaan"}},
            "pull_request": {"number": 7, "title": "feat: CAP-07 wallet"},
            "review": {"id": 88, "state": "changes_requested", "body": "Check null balance", "user": {"login": "qa"}},
        }

        await _process_github_pull_request_payload(pr_payload)
        await _process_github_pr_review_payload(review_payload)
        await replay_dead_letter_event("pull_request", pr_payload, "dl-1")
        await replay_dead_letter_event("pull_request_review", review_payload, "dl-2")

        self.assertEqual(mock_pr_post.await_count, 2)
        self.assertEqual(mock_review_post.await_count, 2)


if __name__ == "__main__":
    unittest.main()
