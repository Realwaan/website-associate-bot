"""Tests for concise_planner module."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from concise_planner import (
    PlannedTicket,
    PlanResult,
    _extract_json_from_response,
    _ticket_to_markdown,
    build_plan_summary,
    generate_concise_plan,
    parse_ai_plan_response,
    write_plan_tickets,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_AI_RESPONSE = json.dumps({
    "project_summary": "A simple task management app with auth, dashboard, and API.",
    "tickets": [
        {
            "area": "server",
            "slug": "user-auth",
            "title": "Implement User Authentication",
            "priority": True,
            "problem": "Users cannot log in or create accounts.",
            "related_files": ["actions/auth.ts", "lib/supabase/server.ts"],
            "what_to_fix": [
                "Create signup endpoint",
                "Create login endpoint",
                "Add session management",
            ],
            "acceptance_criteria": [
                "Users can sign up with email/password",
                "Users can log in with credentials",
                "Session persists across navigation",
            ],
            "cta": "Backend developer: Claim this first — it blocks everything.",
            "blocks": ["dashboard", "api-endpoints"],
        },
        {
            "area": "client",
            "slug": "dashboard-ui",
            "title": "Build Task Dashboard",
            "priority": False,
            "problem": "No task overview page exists for users.",
            "related_files": ["components/dashboard/TaskList.tsx"],
            "what_to_fix": [
                "Create dashboard layout",
                "Add task list component",
                "Connect to API",
            ],
            "acceptance_criteria": [
                "Dashboard shows user tasks",
                "Tasks can be filtered by status",
            ],
            "cta": "Frontend developer: Start after auth is merged.",
            "blocks": [],
        },
    ],
})


@pytest.fixture
def tmp_tickets_dir():
    """Create a temporary directory for ticket output."""
    with tempfile.TemporaryDirectory(prefix="test-tickets-") as tmpdir:
        yield tmpdir


# ---------------------------------------------------------------------------
# JSON extraction tests
# ---------------------------------------------------------------------------

class TestExtractJson:
    def test_plain_json(self):
        raw = '{"key": "value"}'
        result = _extract_json_from_response(raw)
        assert json.loads(result) == {"key": "value"}

    def test_json_with_markdown_fences(self):
        raw = '```json\n{"key": "value"}\n```'
        result = _extract_json_from_response(raw)
        assert json.loads(result) == {"key": "value"}

    def test_json_with_preamble(self):
        raw = 'Here is the plan:\n{"key": "value"}'
        result = _extract_json_from_response(raw)
        assert json.loads(result) == {"key": "value"}

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON object found"):
            _extract_json_from_response("no json here")

    def test_nested_json(self):
        nested = '{"outer": {"inner": "val"}}'
        result = _extract_json_from_response(nested)
        parsed = json.loads(result)
        assert parsed["outer"]["inner"] == "val"


# ---------------------------------------------------------------------------
# Response parsing tests
# ---------------------------------------------------------------------------

class TestParseAiPlanResponse:
    def test_valid_response(self):
        summary, tickets = parse_ai_plan_response(VALID_AI_RESPONSE)
        assert summary == "A simple task management app with auth, dashboard, and API."
        assert len(tickets) == 2
        assert tickets[0].title == "Implement User Authentication"
        assert tickets[0].priority is True
        assert tickets[0].area == "server"
        assert tickets[0].cta == "Backend developer: Claim this first — it blocks everything."
        assert tickets[1].priority is False

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="invalid JSON"):
            parse_ai_plan_response("not json at all {broken")

    def test_empty_tickets_raises(self):
        raw = json.dumps({"project_summary": "Test", "tickets": []})
        with pytest.raises(ValueError, match="zero tickets"):
            parse_ai_plan_response(raw)

    def test_missing_area_defaults_to_client(self):
        raw = json.dumps({
            "project_summary": "Test",
            "tickets": [{
                "slug": "test",
                "title": "Test Ticket",
                "problem": "A problem",
                "what_to_fix": ["Fix it"],
                "acceptance_criteria": ["It works"],
                "cta": "Do it.",
            }],
        })
        _, tickets = parse_ai_plan_response(raw)
        assert tickets[0].area == "client"

    def test_invalid_area_normalized(self):
        raw = json.dumps({
            "project_summary": "Test",
            "tickets": [{
                "area": "INVALID_AREA",
                "slug": "test",
                "title": "Test Ticket",
                "problem": "A problem",
                "what_to_fix": ["Fix it"],
                "acceptance_criteria": ["It works"],
                "cta": "Do it.",
            }],
        })
        _, tickets = parse_ai_plan_response(raw)
        assert tickets[0].area == "client"

    def test_minimal_ticket_gets_defaults(self):
        raw = json.dumps({
            "project_summary": "Test",
            "tickets": [{"title": "Minimal"}],
        })
        _, tickets = parse_ai_plan_response(raw)
        assert len(tickets) == 1
        assert tickets[0].problem  # Should have a default
        assert tickets[0].what_to_fix  # Should have a default
        assert tickets[0].acceptance_criteria  # Should have a default
        assert tickets[0].cta  # Should have a default

    def test_response_with_markdown_fences(self):
        raw = f"```json\n{VALID_AI_RESPONSE}\n```"
        summary, tickets = parse_ai_plan_response(raw)
        assert len(tickets) == 2


# ---------------------------------------------------------------------------
# Markdown generation tests
# ---------------------------------------------------------------------------

class TestTicketToMarkdown:
    def test_basic_structure(self):
        ticket = PlannedTicket(
            area="client",
            slug="login-form",
            title="Build Login Form",
            priority=False,
            problem="No login page exists.",
            related_files=["components/Login.tsx"],
            what_to_fix=["Create form", "Add validation"],
            acceptance_criteria=["Form renders", "Validation works"],
            cta="Frontend dev: Start building.",
            blocks=[],
        )
        md = _ticket_to_markdown(ticket)
        assert md.startswith("# Build Login Form")
        assert "## Problem" in md
        assert "## What to Fix" in md
        assert "## Acceptance Criteria" in md
        assert "## Call to Action" in md
        assert "**→** Frontend dev: Start building." in md
        assert "**[PRIORITY]**" not in md

    def test_priority_ticket(self):
        ticket = PlannedTicket(
            area="server",
            slug="auth",
            title="Auth System",
            priority=True,
            problem="No auth.",
            related_files=[],
            what_to_fix=["Build it"],
            acceptance_criteria=["It works"],
            cta="Do it now.",
            blocks=[],
        )
        md = _ticket_to_markdown(ticket)
        assert "**[PRIORITY]**" in md

    def test_no_related_files(self):
        ticket = PlannedTicket(
            area="utils",
            slug="setup",
            title="Setup Script",
            priority=False,
            problem="No setup.",
            related_files=[],
            what_to_fix=["Create script"],
            acceptance_criteria=["Script runs"],
            cta="DevOps: Run setup.",
            blocks=[],
        )
        md = _ticket_to_markdown(ticket)
        assert "to be determined" in md


# ---------------------------------------------------------------------------
# File writing tests
# ---------------------------------------------------------------------------

class TestWritePlanTickets:
    def test_writes_correct_files(self, tmp_tickets_dir):
        tickets = [
            PlannedTicket(
                area="client",
                slug="login",
                title="Login Page",
                priority=True,
                problem="No login.",
                related_files=[],
                what_to_fix=["Build it"],
                acceptance_criteria=["Works"],
                cta="Do it.",
                blocks=[],
            ),
            PlannedTicket(
                area="server",
                slug="api",
                title="API Endpoints",
                priority=False,
                problem="No API.",
                related_files=[],
                what_to_fix=["Create endpoints"],
                acceptance_criteria=["Returns JSON"],
                cta="Backend dev starts.",
                blocks=[],
            ),
        ]
        paths = write_plan_tickets(tickets, "test-plan", tmp_tickets_dir)
        assert len(paths) == 2

        for path in paths:
            assert Path(path).exists()
            content = Path(path).read_text(encoding="utf-8")
            assert "# " in content
            assert "## Call to Action" in content

        filenames = [Path(p).name for p in paths]
        assert "client-login.md" in filenames
        assert "server-api.md" in filenames

    def test_creates_directory(self, tmp_tickets_dir):
        tickets = [
            PlannedTicket(
                area="utils",
                slug="test",
                title="Test",
                priority=False,
                problem="Test.",
                related_files=[],
                what_to_fix=["Test"],
                acceptance_criteria=["Pass"],
                cta="Test.",
                blocks=[],
            ),
        ]
        folder = "nonexistent-folder"
        paths = write_plan_tickets(tickets, folder, tmp_tickets_dir)
        assert len(paths) == 1
        assert Path(tmp_tickets_dir, folder).is_dir()


class TestBuildPlanSummary:
    def test_creates_plan_file(self, tmp_tickets_dir):
        tickets = [
            PlannedTicket(
                area="client",
                slug="ui",
                title="Build UI",
                priority=True,
                problem="No UI.",
                related_files=[],
                what_to_fix=["Build it"],
                acceptance_criteria=["Renders"],
                cta="Start now.",
                blocks=["api"],
            ),
        ]
        path = build_plan_summary(
            project_summary="A test project.",
            tickets=tickets,
            folder="test-summary",
            description="Build a test app.",
            tickets_dir=tmp_tickets_dir,
        )
        assert Path(path).exists()
        content = Path(path).read_text(encoding="utf-8")
        assert "# Concise Plan: test-summary" in content
        assert "A test project." in content
        assert "Build UI" in content
        assert "Start now." in content
        assert "Dependencies" in content
        assert "blocks" in content.lower()


# ---------------------------------------------------------------------------
# AI call test (mocked)
# ---------------------------------------------------------------------------

class TestGenerateConcisePlan:
    def test_calls_ai_client(self):
        mock_client = MagicMock()
        mock_client.chat.return_value = VALID_AI_RESPONSE

        result = generate_concise_plan(
            mock_client,
            "Build a task management app",
            context="Using Next.js and Supabase",
            max_tickets=5,
        )

        mock_client.chat.assert_called_once()
        call_kwargs = mock_client.chat.call_args
        assert "task management" in call_kwargs.args[0].lower()
        assert call_kwargs.kwargs["enable_thinking"] is True
        assert result == VALID_AI_RESPONSE
