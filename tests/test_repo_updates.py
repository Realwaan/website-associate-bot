import unittest
from unittest.mock import patch

from repo_updates import fetch_new_commits


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


if __name__ == "__main__":
    unittest.main()
