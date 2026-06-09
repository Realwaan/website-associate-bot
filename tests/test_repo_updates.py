import unittest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import discord

from repo_updates import fetch_new_commits, fetch_new_merged_prs, post_project_updates


class TestRepoUpdates(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_new_commits_pages_until_cursor(self):
        page1 = [{"sha": "s5"}, {"sha": "s4"}, {"sha": "s3"}]
        page2 = [{"sha": "s2"}, {"sha": "s1"}, {"sha": "s0"}]

        async def fake_get(url: str, token: str | None = None):
            if "page=1" in url:
                return page1
            if "page=2" in url:
                return page2
            return []

        with patch("repo_updates.github_get", new=fake_get):
            commits, newest_sha = await fetch_new_commits(
                api_base="https://api.github.com/repos/acme/demo",
                branch="main",
                last_sha="s1",
                token=None,
                first_run_limit=10,
                per_page=3,
                max_pages=4,
            )

        self.assertEqual([c["sha"] for c in commits], ["s5", "s4", "s3", "s2"])
        self.assertEqual(newest_sha, "s5")

    async def test_fetch_new_commits_first_run_uses_limit(self):
        page = [{"sha": "n3"}, {"sha": "n2"}, {"sha": "n1"}]

        async def fake_get(url: str, token: str | None = None):
            self.assertIn("per_page=2", url)
            return page[:2]

        with patch("repo_updates.github_get", new=fake_get):
            commits, newest_sha = await fetch_new_commits(
                api_base="https://api.github.com/repos/acme/demo",
                branch="main",
                last_sha=None,
                token=None,
                first_run_limit=2,
            )

        self.assertEqual([c["sha"] for c in commits], ["n3", "n2"])
        self.assertEqual(newest_sha, "n3")

    async def test_fetch_new_merged_prs(self):
        """Verify that fetch_new_merged_prs filters unmerged or older PRs correctly."""
        mock_prs = [
            {
                "number": 102,
                "merged_at": "2026-06-09T12:00:00Z",
                "title": "PR 102",
                "html_url": "https://github.com/acme/demo/pull/102",
                "user": {"login": "user1"},
            },
            {
                "number": 101,
                "merged_at": None,
                "title": "PR 101 (Not Merged)",
            },
            {
                "number": 100,
                "merged_at": "2026-06-09T10:00:00Z",
                "title": "PR 100",
                "html_url": "https://github.com/acme/demo/pull/100",
                "user": {"login": "user2"},
            },
        ]

        async def fake_get(url: str, token: str | None = None):
            return mock_prs

        with patch("repo_updates.github_get", new=fake_get):
            prs, newest_pr = await fetch_new_merged_prs(
                api_base="https://api.github.com/repos/acme/demo",
                last_pr_id=100,
                token=None,
            )

        # Should only return PR 102 since it's merged and number is > 100
        self.assertEqual(len(prs), 1)
        self.assertEqual(prs[0]["number"], 102)
        self.assertEqual(newest_pr, 102)

    async def test_post_project_updates_success_and_descriptions(self):
        """Verify post_project_updates sends expected embeds and description values."""
        channel_mock = AsyncMock()
        channel_mock.id = 12345

        # In-memory settings dictionary
        settings = {}
        async def get_setting(key):
            return settings.get(key)
        async def set_setting(key, val):
            settings[key] = val

        # Idempotency checks return True for new events
        async def mark_event_posted(key, channel_id):
            return True

        commits = [
            {
                "sha": "c1",
                "commit": {
                    "message": "Commit 1\nWith detailed body",
                    "author": {"name": "author1", "date": "2026-06-09T11:00:00Z"},
                },
            }
        ]
        prs = [
            {
                "number": 101,
                "merged_at": "2026-06-09T12:00:00Z",
                "title": "PR 101 Title",
                "html_url": "https://github.com/acme/demo/pull/101",
                "user": {"login": "user1"},
                "body": "PR Body Content 1",
            }
        ]

        with patch("repo_updates.fetch_new_commits", AsyncMock(return_value=(commits, "c1"))), \
             patch("repo_updates.fetch_new_merged_prs", AsyncMock(return_value=(prs, 101))):

            ok, message, commit_count, pr_count = await post_project_updates(
                target_channel=channel_mock,
                repo_url="https://github.com/acme/demo",
                branch="main",
                limit=5,
                feed_type="both",
                reported_by="Tester",
                github_token=None,
                get_setting=get_setting,
                set_setting=set_setting,
                mark_event_posted=mark_event_posted,
            )

        self.assertTrue(ok)
        self.assertEqual(commit_count, 1)
        self.assertEqual(pr_count, 1)

        # Expected 3 posts: Header bulletin, PR embed, Commit embed
        self.assertEqual(channel_mock.send.call_count, 3)

        # Verify the PR embed structure and custom description
        pr_send_args = channel_mock.send.call_args_list[1]
        pr_embed = pr_send_args[1].get("embed") or pr_send_args[0][0]
        self.assertIsInstance(pr_embed, discord.Embed)
        self.assertEqual(pr_embed.title, "Merged Pull Request  #101")
        self.assertIn("PR 101 Title", pr_embed.description)
        self.assertIn("PR Body Content 1", pr_embed.description)


if __name__ == "__main__":
    unittest.main()
