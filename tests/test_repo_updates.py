import io
import json
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from repo_updates import (
    clear_github_etag_cache,
    fetch_commits_atom_fallback,
    fetch_new_commits,
    fetch_new_merged_prs,
    fetch_new_repo_events,
    find_project_updates_channel,
    github_get,
    post_project_updates,
)
from services.github_embed_formatter import (
    build_grouped_push_embeds,
    format_author_inline,
)


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

        # Expected 2 posts: PR card and grouped Commit card (no redundant Bulletin header)
        self.assertEqual(channel_mock.send.call_count, 2)

        pr_embed = channel_mock.send.call_args_list[0][1].get("embed")
        self.assertIsInstance(pr_embed, discord.Embed)
        self.assertEqual(pr_embed.title, "🟣 Pull Request Merged • #101")
        self.assertIn("PR 101 Title", pr_embed.description)
        self.assertIn("PR Body Content 1", pr_embed.description)

        push_embed = channel_mock.send.call_args_list[1][1].get("embed")
        self.assertIsInstance(push_embed, discord.Embed)
        self.assertEqual(push_embed.title, "🔨 1 new commit to `main`")
        self.assertIn("c1", push_embed.description)
        self.assertIn("Commit 1", push_embed.description)

    async def test_grouped_push_chronological_author_normalization_noise_and_tickets(self):
        """Grouped push cards sort oldest->newest, fix LAB/WS authors, collapse sync noise, and link CAP tickets."""
        self.assertEqual(
            format_author_inline("LAB15_USER ON WS27", "Realwaan"),
            "[@Realwaan](https://github.com/Realwaan)",
        )
        commits = [
            {
                "sha": "aaaa111",
                "subject": "feat(wallet): CAP-07 cash in/out",
                "body": "",
                "author_name": "LAB15_USER ON WS25",
                "author_login": "Realwaan",
                "author_avatar": None,
                "dt": datetime(2026, 11, 16, 8, 4, tzinfo=timezone.utc),
                "url": "https://github.com/acme/demo/commit/aaaa111",
            },
            {
                "sha": "bbbb222",
                "subject": "fix: resolve CAP-04/CAP-05 merge breakage",
                "body": "",
                "author_name": "LAB15_USER ON WS27",
                "author_login": "Andrei",
                "author_avatar": None,
                "dt": datetime(2026, 11, 16, 8, 10, tzinfo=timezone.utc),
                "url": "https://github.com/acme/demo/commit/bbbb222",
            },
            {
                "sha": "cccc333",
                "subject": "Merge branch 'main' into feat/andrei/cap-05",
                "body": "",
                "author_name": "Marc Andrei Regulacion",
                "author_login": "Andrei",
                "author_avatar": None,
                "dt": datetime(2026, 11, 16, 8, 12, tzinfo=timezone.utc),
                "url": "https://github.com/acme/demo/commit/cccc333",
            },
            {
                "sha": "dddd444",
                "subject": "Merge pull request #101 from acme/feat",
                "body": "",
                "author_name": "Marc Andrei Regulacion",
                "author_login": "Andrei",
                "author_avatar": None,
                "dt": datetime(2026, 11, 16, 8, 15, tzinfo=timezone.utc),
                "url": "https://github.com/acme/demo/commit/dddd444",
            },
        ]
        # Reverse input to confirm chronological oldest -> newest sorting
        embeds = build_grouped_push_embeds(
            owner="acme",
            repo="demo",
            branch="feat/cap-05",
            commits=list(reversed(commits)),
            compare_url="https://github.com/acme/demo/compare/000...ddd",
            pushed_by_login="Andrei",
            posted_pr_numbers={101},
            ticket_lookup={"CAP-05": 9005, "CAP-07": 9007},
        )
        self.assertEqual(len(embeds), 1)
        desc = embeds[0].description
        self.assertLess(desc.index("aaaa111"), desc.index("bbbb222"))
        self.assertNotIn("LAB15_USER", desc)
        self.assertIn("[@Realwaan](https://github.com/Realwaan)", desc)
        self.assertIn("+1 branch sync merge (`cccc333`)", desc)
        self.assertNotIn("dddd444", desc)
        self.assertIn("2 new commits to `feat/cap-05`", embeds[0].title)
        fields = {f.name: f.value for f in embeds[0].fields}
        self.assertIn("<#9005> (**CAP-05**)", fields["🎫 Linked Tickets"])
        self.assertIn("<#9007> (**CAP-07**)", fields["🎫 Linked Tickets"])

    async def test_grouped_push_chunks_large_commit_batches(self):
        """Large 25-commit pushes chunk cleanly within Discord embed limits."""
        commits = [
            {
                "sha": f"{i:07x}" + "a" * 33,
                "subject": f"feat: step {i} implementation details for CAP-08",
                "body": "",
                "author_name": "dev",
                "author_login": "devuser",
                "author_avatar": None,
                "dt": datetime(2026, 11, 16, 8, i, tzinfo=timezone.utc),
                "url": f"https://github.com/acme/demo/commit/{i:07x}",
            }
            for i in range(25)
        ]
        embeds = build_grouped_push_embeds(
            owner="acme",
            repo="demo",
            branch="main",
            commits=commits,
            ticket_lookup={"CAP-08": 9008},
        )
        self.assertEqual(len(embeds), 3)
        for embed in embeds:
            self.assertLessEqual(len(embed.description), 4096)
            for field in embed.fields:
                self.assertLessEqual(len(field.value), 1024)

    async def test_github_get_uses_etag_cache_on_304(self):
        """304 Not Modified reuses cached JSON payload without failing."""
        clear_github_etag_cache()
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = json.dumps([{"id": "ev-1"}]).encode("utf-8")
        mock_resp.headers = {"ETag": '"etag-123"'}

        err_304 = urllib.error.HTTPError(
            url="https://api.github.com/repos/acme/demo/events",
            code=304,
            msg="Not Modified",
            hdrs={},
            fp=io.BytesIO(b""),
        )

        with patch("urllib.request.urlopen", side_effect=[mock_resp, err_304]) as mock_open:
            first = await github_get("https://api.github.com/repos/acme/demo/events")
            second = await github_get("https://api.github.com/repos/acme/demo/events")

        self.assertEqual(first, [{"id": "ev-1"}])
        self.assertEqual(second, [{"id": "ev-1"}])
        second_req = mock_open.call_args_list[1][0][0]
        self.assertEqual(second_req.get_header("If-none-match"), '"etag-123"')
        clear_github_etag_cache()

    async def test_fetch_new_merged_prs_handles_out_of_order_merges(self):
        """Passing last_merged_at catches older PR numbers merged after higher PR numbers."""
        mock_prs = [
            {
                "number": 98,
                "merged_at": "2026-06-09T14:00:00Z",
                "title": "Older PR merged later",
            },
            {
                "number": 102,
                "merged_at": "2026-06-09T12:00:00Z",
                "title": "Already posted PR",
            },
        ]
        with patch("repo_updates.github_get", AsyncMock(return_value=mock_prs)):
            prs, newest_pr = await fetch_new_merged_prs(
                api_base="https://api.github.com/repos/acme/demo",
                last_pr_id=102,
                token=None,
                last_merged_at="2026-06-09T12:00:00Z",
            )
        self.assertEqual([p["number"] for p in prs], [98])
        self.assertEqual(newest_pr, 102)

    async def test_fetch_new_repo_events_hydrates_push_pr_and_review(self):
        """fetch_new_repo_events hydrates PushEvent via /compare plus PullRequestEvent & PullRequestReviewEvent."""
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        events_payload = [
            {
                "id": "300",
                "type": "PullRequestReviewEvent",
                "created_at": now_iso,
                "actor": {"login": "qa_dev"},
                "payload": {
                    "action": "created",
                    "pull_request": {"number": 12, "title": "feat: CAP-09 controls"},
                    "review": {
                        "id": 777,
                        "state": "approved",
                        "body": "Looks solid!",
                        "user": {"login": "qa_dev"},
                        "submitted_at": now_iso,
                    },
                },
            },
            {
                "id": "200",
                "type": "PullRequestEvent",
                "created_at": now_iso,
                "actor": {"login": "andrei"},
                "payload": {
                    "action": "opened",
                    "number": 12,
                    "pull_request": {"number": 12},
                },
            },
            {
                "id": "100",
                "type": "PushEvent",
                "created_at": now_iso,
                "actor": {"login": "Realwaan"},
                "payload": {
                    "ref": "refs/heads/feat/cap-09",
                    "before": "1111111",
                    "head": "2222222",
                    "commits": [],
                },
            },
        ]

        async def fake_get(url: str, token: str | None = None):
            if "/events" in url:
                return events_payload
            if "/compare/1111111...2222222" in url:
                return {
                    "html_url": "https://github.com/acme/demo/compare/1111111...2222222",
                    "commits": [
                        {
                            "sha": "2222222",
                            "author": {"login": "Realwaan"},
                            "commit": {
                                "message": "feat: CAP-09 audit log",
                                "author": {"name": "LAB15_USER ON WS25", "date": now_iso},
                            },
                        }
                    ],
                }
            if "/pulls/12" in url:
                return {
                    "number": 12,
                    "title": "feat: CAP-09 controls",
                    "html_url": "https://github.com/acme/demo/pull/12",
                    "user": {"login": "andrei"},
                    "head": {"ref": "feat/cap-09"},
                    "base": {"ref": "main"},
                }
            return None

        with patch("repo_updates.github_get", new=fake_get):
            events, newest_id = await fetch_new_repo_events(
                api_base="https://api.github.com/repos/acme/demo",
                repo_url_clean="https://github.com/acme/demo",
                last_event_id=None,
                token=None,
                first_run_limit=10,
            )

        self.assertEqual(newest_id, "300")
        self.assertEqual([e["kind"] for e in events], ["push", "pull_request", "pull_request_review"])
        self.assertEqual(events[0]["branch"], "feat/cap-09")
        self.assertEqual(events[0]["commits"][0]["sha"], "2222222")
        self.assertEqual(events[1]["pr"]["title"], "feat: CAP-09 controls")

        # Background poll with existing cursor skips events older than 15 minutes
        stale_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        stale_events = [{**events_payload[0], "created_at": stale_iso}]
        with patch("repo_updates.github_get", AsyncMock(return_value=stale_events)):
            bg_events, bg_id = await fetch_new_repo_events(
                api_base="https://api.github.com/repos/acme/demo",
                repo_url_clean="https://github.com/acme/demo",
                last_event_id=None,
                token=None,
                is_background_poll=True,
                has_existing_cursor=True,
            )
        self.assertEqual(bg_events, [])
        self.assertEqual(bg_id, "300")

    async def test_fetch_commits_atom_fallback_parses_entries(self):
        """Atom fallback parses GitHub commits.atom XML when REST /commits is unavailable."""
        atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>tag:github.com,2008:Grit::Commit/abc123456789</id>
            <link type="text/html" rel="alternate" href="https://github.com/acme/demo/commit/abc123456789"/>
            <title>feat: CAP-10 pay bills flow</title>
            <updated>2026-11-16T08:10:00Z</updated>
            <author>
              <name>LAB15_USER ON WS27</name>
              <uri>https://github.com/Realwaan</uri>
            </author>
          </entry>
        </feed>"""
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = atom_xml.encode("utf-8")

        with patch("urllib.request.urlopen", return_value=mock_resp):
            commits, newest = await fetch_commits_atom_fallback(
                owner="acme",
                repo="demo",
                branch="main",
                last_sha=None,
                first_run_limit=5,
            )

        self.assertEqual(newest, "abc123456789")
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0]["author"]["login"], "Realwaan")
        self.assertEqual(commits[0]["commit"]["message"], "feat: CAP-10 pay bills flow")

    def test_find_project_updates_channel_prefers_capstone_category(self):
        """When multiple #project-updates channels exist, prefer the Capstone category."""
        top_ch = MagicMock(spec=discord.TextChannel)
        top_ch.id = 1
        top_ch.name = "project-updates"
        top_ch.category_id = None
        top_ch.category = None

        ide_cat = MagicMock()
        ide_cat.name = "IDE-a"
        ide_ch = MagicMock(spec=discord.TextChannel)
        ide_ch.id = 2
        ide_ch.name = "project-updates"
        ide_ch.category_id = 20
        ide_ch.category = ide_cat

        cap_cat = MagicMock()
        cap_cat.name = "Capstone"
        cap_ch = MagicMock(spec=discord.TextChannel)
        cap_ch.id = 3
        cap_ch.name = "project-updates"
        cap_ch.category_id = 30
        cap_ch.category = cap_cat

        guild = MagicMock(spec=discord.Guild)
        guild.text_channels = [top_ch, ide_ch, cap_ch]

        found = find_project_updates_channel(guild)
        self.assertEqual(found, cap_ch)


if __name__ == "__main__":
    unittest.main()
