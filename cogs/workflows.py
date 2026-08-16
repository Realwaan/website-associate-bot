"""AI UX Playground Multi-Step Workflows Cog."""
import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
from pathlib import Path
from database import (
    add_thread, mark_ticket_loaded, get_user_roles
)
from services.ai_service import ai_client
from config import TICKETS_DIR

logger = logging.getLogger(__name__)

async def safe_defer(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer()

WORKFLOW_SPECS = {
    "design-sprint": {
        "title": "5-Day Design Sprint",
        "category": "Design",
        "duration": "5 Days / 40h",
        "color": 0x8b5cf6,
        "description": "Multi-step design sprint derived from GV & AI UX Playground: Understand & Map -> Lightning Solutions -> Storyboard -> High-Fi Prototype -> Usability Test.",
        "steps": [
            {
                "id": "day1-map",
                "title": "Day 1: Understand & Map User Journey",
                "priority": "HIGH",
                "problem": "The core user friction points and drop-offs have not been mapped into an actionable customer empathy journey.",
                "what_to_fix": [
                    "Interview stakeholders or users on primary workflow friction",
                    "Construct customer journey map from discovery to success state",
                    "Formulate 6 How Might We (HMW) statements"
                ],
                "acceptance_criteria": [
                    "Customer journey map documented",
                    "Primary sprint question approved",
                    "6 HMW opportunity statements categorized"
                ],
                "files": ["docs/design-sprint/day1-journey.md"]
            },
            {
                "id": "day2-sketch",
                "title": "Day 2: Ideate & Lightning Solutions",
                "priority": "HIGH",
                "problem": "Alternative interaction patterns have not been systematically explored.",
                "what_to_fix": [
                    "Conduct Lightning Demos on 3 benchmark platforms",
                    "Perform Crazy Eights sketch iterations on core views",
                    "Produce 3 distinct three-panel solution sketches"
                ],
                "acceptance_criteria": [
                    "3 competing solution patterns documented",
                    "Interaction trade-offs analyzed"
                ],
                "files": ["docs/design-sprint/day2-sketches.md"]
            },
            {
                "id": "day3-decide",
                "title": "Day 3: Storyboard & Screen Decision Matrix",
                "priority": "CRITICAL",
                "problem": "Team requires alignment on winning architecture and an 8-panel storyboard before implementation.",
                "what_to_fix": [
                    "Critique solution sketches and vote on winning interaction",
                    "Draft 8-panel gapless storyboard covering happy path and edge states"
                ],
                "acceptance_criteria": [
                    "Winning architectural concept selected and justified",
                    "8-panel storyboard completed with copy and state transitions"
                ],
                "files": ["docs/design-sprint/day3-storyboard.md"]
            },
            {
                "id": "day4-prototype",
                "title": "Day 4: High-Fidelity Prototype Implementation",
                "priority": "CRITICAL",
                "problem": "Clickable high-fidelity UI prototype is needed for user testing.",
                "what_to_fix": [
                    "Scaffold responsive UI components matching Day 3 storyboard",
                    "Wire dynamic mock data and input validation states",
                    "Verify fluid transitions and deploy to staging"
                ],
                "acceptance_criteria": [
                    "Prototype runs smoothly in browser with 0 runtime errors",
                    "All 8 storyboard screens are interactive"
                ],
                "files": ["src/components/", "src/styles/"]
            },
            {
                "id": "day5-test",
                "title": "Day 5: Usability Validation & Synthesis Matrix",
                "priority": "HIGH",
                "problem": "Validate prototype with 5 user tests and translate findings into development backlog.",
                "what_to_fix": [
                    "Conduct 5 recorded usability tests using standardized protocol",
                    "Score System Usability Scale (SUS) and log friction points",
                    "Synthesize qualitative findings into prioritized fix tickets"
                ],
                "acceptance_criteria": [
                    "5 user test sessions completed and scored",
                    "Synthesis matrix documents positive patterns vs friction blockers"
                ],
                "files": ["docs/design-sprint/day5-synthesis.md"]
            }
        ]
    },
    "write-prd": {
        "title": "Write a PRD / Product Spec",
        "category": "Product",
        "duration": "2 Days / 16h",
        "color": 0x0ea5e9,
        "description": "Comprehensive PRD playbook: Problem Justification -> MoSCoW Functional Scope -> Architecture & Data Contracts -> Launch Gates.",
        "steps": [
            {
                "id": "prd-part1",
                "title": "PRD Part 1: Problem Space & Business Objectives",
                "priority": "HIGH",
                "problem": "Unclear business justification and ambiguous problem scope creates team misalignment.",
                "what_to_fix": [
                    "Articulate primary problem statement with qualitative/quantitative proof",
                    "Document target personas and Jobs to Be Done (JTBD)",
                    "Establish North Star metric and guardrail metrics"
                ],
                "acceptance_criteria": [
                    "Problem statement clearly states who is affected and impact of inaction",
                    "3 core JTBD statements formatted properly"
                ],
                "files": ["docs/prd/01-problem-objectives.md"]
            },
            {
                "id": "prd-part2",
                "title": "PRD Part 2: Functional Scope & MoSCoW Prioritization",
                "priority": "CRITICAL",
                "problem": "Feature scope lacks strict P0 Must-Have vs P2 Nice-To-Have boundaries.",
                "what_to_fix": [
                    "Document user stories with P0/P1/P2 priorities",
                    "Define Out-of-Scope boundaries to prevent scope creep",
                    "Map state machine transitions for core user journey"
                ],
                "acceptance_criteria": [
                    "All functional requirements include edge cases",
                    "Explicit Out-of-Scope list documented"
                ],
                "files": ["docs/prd/02-functional-scope.md"]
            },
            {
                "id": "prd-part3",
                "title": "PRD Part 3: Architecture & Data Contracts",
                "priority": "HIGH",
                "problem": "Data models and API schemas must be locked before coding begins.",
                "what_to_fix": [
                    "Define database schema and entity relationships",
                    "Specify REST/GraphQL API contracts with payload samples",
                    "Document authentication and RBAC permissions"
                ],
                "acceptance_criteria": [
                    "SQL schema provided with foreign keys and indexes",
                    "API endpoints documented with error status codes"
                ],
                "files": ["docs/prd/03-technical-specs.md", "src/types/index.ts"]
            },
            {
                "id": "prd-part4",
                "title": "PRD Part 4: Launch Gates & Telemetry Plan",
                "priority": "MEDIUM",
                "problem": "Need telemetry tracking taxonomy and pre-launch QA checklists before release.",
                "what_to_fix": [
                    "Formulate analytics event tracking taxonomy",
                    "Establish pre-launch QA checklists",
                    "Document rollback and recovery plan"
                ],
                "acceptance_criteria": [
                    "Analytics event taxonomy covers conversion telemetry",
                    "Zero P0 blockers launch criteria verified"
                ],
                "files": ["docs/prd/04-launch-gates.md"]
            }
        ]
    },
    "design-system": {
        "title": "Build a Design System",
        "category": "Design",
        "duration": "3 Days / 24h",
        "color": 0xec4899,
        "description": "Design system architecture: Semantic Color Tokens -> Polymorphic Component Primitives -> Micro-interactions -> Documentation.",
        "steps": [
            {
                "id": "ds-part1",
                "title": "Design System: Color Tokens & Typography Scale",
                "priority": "HIGH",
                "problem": "Inconsistent hex values and font sizes cause visual fragmentation.",
                "what_to_fix": [
                    "Construct semantic HSL color palette with dark/light mode support",
                    "Define fluid typography hierarchy with line heights",
                    "Standardize 4px/8px spacing and elevation tokens"
                ],
                "acceptance_criteria": [
                    "CSS variables defined in central stylesheet",
                    "All text passes WCAG 2.1 AA 4.5:1 contrast"
                ],
                "files": ["src/index.css", "src/styles/tokens.css"]
            },
            {
                "id": "ds-part2",
                "title": "Design System: Core UI Component Primitives",
                "priority": "CRITICAL",
                "problem": "Buttons, Inputs, and Badges are duplicated with bespoke styling.",
                "what_to_fix": [
                    "Implement polymorphic Button primitive with size/loading states",
                    "Implement Input/Textarea primitives with error labels",
                    "Implement Card, Modal, and Badge primitives"
                ],
                "acceptance_criteria": [
                    "Components export strict TypeScript prop interfaces",
                    "Keyboard focus rings and ARIA attributes included"
                ],
                "files": ["src/components/ui/"]
            },
            {
                "id": "ds-part3",
                "title": "Design System: Micro-Interactions & States",
                "priority": "MEDIUM",
                "problem": "Interactive elements lack tactile feedback and shimmer loading states.",
                "what_to_fix": [
                    "Add hover elevation transitions and active click feedback",
                    "Implement skeleton shimmer loaders for async views",
                    "Add accessible toast notifications and alert banners"
                ],
                "acceptance_criteria": [
                    "Hardware-accelerated transforms used",
                    "prefers-reduced-motion media query respected"
                ],
                "files": ["src/components/", "src/index.css"]
            }
        ]
    },
    "usability-testing": {
        "title": "Run Usability Tests & Heuristics",
        "category": "Research",
        "duration": "2 Days / 16h",
        "color": 0x10b981,
        "description": "Nielsen Heuristics evaluation and task scenario usability testing protocol.",
        "steps": [
            {
                "id": "ut-part1",
                "title": "Usability: Test Protocol & 5 Task Scenarios",
                "priority": "HIGH",
                "problem": "Unstructured testing produces subjective, non-actionable feedback.",
                "what_to_fix": [
                    "Draft 5 realistic task scenario prompts",
                    "Formulate pre/post-test System Usability Scale (SUS) survey",
                    "Establish objective completion benchmark (>80%)"
                ],
                "acceptance_criteria": [
                    "5 core task scenarios documented",
                    "SUS survey prepared for scoring"
                ],
                "files": ["docs/usability/test-protocol.md"]
            },
            {
                "id": "ut-part2",
                "title": "Usability: 10 Nielsen Heuristics Audit",
                "priority": "HIGH",
                "problem": "System may violate standard usability heuristics.",
                "what_to_fix": [
                    "Audit workflows against 10 Nielsen Heuristics",
                    "Log violations with severity rating 1 to 4",
                    "Evaluate error message clarity and recovery instructions"
                ],
                "acceptance_criteria": [
                    "Scorecard covers all 10 heuristics",
                    "Remediation actions documented for all violations"
                ],
                "files": ["docs/usability/heuristic-audit.md"]
            },
            {
                "id": "ut-part3",
                "title": "Usability: Prioritized Remediation Backlog",
                "priority": "CRITICAL",
                "problem": "Usability findings must be resolved in code.",
                "what_to_fix": [
                    "Implement code fixes for Severity 3 and 4 blockers",
                    "Refine microcopy, confirmation dialogs, and recovery states"
                ],
                "acceptance_criteria": [
                    "Critical usability friction points resolved and verified"
                ],
                "files": ["src/components/"]
            }
        ]
    },
    "accessibility-audit": {
        "title": "Run an Accessibility (a11y) Audit",
        "category": "Accessibility",
        "duration": "2 Days / 16h",
        "color": 0xf59e0b,
        "description": "WCAG 2.1 AA accessibility audit: Contrast & Landmarks -> Keyboard Focus Traps -> Screen Reader ARIA.",
        "steps": [
            {
                "id": "a11y-part1",
                "title": "Accessibility: WCAG 2.1 AA Contrast & Structure",
                "priority": "HIGH",
                "problem": "Color contrast and semantic hierarchy may exclude visually impaired users.",
                "what_to_fix": [
                    "Audit text and button contrast against 4.5:1 ratio",
                    "Verify HTML5 landmark structure and sequential heading hierarchy"
                ],
                "acceptance_criteria": [
                    "Zero contrast violations in dark/light modes",
                    "Proper landmark hierarchy across all pages"
                ],
                "files": ["src/index.css", "src/components/"]
            },
            {
                "id": "a11y-part2",
                "title": "Accessibility: Keyboard Navigation & Focus Traps",
                "priority": "CRITICAL",
                "problem": "Keyboard users cannot operate interactive dialogs and dropdowns.",
                "what_to_fix": [
                    "Ensure all interactive elements are reachable via Tab",
                    "Implement focus trap on open modals with Escape key dismiss"
                ],
                "acceptance_criteria": [
                    "Complete workflow operable via keyboard only",
                    "High-visibility focus ring on active controls"
                ],
                "files": ["src/components/"]
            },
            {
                "id": "a11y-part3",
                "title": "Accessibility: Screen Reader ARIA & Alt Text",
                "priority": "HIGH",
                "problem": "Icon buttons and async notifications are not announced to screen readers.",
                "what_to_fix": [
                    "Add aria-label to all icon-only buttons",
                    "Use aria-live polite regions on toasts and progress bars",
                    "Ensure descriptive alt text on images"
                ],
                "acceptance_criteria": [
                    "Screen readers announce status updates",
                    "Zero unlabelled interactive buttons"
                ],
                "files": ["src/components/"]
            }
        ]
    },
    "design-handoff": {
        "title": "Engineering Handoff & Edge Cases",
        "category": "Engineering",
        "duration": "2 Days / 16h",
        "color": 0x06b6d4,
        "description": "Design-to-engineering handoff: Component States -> Error Boundaries -> Token & API Payload Mapping.",
        "steps": [
            {
                "id": "handoff-part1",
                "title": "Handoff: Component State Matrix",
                "priority": "HIGH",
                "problem": "Developers guess component styling in empty, loading, and error states.",
                "what_to_fix": [
                    "Specify visual rules for Idle, Hover, Loading, Empty, and Error states",
                    "Design empty states with clear calls-to-action"
                ],
                "acceptance_criteria": [
                    "All components have visual specifications for all states"
                ],
                "files": ["docs/handoff/component-states.md"]
            },
            {
                "id": "handoff-part2",
                "title": "Handoff: Error Boundaries & Network Fallbacks",
                "priority": "CRITICAL",
                "problem": "Network errors cause unhandled crashes with no user recovery.",
                "what_to_fix": [
                    "Implement React Error Boundary with retry trigger",
                    "Add optimistic UI updates with automatic rollback on failure"
                ],
                "acceptance_criteria": [
                    "App catches unexpected runtime exceptions with friendly retry CTA",
                    "Optimistic state rollbacks seamlessly on API errors"
                ],
                "files": ["src/components/"]
            },
            {
                "id": "handoff-part3",
                "title": "Handoff: Token Mapping & API Payload Contracts",
                "priority": "HIGH",
                "problem": "Design token names and backend API response keys lack synchronized types.",
                "what_to_fix": [
                    "Map design tokens to component props",
                    "Export shared TypeScript type interfaces for all API payloads"
                ],
                "acceptance_criteria": [
                    "Shared TypeScript types export 100% type-safe schemas"
                ],
                "files": ["src/types/index.ts"]
            }
        ]
    }
}

class WorkflowsCog(commands.Cog, name="AI UX Workflows"):
    """AI UX Playground Multi-Step Workflow Engine."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 1. /workflow-list
    @app_commands.command(name="workflow-list", description="Browse AI UX Playground multi-step design & product workflows")
    async def workflow_list(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        embed = discord.Embed(
            title="🧩 AI UX Playground Workflows Catalog",
            description="Multi-step chained prompt workflows for Design, Product, Research, and Engineering.\nUse `/workflow <type> [project_name]` to generate and create ticket threads.",
            color=0x8b5cf6
        )

        for key, spec in WORKFLOW_SPECS.items():
            embed.add_field(
                name=f"✨ {spec['title']} (`{key}`)",
                value=f"**Category**: {spec['category']} • **Duration**: {spec['duration']}\n{spec['description']}\n*Steps ({len(spec['steps'])})*: {', '.join(s['id'] for s in spec['steps'])}",
                inline=False
            )

        embed.set_footer(text="CapStoneFlow • Powered by aiuxplayground.com playbooks")
        await interaction.followup.send(embed=embed)

    # 2. /workflow
    @app_commands.command(name="workflow", description="Generate a chained multi-step workflow ticket series and create Discord threads")
    @app_commands.describe(
        workflow_type="Select workflow framework",
        project_name="Name of the project or feature (e.g. USCCE Attendance)"
    )
    @app_commands.choices(workflow_type=[
        app_commands.Choice(name="5-Day Design Sprint (Design)", value="design-sprint"),
        app_commands.Choice(name="Write a PRD / Product Spec (Product)", value="write-prd"),
        app_commands.Choice(name="Build a Design System (Design)", value="design-system"),
        app_commands.Choice(name="Run Usability Tests & Heuristics (Research)", value="usability-testing"),
        app_commands.Choice(name="Run an Accessibility Audit (a11y)", value="accessibility-audit"),
        app_commands.Choice(name="Engineering Handoff & Edge Cases (Dev)", value="design-handoff"),
    ])
    async def run_workflow(self, interaction: discord.Interaction, workflow_type: str, project_name: str = "Capstone Project"):
        await safe_defer(interaction)
        try:
            spec = WORKFLOW_SPECS.get(workflow_type)
            if not spec:
                await interaction.followup.send(f"❌ Unknown workflow type `{workflow_type}`.")
                return

            folder_slug = f"{project_name.lower().replace(' ', '-')}-{workflow_type}"
            target_dir = Path(TICKETS_DIR) / folder_slug
            target_dir.mkdir(parents=True, exist_ok=True)

            created_threads = []
            
            # Post Overview Embed
            overview_embed = discord.Embed(
                title=f"🚀 Launching AI UX Workflow: {spec['title']}",
                description=f"**Project**: `{project_name}`\n**Folder**: `tickets/{folder_slug}/`\n{spec['description']}",
                color=spec['color']
            )
            overview_embed.add_field(name="⏱️ Total Duration", value=spec['duration'], inline=True)
            overview_embed.add_field(name="📑 Chained Steps", value=f"`{len(spec['steps'])}` tickets", inline=True)
            overview_embed.set_footer(text="Synchronized with CapStoneFlow Task Matrix")
            await interaction.followup.send(embed=overview_embed)

            for step in spec['steps']:
                title = f"{step['title']} ({project_name})"
                filename = f"{step['id']}.md"
                file_path = target_dir / filename

                # Generate Markdown content matching ticketsguideline.md
                md_content = f"""# [{step['priority']}] {title}

**[{step['priority']}]**

## Problem
{step['problem']} (Context: {project_name})

## Potentially Related Files
{chr(10).join(f"- {f}" for f in step['files'])}

## What to Fix
{chr(10).join(f"{i+1}. {fix}" for i, fix in enumerate(step['what_to_fix']))}

## Acceptance Criteria
{chr(10).join(f"- [ ] {crit}" for crit in step['acceptance_criteria'])}
"""
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(md_content)

                # Create Thread
                thread_name = f"[{step['priority']}][OPEN] {step['title']}"[:100]
                thread = await interaction.channel.create_thread(
                    name=thread_name,
                    auto_archive_duration=1440,
                    type=discord.ChannelType.public_thread
                )

                # Post Initial Step Embed
                step_embed = discord.Embed(
                    title=f"📋 {step['title']}",
                    description=step['problem'],
                    color=spec['color']
                )
                step_embed.add_field(name="🚨 Priority", value=f"`{step['priority']}`", inline=True)
                step_embed.add_field(name="📂 Folder", value=f"`{folder_slug}`", inline=True)
                step_embed.add_field(
                    name="🛠️ What to Fix",
                    value="\n".join(f"**{i+1}.** {fix}" for i, fix in enumerate(step['what_to_fix']))[:1024],
                    inline=False
                )
                step_embed.add_field(
                    name="✅ Acceptance Criteria",
                    value="\n".join(f"▫️ {crit}" for crit in step['acceptance_criteria'])[:1024],
                    inline=False
                )
                step_embed.set_footer(text="Type /claim to take ownership of this step.")
                await thread.send(embed=step_embed)

                add_thread(thread.id, title, folder_slug, interaction.channel_id, interaction.user.name)
                mark_ticket_loaded(filename, folder_slug, thread.id, interaction.channel_id)
                created_threads.append(thread.mention)

            summary_embed = discord.Embed(
                title="🎉 Workflow Generated & Synchronized!",
                description=f"Created **{len(created_threads)}** chained workflow ticket threads:\n" + "\n".join(f"👉 {t}" for t in created_threads),
                color=0x10b981
            )
            summary_embed.set_footer(text="All tickets are live and ready for /claim!")
            await interaction.channel.send(embed=summary_embed)

        except Exception as e:
            logger.error(f"Error in /workflow: {e}")
            await interaction.followup.send(f"❌ Error generating workflow: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(WorkflowsCog(bot))
