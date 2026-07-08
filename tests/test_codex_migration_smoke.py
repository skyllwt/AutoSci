#!/usr/bin/env python3
"""Static and local Codex migration smoke checks.

These tests avoid network calls and avoid mutating the repository. They cover
the invariants that should stay true while the heavier Codex skill matrix is
run manually or in disposable branches.
"""

from __future__ import annotations

import json
import ast
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CodexMigrationSmokeTests(unittest.TestCase):
    def _load_daily_arxiv_without_sandbox(self):
        sys.modules["_sandbox"] = types.ModuleType("_sandbox")
        sys.modules.pop("daily_arxiv", None)
        spec = importlib.util.spec_from_file_location("daily_arxiv", ROOT / "tools/daily_arxiv.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules["daily_arxiv"] = module
        spec.loader.exec_module(module)
        return module

    def _load_discover_without_sandbox(self):
        sys.modules["_sandbox"] = types.ModuleType("_sandbox")
        sys.modules.pop("discover", None)
        if str(ROOT / "tools") not in sys.path:
            sys.path.insert(0, str(ROOT / "tools"))
        spec = importlib.util.spec_from_file_location("discover", ROOT / "tools/discover.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules["discover"] = module
        spec.loader.exec_module(module)
        return module

    def _load_serve_module(self):
        sys.modules.pop("serve", None)
        spec = importlib.util.spec_from_file_location("serve", ROOT / "tools/serve.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules["serve"] = module
        spec.loader.exec_module(module)
        return module

    def _intent_payload(self, skill: str, body: dict) -> dict:
        serve = self._load_serve_module()
        builders = {
            "ingest": serve.WikiHandler._intent_ingest,
            "ask": serve.WikiHandler._intent_ask,
            "check": serve.WikiHandler._intent_check,
            "discover": serve.WikiHandler._intent_discover,
        }
        out = builders[skill](body)
        out.setdefault("skill", skill)
        out.setdefault("doc_url", f".claude/skills/{skill}/SKILL.md")
        out.setdefault("codex_doc_url", f".agents/skills/{skill}/SKILL.md")
        if "codex_command" not in out and out.get("command", "").startswith("/"):
            out["codex_command"] = "$" + out["command"][1:]
        return out

    def test_skill_trees_have_matching_skill_names(self) -> None:
        source = sorted(path.name for path in (ROOT / "i18n/en/skills").iterdir() if path.is_dir())
        codex = sorted(
            path.name
            for path in (ROOT / ".agents/skills").iterdir()
            if path.is_dir() and path.name != "shared-references"
        )
        claude = sorted(
            path.name
            for path in (ROOT / ".claude/skills").iterdir()
            if path.is_dir() and path.name != "shared-references"
        )
        self.assertEqual(source, codex)
        self.assertEqual(codex, claude)

    def test_i18n_skill_sources_have_matching_shape(self) -> None:
        en_dirs = sorted(path.name for path in (ROOT / "i18n/en/skills").iterdir() if path.is_dir())
        zh_dirs = sorted(path.name for path in (ROOT / "i18n/zh/skills").iterdir() if path.is_dir())
        self.assertEqual(en_dirs, zh_dirs)

        def frontmatter(path: Path) -> dict[str, str]:
            text = path.read_text(encoding="utf-8")
            match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
            self.assertIsNotNone(match, path)
            fields: dict[str, str] = {}
            for line in match.group(1).splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    fields[key.strip()] = value.strip().strip('"')
            return fields

        for name in en_dirs:
            en_fm = frontmatter(ROOT / "i18n/en/skills" / name / "SKILL.md")
            zh_fm = frontmatter(ROOT / "i18n/zh/skills" / name / "SKILL.md")
            self.assertEqual(en_fm.get("name"), name)
            self.assertEqual(zh_fm.get("name"), name)
            self.assertTrue(en_fm.get("description"), name)
            self.assertTrue(zh_fm.get("description"), name)

        en_refs = sorted(path.name for path in (ROOT / "i18n/en/shared-references").glob("*.md"))
        zh_refs = sorted(path.name for path in (ROOT / "i18n/zh/shared-references").glob("*.md"))
        self.assertEqual(en_refs, zh_refs)

    def test_shared_references_are_synced_from_i18n(self) -> None:
        source = ROOT / "i18n/en/shared-references"
        codex = ROOT / ".agents/skills/shared-references"
        claude = ROOT / ".claude/skills/shared-references"
        source_files = sorted(path.name for path in source.glob("*.md"))
        self.assertEqual(source_files, sorted(path.name for path in codex.glob("*.md")))
        self.assertEqual(source_files, sorted(path.name for path in claude.glob("*.md")))
        for filename in source_files:
            expected = (source / filename).read_text(encoding="utf-8")
            self.assertEqual(expected, (codex / filename).read_text(encoding="utf-8"))
            self.assertEqual(expected, (claude / filename).read_text(encoding="utf-8"))

    def test_active_agent_instruction_files_are_synced_from_i18n(self) -> None:
        pairs = [
            (ROOT / "i18n/en/AGENTS.md", ROOT / "AGENTS.md"),
            (ROOT / "i18n/en/CLAUDE.md", ROOT / "CLAUDE.md"),
        ]
        for source, active in pairs:
            self.assertEqual(source.read_text(encoding="utf-8"), active.read_text(encoding="utf-8"), active)

    def test_agents_and_claude_shared_repo_rules_stay_equivalent(self) -> None:
        agents = (ROOT / "i18n/en/AGENTS.md").read_text(encoding="utf-8")
        claude = (ROOT / "i18n/en/CLAUDE.md").read_text(encoding="utf-8")
        shared_rule_anchors = [
            "`raw/{papers,notes,web}` are user-owned, read-only",
            "Skills append only to `raw/discovered/` or `raw/tmp/`",
            "`wiki/graph/` is derived",
            "Modify only via `tools/research_wiki.py`",
            "`wiki/log.md` is append-only",
            "Never rewrite in place",
            "User-facing skill flags",
            "Do not invent, flip, or drop them based on repo state",
            "runtime/schema/entities.yaml",
            "runtime/templates/{kind}.md.tmpl",
            "runtime/schema/edges.yaml",
            "runtime/schema/xref.yaml",
            "runtime/schema/conventions.yaml",
            "runtime/policy/writers.yaml",
            "runtime/CLAUDE.md",
            "Prefer in order: `.venv/bin/python`",
            "Tools auto-load API keys from `~/.env` and project-root `.env` via `tools/_env.py`",
            "`i18n/<lang>/skills`",
            ".claude/skills",
            ".agents/skills",
        ]
        for anchor in shared_rule_anchors:
            self.assertIn(anchor, agents, anchor)
            self.assertIn(anchor, claude, anchor)

    def test_i18n_agents_sandbox_tables_stay_aligned(self) -> None:
        def sandbox_table(path: Path) -> dict[str, tuple[str, str]]:
            text = path.read_text(encoding="utf-8")
            rows: dict[str, tuple[str, str]] = {}
            for match in re.finditer(
                r"\| `tools/([^`]+)` \| `([^`]+)` \| \"([^\"]+)\" \|",
                text,
            ):
                rows[match.group(1)] = (match.group(2), match.group(3))
            return rows

        en_rows = sandbox_table(ROOT / "i18n/en/AGENTS.md")
        zh_rows = sandbox_table(ROOT / "i18n/zh/AGENTS.md")
        self.assertEqual(en_rows, zh_rows)
        self.assertIn("discover.py", en_rows)
        self.assertIn("daily_arxiv.py", en_rows)
        self.assertIn("prepare_paper_source.py", en_rows)
        self.assertIn("backfill_citations.py", en_rows)

    def test_codex_skill_frontmatter_is_complete(self) -> None:
        for skill_dir in sorted((ROOT / ".agents/skills").iterdir()):
            if not skill_dir.is_dir() or skill_dir.name == "shared-references":
                continue
            skill = skill_dir / "SKILL.md"
            text = skill.read_text(encoding="utf-8").splitlines()[:8]
            self.assertIn(f"name: {skill_dir.name}", text, skill)
            self.assertTrue(any(line.startswith("description: ") for line in text), skill)

    def test_smoke_matrix_mentions_every_repo_skill(self) -> None:
        matrix = (ROOT / "docs/codex-smoke-test-matrix.md").read_text(encoding="utf-8")
        skills = sorted(path.name for path in (ROOT / "i18n/en/skills").iterdir() if path.is_dir())
        missing = [name for name in skills if f"${name}" not in matrix]
        self.assertEqual(missing, [])

    def test_smoke_matrix_uses_project_python_resolution(self) -> None:
        matrix = (ROOT / "docs/codex-smoke-test-matrix.md").read_text(encoding="utf-8")
        self.assertIn('PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"', matrix)
        self.assertIn('"$PYTHON_BIN" -m unittest', matrix)
        self.assertIn('"$PYTHON_BIN" -m json.tool', matrix)
        self.assertNotIn("python -m unittest", matrix)
        self.assertNotIn("python -m json.tool", matrix)

    def test_daily_arxiv_codex_schema_is_strict_and_inform_only(self) -> None:
        schema = json.loads((ROOT / ".github/codex/daily-arxiv-decisions.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["provider"]["const"], "codex")
        self.assertEqual(schema["properties"]["mode"]["const"], "inform")
        self.assertEqual(set(schema["required"]), set(schema["properties"]))
        decision_schema = schema["properties"]["decisions"]["items"]["properties"]["decision"]
        self.assertEqual(set(decision_schema["enum"]), {"strong_recommend", "maybe", "skip"})

    def test_daily_arxiv_workflow_declares_codex_inform_boundary(self) -> None:
        workflow = (ROOT / ".github/workflows/daily-arxiv.yml").read_text(encoding="utf-8")
        self.assertIn("recommender:", workflow)
        self.assertIn("HAS_CODEX_AUTH", workflow)
        self.assertIn("Build compact context for Codex", workflow)
        self.assertIn("codex --ask-for-approval never", workflow)
        self.assertIn("full Codex CI ingest orchestration and push are verified", workflow)
        self.assertIn('steps.resolve.outputs.mode == \'inform\'', workflow)
        self.assertIn('[ "$DAILY_ARXIV_RECOMMENDER" != "auto" ]', workflow)
        self.assertIn('[ "$DAILY_ARXIV_RECOMMENDER" != "claude-action" ]', workflow)
        self.assertIn("Codex, review-llm, and tool recommenders are inform-mode only", workflow)
        self.assertIn('if [ "$DAILY_ARXIV_MODE" = "auto-ingest" ] && [ "$HAS_CLAUDE_CODE_AUTH" != "true" ]', workflow)
        self.assertIn("git add -f wiki raw/discovered", workflow)

        codex_step_names = (
            "Build compact context for Codex",
            "Setup Node for Codex",
            "Install Codex CLI",
            "Authenticate Codex CLI",
            "Run Codex recommendation",
        )
        for name in codex_step_names:
            pos = workflow.index(f"- name: {name}")
            next_step = workflow.find("\n      - name:", pos + 1)
            block = workflow[pos : next_step if next_step != -1 else len(workflow)]
            self.assertIn("steps.resolve.outputs.mode == 'inform'", block, name)

    def test_daily_arxiv_workflow_credentials_guard_is_executable(self) -> None:
        workflow = (ROOT / ".github/workflows/daily-arxiv.yml").read_text(encoding="utf-8")
        step_start = workflow.index("      - name: Validate recommender credentials")
        run_start = workflow.index("        run: |\n", step_start) + len("        run: |\n")
        next_step = workflow.find("\n      - name:", run_start)
        raw_script = workflow[run_start : next_step if next_step != -1 else len(workflow)]
        script = "\n".join(
            line[10:] if line.startswith("          ") else line
            for line in raw_script.splitlines()
        )

        def run_guard(mode: str, recommender: str, *, codex: bool = False, claude: bool = False, review: bool = False) -> subprocess.CompletedProcess[str]:
            env = os.environ.copy()
            env.update(
                {
                    "DAILY_ARXIV_MODE": mode,
                    "DAILY_ARXIV_RECOMMENDER": recommender,
                    "HAS_CODEX_AUTH": "true" if codex else "false",
                    "HAS_CLAUDE_CODE_AUTH": "true" if claude else "false",
                    "HAS_REVIEW_LLM": "true" if review else "false",
                }
            )
            return subprocess.run(
                ["bash", "-c", script],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        codex_auto = run_guard("auto-ingest", "codex", codex=True, claude=True)
        self.assertEqual(codex_auto.returncode, 1)
        self.assertIn("inform-mode only", codex_auto.stdout)

        review_auto = run_guard("auto-ingest", "review-llm", claude=True, review=True)
        self.assertEqual(review_auto.returncode, 1)
        self.assertIn("inform-mode only", review_auto.stdout)

        tool_auto = run_guard("auto-ingest", "tool", claude=True)
        self.assertEqual(tool_auto.returncode, 1)
        self.assertIn("inform-mode only", tool_auto.stdout)

        missing_claude = run_guard("auto-ingest", "auto", codex=True)
        self.assertEqual(missing_claude.returncode, 1)
        self.assertIn("requires legacy Claude Code Action auth", missing_claude.stdout)

        self.assertEqual(run_guard("auto-ingest", "auto", claude=True).returncode, 0)
        self.assertEqual(run_guard("auto-ingest", "claude-action", claude=True).returncode, 0)

        no_codex_auth = run_guard("inform", "codex")
        self.assertEqual(no_codex_auth.returncode, 1)
        self.assertIn("recommender=codex requires", no_codex_auth.stdout)
        self.assertEqual(run_guard("inform", "codex", codex=True).returncode, 0)

        no_review_auth = run_guard("inform", "review-llm")
        self.assertEqual(no_review_auth.returncode, 1)
        self.assertIn("recommender=review-llm requires", no_review_auth.stdout)
        self.assertEqual(run_guard("inform", "review-llm", review=True).returncode, 0)
        self.assertEqual(run_guard("inform", "tool").returncode, 0)

    def test_daily_arxiv_writeback_rehearsal_stages_only_ingest_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-writeback-smoke.") as tmp:
            repo = Path(tmp)
            for path in (
                repo / "wiki/papers",
                repo / "raw/discovered",
                repo / "raw/tmp",
                repo / "raw/papers",
                repo / ".daily-arxiv/run",
            ):
                path.mkdir(parents=True, exist_ok=True)
            (repo / "wiki/index.md").write_text("papers: []\n", encoding="utf-8")
            (repo / "raw/discovered/.gitkeep").write_text("", encoding="utf-8")
            (repo / "raw/tmp/.gitkeep").write_text("", encoding="utf-8")
            (repo / "raw/papers/.gitkeep").write_text("", encoding="utf-8")
            (repo / ".gitignore").write_text(
                "\n".join(
                    [
                        ".daily-arxiv/",
                        "raw/discovered/*",
                        "!raw/discovered/.gitkeep",
                        "raw/tmp/*",
                        "!raw/tmp/.gitkeep",
                        "raw/papers/*",
                        "!raw/papers/.gitkeep",
                        "wiki/papers/*",
                        "!wiki/papers/.gitkeep",
                        "wiki/graph/*",
                        "!wiki/graph/.gitkeep",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            commands = [
                ["git", "init", "-q"],
                ["git", "config", "user.name", "Smoke Test"],
                ["git", "config", "user.email", "smoke@example.invalid"],
                ["git", "add", "wiki", "raw"],
                ["git", "commit", "-q", "-m", "initial"],
            ]
            for command in commands:
                proc = subprocess.run(command, cwd=repo, capture_output=True, text=True, check=False)
                self.assertEqual(proc.returncode, 0, proc.stderr)

            (repo / "wiki/papers/codex-writeback.md").write_text("# Codex writeback\n", encoding="utf-8")
            (repo / "raw/discovered/codex-writeback.tex").write_text("\\section{Fetched}\n", encoding="utf-8")
            (repo / "raw/tmp/prepared-sidecar.tex").write_text("\\section{Temp}\n", encoding="utf-8")
            (repo / "raw/papers/user-owned.tex").write_text("\\section{User}\n", encoding="utf-8")
            (repo / ".daily-arxiv/run/digest.md").write_text("scratch digest\n", encoding="utf-8")

            proc = subprocess.run(["git", "add", "-f", "wiki", "raw/discovered"], cwd=repo, capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            staged = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(staged.returncode, 0, staged.stderr)
            self.assertEqual(
                staged.stdout.splitlines(),
                ["raw/discovered/codex-writeback.tex", "wiki/papers/codex-writeback.md"],
            )
            unstaged_before_commit = subprocess.run(
                ["git", "status", "--short", "--ignored"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(unstaged_before_commit.returncode, 0, unstaged_before_commit.stderr)
            self.assertIn("!! .daily-arxiv/", unstaged_before_commit.stdout)
            self.assertIn("!! raw/papers/user-owned.tex", unstaged_before_commit.stdout)
            self.assertIn("!! raw/tmp/prepared-sidecar.tex", unstaged_before_commit.stdout)

            proc = subprocess.run(["git", "commit", "-q", "-m", "daily-arxiv auto-ingest"], cwd=repo, capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            unstaged = subprocess.run(["git", "status", "--short", "--ignored"], cwd=repo, capture_output=True, text=True, check=False)
            self.assertEqual(unstaged.returncode, 0, unstaged.stderr)
            self.assertIn("!! .daily-arxiv/", unstaged.stdout)
            self.assertIn("!! raw/papers/user-owned.tex", unstaged.stdout)
            self.assertIn("!! raw/tmp/prepared-sidecar.tex", unstaged.stdout)

    def test_daily_arxiv_finalizer_keeps_auto_ingest_high_confidence_only(self) -> None:
        daily_arxiv = self._load_daily_arxiv_without_sandbox()

        context = {
            "mode": "auto-ingest",
            "config": {"mode": "auto-ingest", "max_auto_ingest": 1, "max_recommendations": 10},
            "candidates": [
                {
                    "arxiv_id": "2501.00001",
                    "title": "High confidence candidate",
                    "arxiv_url": "https://arxiv.org/abs/2501.00001",
                    "is_known": False,
                    "tool_rank_score": 0.2,
                    "signals": {},
                },
                {
                    "arxiv_id": "2501.00002",
                    "title": "Medium confidence candidate",
                    "arxiv_url": "https://arxiv.org/abs/2501.00002",
                    "is_known": False,
                    "tool_rank_score": 0.9,
                    "signals": {},
                },
            ],
        }
        decisions = {
            "decisions": [
                {"arxiv_id": "2501.00001", "decision": "ingest", "confidence": "high", "score": 0.2},
                {"arxiv_id": "2501.00002", "decision": "ingest", "confidence": "medium", "score": 0.9},
            ]
        }
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as fh:
            json.dump(decisions, fh)
            fh.flush()
            payload = daily_arxiv.finalize_payload(context, Path(fh.name))

        selected = payload["auto_ingest"]["selected"]
        self.assertEqual([item["arxiv_id"] for item in selected], ["2501.00001"])
        medium = next(item for item in payload["candidates"] if item["arxiv_id"] == "2501.00002")
        self.assertIn("auto_ingest_blocked", medium)

    def test_daily_arxiv_inform_mode_never_selects_auto_ingest(self) -> None:
        daily_arxiv = self._load_daily_arxiv_without_sandbox()

        context = {
            "mode": "inform",
            "config": {"mode": "inform", "max_auto_ingest": 1, "max_recommendations": 10},
            "candidates": [
                {
                    "arxiv_id": "2501.00003",
                    "title": "Invalid inform ingest candidate",
                    "arxiv_url": "https://arxiv.org/abs/2501.00003",
                    "is_known": False,
                    "tool_rank_score": 0.9,
                    "signals": {},
                }
            ],
        }
        decisions = {
            "decisions": [
                {"arxiv_id": "2501.00003", "decision": "ingest", "confidence": "high", "score": 0.9}
            ]
        }
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as fh:
            json.dump(decisions, fh)
            fh.flush()
            payload = daily_arxiv.finalize_payload(context, Path(fh.name))

        self.assertFalse(payload["auto_ingest"]["enabled"])
        self.assertEqual(payload["auto_ingest"]["selected"], [])
        self.assertIn("auto_ingest_blocked", payload["candidates"][0])

    def test_daily_arxiv_local_inform_helpers_do_not_require_network_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-daily-local.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            feed = root / "feed.json"
            context = root / "recommendation-context.json"
            compact = root / "codex-context.json"
            digest_md = root / "digest.md"
            digest_json = root / "digest.json"
            feed.write_text(
                json.dumps(
                    [
                        {
                            "arxiv_id": "2601.00001",
                            "title": "Tiny Codex Daily Arxiv Fixture",
                            "authors": ["Smoke Tester"],
                            "category": "cs.LG",
                            "published": "2026-07-08T00:00:00Z",
                            "summary": "A deterministic local feed item for inform-mode helper validation.",
                            "arxiv_url": "https://arxiv.org/abs/2601.00001",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            prepare = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/daily_arxiv.py"),
                    "prepare",
                    "--feed",
                    str(feed),
                    "--wiki-root",
                    str(wiki),
                    "--out",
                    str(context),
                    "--mode",
                    "inform",
                    "--max-recommendations",
                    "1",
                    "--no-external",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(prepare.returncode, 0, prepare.stderr)
            self.assertNotIn("SANDBOX GATE", prepare.stderr)
            self.assertTrue(context.exists())

            compact_proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/daily_arxiv.py"),
                    "compact-context",
                    "--context",
                    str(context),
                    "--out",
                    str(compact),
                    "--limit",
                    "1",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(compact_proc.returncode, 0, compact_proc.stderr)
            self.assertNotIn("SANDBOX GATE", compact_proc.stderr)

            finalize = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/daily_arxiv.py"),
                    "finalize",
                    "--context",
                    str(context),
                    "--out-md",
                    str(digest_md),
                    "--out-json",
                    str(digest_json),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(finalize.returncode, 0, finalize.stderr)
            self.assertNotIn("SANDBOX GATE", finalize.stderr)

            context_payload = json.loads(context.read_text(encoding="utf-8"))
            compact_payload = json.loads(compact.read_text(encoding="utf-8"))
            digest_payload = json.loads(digest_json.read_text(encoding="utf-8"))
            self.assertEqual(context_payload["mode"], "inform")
            self.assertEqual(context_payload["counts"]["new_candidates"], 1)
            self.assertEqual(compact_payload["candidates"][0]["arxiv_id"], "2601.00001")
            self.assertFalse(digest_payload["auto_ingest"]["enabled"])
            self.assertIn("Tiny Codex Daily Arxiv Fixture", digest_md.read_text(encoding="utf-8"))

    def test_reset_raw_scope_preserves_user_owned_raw_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-reset-raw.") as tmp:
            root = Path(tmp)
            for subdir in ("papers", "notes", "web", "discovered", "tmp"):
                path = root / "raw" / subdir
                path.mkdir(parents=True)
                (path / ".gitkeep").write_text("", encoding="utf-8")

            user_files = {
                root / "raw/papers/user-paper.pdf": b"%PDF-user-owned",
                root / "raw/notes/user-note.md": b"# user note\n",
                root / "raw/web/user-page.md": b"# user web capture\n",
            }
            generated_files = {
                root / "raw/discovered/generated.tex": b"\\section{generated}\n",
                root / "raw/tmp/sidecar.json": b"{}\n",
            }
            for path, content in {**user_files, **generated_files}.items():
                path.write_bytes(content)

            plan = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/reset_wiki.py"),
                    "--scope",
                    "raw",
                    "--project-root",
                    str(root),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(plan.returncode, 0, plan.stderr)
            plan_payload = json.loads(plan.stdout)
            self.assertEqual(plan_payload["status"], "plan")
            self.assertEqual(
                sorted(plan_payload["delete_files"]),
                ["raw/discovered/generated.tex", "raw/tmp/sidecar.json"],
            )
            self.assertIn("preserve user-owned raw/papers, raw/notes, and raw/web", plan_payload["actions"])

            execute = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/reset_wiki.py"),
                    "--scope",
                    "raw",
                    "--project-root",
                    str(root),
                    "--yes",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(execute.returncode, 0, execute.stderr)
            execute_payload = json.loads(execute.stdout)
            self.assertEqual(execute_payload["deleted_files"], 2)

            for path, content in user_files.items():
                self.assertTrue(path.exists(), path)
                self.assertEqual(path.read_bytes(), content)
            for path in generated_files:
                self.assertFalse(path.exists(), path)

    def test_edit_fixture_updates_wiki_and_only_generated_raw_dirs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-edit.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            for path, content in {
                raw / "papers/user-paper.tex": "\\section{User paper}\n",
                raw / "notes/user-note.md": "# User note\n",
                raw / "web/user-page.html": "<p>User web source</p>\n",
            }.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            (raw / "discovered").mkdir(parents=True)
            (raw / "tmp").mkdir(parents=True)
            user_owned_before = {
                path.relative_to(raw): path.read_bytes()
                for base in (raw / "papers", raw / "notes", raw / "web")
                for path in base.rglob("*")
                if path.is_file()
            }

            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            concept = wiki / "concepts/codex-edit-concept.md"
            concept.write_text(
                """---
title: Codex Edit Concept
tags: [codex, edit]
maturity: active
key_papers: []
aliases: []
linked_ideas: []
---

## Definition
Original definition.

## Variants

## Comparison

## Known limitations

## Open problems
""",
                encoding="utf-8",
            )

            concept.write_text(
                concept.read_text(encoding="utf-8").replace(
                    "Original definition.",
                    "Original definition.\n\nGenerated edit note: [[codex-edit-concept]] keeps user-owned raw sources read-only.",
                    1,
                ),
                encoding="utf-8",
            )
            (raw / "discovered/codex-edit-source.tex").write_text(
                "\\section{Generated source for later ingest}\n",
                encoding="utf-8",
            )
            (raw / "tmp/codex-edit-web-extract.md").write_text(
                "# Generated temporary web extract\n",
                encoding="utf-8",
            )
            log = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "log",
                    str(wiki),
                    "edit | updated codex-edit-concept and prepared generated raw inputs",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(log.returncode, 0, log.stderr)

            user_owned_after = {
                path.relative_to(raw): path.read_bytes()
                for base in (raw / "papers", raw / "notes", raw / "web")
                for path in base.rglob("*")
                if path.is_file()
            }
            self.assertEqual(user_owned_before, user_owned_after)
            self.assertTrue((raw / "discovered/codex-edit-source.tex").is_file())
            self.assertTrue((raw / "tmp/codex-edit-web-extract.md").is_file())
            self.assertFalse(any((raw / "papers").glob("codex-*")))
            self.assertFalse(any((raw / "notes").glob("codex-*")))
            self.assertFalse(any((raw / "web").glob("codex-*")))
            self.assertIn("Generated edit note", concept.read_text(encoding="utf-8"))
            self.assertIn("edit | updated codex-edit-concept", (wiki / "log.md").read_text(encoding="utf-8"))

    def test_sandbox_gate_matches_agents_escalation_contract(self) -> None:
        tree = ast.parse((ROOT / "tools/_sandbox.py").read_text(encoding="utf-8"))
        justifications = None
        for node in tree.body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "JUSTIFICATIONS":
                justifications = ast.literal_eval(node.value)
                break
        self.assertIsInstance(justifications, dict)

        agents = (ROOT / "i18n/en/AGENTS.md").read_text(encoding="utf-8")
        for tool, justification in justifications.items():
            self.assertIn(f"`tools/{tool}`", agents)
            self.assertIn(f'"{justification}"', agents)

    def test_sandbox_gate_prints_actionable_prefix_rule(self) -> None:
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import socket, sys; "
                    "socket.socket = lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError('blocked')); "
                    "sys.argv = ['tools/discover.py']; "
                    f"sys.path.insert(0, {str(ROOT / 'tools')!r}); "
                    "import _sandbox"
                ),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(probe.returncode, 126)
        self.assertIn("SANDBOX GATE: discover.py needs network access", probe.stderr)
        self.assertIn('sandbox_permissions = "require_escalated"', probe.stderr)
        self.assertIn('justification = "AutoSci discover needs network access (S2/DeepXiv)"', probe.stderr)
        self.assertIn(f'prefix_rule = ["{sys.executable}", "tools/discover.py"]', probe.stderr)

    def test_fetch_s2_rate_limit_retry_is_env_configurable(self) -> None:
        env = os.environ.copy()
        env["S2_MAX_RETRIES"] = "2"
        env["S2_RATE_LIMIT_WAIT_SECONDS"] = "0"
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json, sys, types\n"
                    "sys.path.insert(0, 'tools')\n"
                    "sys.modules['_sandbox'] = types.ModuleType('_sandbox')\n"
                    "class Resp:\n"
                    "    status_code = 429\n"
                    "    def raise_for_status(self):\n"
                    "        raise RuntimeError('unexpected')\n"
                    "class Requests:\n"
                    "    def request(self, *args, **kwargs):\n"
                    "        return Resp()\n"
                    "sys.modules['requests'] = Requests()\n"
                    "import fetch_s2\n"
                    "sleeps = []\n"
                    "fetch_s2.time.sleep = sleeps.append\n"
                    "try:\n"
                    "    fetch_s2.paper('2106.09685')\n"
                    "except RuntimeError as exc:\n"
                    "    print(json.dumps({'message': str(exc), 'max_retries': fetch_s2.MAX_RETRIES, 'wait': fetch_s2.RATE_LIMIT_WAIT_SECONDS, 'sleeps': sleeps}))\n"
                ),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(probe.returncode, 0, probe.stderr)
        payload = json.loads(probe.stdout)
        self.assertEqual(payload["max_retries"], 2)
        self.assertEqual(payload["wait"], 0)
        self.assertIn("S2 API rate limited after 2 retries", payload["message"])
        self.assertEqual(payload["sleeps"], [3.0, 0, 0])

        daily_arxiv = (ROOT / "tools/daily_arxiv.py").read_text(encoding="utf-8")
        self.assertIn('os.environ.setdefault("S2_MAX_RETRIES", "1")', daily_arxiv)
        self.assertIn('os.environ.setdefault("S2_RATE_LIMIT_WAIT_SECONDS", "5")', daily_arxiv)

    def test_high_risk_skills_have_codex_safe_sequential_fallbacks(self) -> None:
        ideate = (ROOT / ".agents/skills/ideate/SKILL.md").read_text(encoding="utf-8")
        research = (ROOT / ".agents/skills/research/SKILL.md").read_text(encoding="utf-8")
        novelty = (ROOT / ".agents/skills/novelty/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Codex-safe default", ideate)
        self.assertIn("run the same steps sequentially", ideate)
        self.assertIn("Codex-safe default", research)
        self.assertIn("run the three searches sequentially", research)
        self.assertIn("Codex-safe default", novelty)
        self.assertIn("run them sequentially", novelty)

    def test_i18n_sources_preserve_codex_migration_boundaries(self) -> None:
        pairs = {
            "skills/ideate/SKILL.md": ["Codex-safe default", "Codex-safe 默认"],
            "skills/novelty/SKILL.md": ["Codex-safe default", "Codex-safe 默认"],
            "skills/research/SKILL.md": ["$exp-status --collect-ready", "$exp-status --collect-ready"],
            "skills/exp-status/SKILL.md": ["external scheduler", "外部调度器"],
            "skills/exp-run/SKILL.md": ["User inspection gate", "用户检查门控"],
            "skills/exp-pilot-run/SKILL.md": ["User inspection gate", "用户检查门控"],
            "skills/exp-design/SKILL.md": ["`/exp-run` / `$exp-run`", "`/exp-run` / `$exp-run`"],
            "skills/review/SKILL.md": ["$ask", "$ask"],
            "skills/paper-plan/SKILL.md": ["$paper-compile", "$paper-compile"],
            "skills/poster/SKILL.md": ["$paper-draft", "$paper-draft"],
            "skills/paper-draft/SKILL.md": ["$research", "$research"],
            "skills/paper-compile/SKILL.md": ["$research", "$research"],
            "skills/review/SKILL.md": ["$exp-design --review", "$exp-design --review"],
            "skills/daily-arxiv/SKILL.md": ["$daily-arxiv setup", "$daily-arxiv setup"],
            "skills/daily-arxiv/references/automation-scaffold.md": ["Workflow Env Exposures", "Workflow Env Exposures"],
        }
        for rel, (en_expected, zh_expected) in pairs.items():
            self.assertIn(en_expected, (ROOT / "i18n/en" / rel).read_text(encoding="utf-8"), rel)
            self.assertIn(zh_expected, (ROOT / "i18n/zh" / rel).read_text(encoding="utf-8"), rel)

    def test_obsolete_runtime_phrases_do_not_reappear_in_sources(self) -> None:
        obsolete = [
            "/run-experiment",
            "use Agent tool",
            "Agent tool 并发",
            "`Agent` tool",
            "CLAUDE.md template",
            "CLAUDE.md 模板",
            "CLAUDE.md rule",
            "CLAUDE.md 规则",
            "CronCreate",
            "auto-creates CronCreate",
            "automatically sets up a CronCreate",
            "automatically trigger Stage 4",
            "/query",
            "$query",
            "query workflow",
            "via Skill tool",
            "Skill tool",
            "通过 Skill tool",
            "Skill:",
            "Args:",
            "Skill: exp-run",
            "Skill: research",
            "`Skill` — call sub-skills",
            "`Skill` — 调用子 skills",
            "`Skill` — call ",
            "`Skill` — 调用",
        ]
        paths = [
            *Path(ROOT / "i18n/en").rglob("*.md"),
            *Path(ROOT / "i18n/zh").rglob("*.md"),
            ROOT / "config/server.yaml.example",
        ]
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for phrase in obsolete:
                self.assertNotIn(phrase, text, path)

    def test_research_scheduler_language_is_runtime_neutral(self) -> None:
        research = (ROOT / ".agents/skills/research/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Runtimes with a scheduler", research)
        self.assertIn("Codex should use manual `$exp-status --collect-ready`", research)
        self.assertIn("external schedulers report `stage4 ready`", research)
        self.assertIn("$research --start-from stage4", research)
        self.assertIn("$research --start-from stage3-collect", research)
        self.assertIn("corresponding slash command or Codex `$skill` workflow", research)
        self.assertIn("Slash command or Codex `$skill` workflow invocation", research)
        self.assertIn("$paper-plan", research)
        self.assertNotIn("CronCreate", research)

    def test_every_skill_source_exposes_codex_invocation(self) -> None:
        for lang in ("en", "zh"):
            for path in sorted((ROOT / f"i18n/{lang}/skills").glob("*/SKILL.md")):
                text = path.read_text(encoding="utf-8")
                self.assertRegex(text, r"\$[a-z][a-z-]*", path)

    def test_research_pipeline_progress_resume_fields_are_cli_safe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-research-progress.") as tmp:
            wiki = Path(tmp) / "wiki"
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            progress = wiki / "outputs/pipeline-progress.md"
            progress.parent.mkdir(parents=True, exist_ok=True)
            progress.write_text(
                """---
slug: codex-research-progress
direction: tiny Codex research progress fixture
status: running
current_stage: stage1
started: 2026-07-08
mode: auto
skip_paper: true
venue: ""
idea_slug: ""
experiment_slugs: []
stage3a_deployed: []
linked_idea_slugs: []
iteration_count: 0
---
## Stage Log
- Stage 0 (Bootstrap): skipped
- Stage 1: pending
- Gate 1: pending
- Stage 2: pending
- Stage 3a (Deploy): pending
- Stage 3b (Await): pending
- Stage 3c (Collect): pending
- Stage 4: pending
- Gate 2: pending
- Stage 5: skipped
""",
                encoding="utf-8",
            )

            updates = (
                ("current_stage", "stage3-await"),
                ("idea_slug", "codex-progress-idea"),
                ("experiment_slugs", "[codex-progress-baseline, codex-progress-validation]"),
                ("stage3a_deployed", "[codex-progress-baseline, codex-progress-validation]"),
                ("linked_idea_slugs", "[codex-progress-idea]"),
                ("iteration_count", "1"),
            )
            for field, value in updates:
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), "set-meta", str(progress), field, value],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)

            append_log = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "log",
                    str(wiki),
                    "research | stage3b | awaiting 2 experiments | pipeline: codex-research-progress",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(append_log.returncode, 0, append_log.stderr)

            meta = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "read-meta", str(progress)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(meta.returncode, 0, meta.stderr)
            payload = json.loads(meta.stdout)
            self.assertEqual(payload["status"], "running")
            self.assertEqual(payload["current_stage"], "stage3-await")
            self.assertEqual(payload["idea_slug"], "codex-progress-idea")
            self.assertEqual(payload["experiment_slugs"], ["codex-progress-baseline", "codex-progress-validation"])
            self.assertEqual(payload["stage3a_deployed"], ["codex-progress-baseline", "codex-progress-validation"])
            self.assertEqual(payload["linked_idea_slugs"], ["codex-progress-idea"])
            self.assertEqual(payload["iteration_count"], 1)
            self.assertIn("research | stage3b | awaiting 2 experiments", (wiki / "log.md").read_text(encoding="utf-8"))

            complete = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "set-meta", str(progress), "status", "completed"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(complete.returncode, 0, complete.stderr)
            status = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "read-meta", str(progress), "status"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertEqual(json.loads(status.stdout), "completed")

    def test_research_prepared_stage_orchestration_reaches_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-research-orchestration.") as tmp:
            wiki = Path(tmp) / "wiki"
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            pipeline_slug = "codex-prepared-research"
            idea_slug = "codex-orchestration-idea"
            exp_slug = "codex-orchestration-exp"
            progress = wiki / "outputs/pipeline-progress.md"
            progress.write_text(
                f"""---
slug: {pipeline_slug}
direction: prepared Codex research orchestration fixture
status: running
current_stage: stage3-await
started: 2026-07-08
mode: auto
skip_paper: true
venue: ""
idea_slug: {idea_slug}
experiment_slugs: [{exp_slug}]
stage3a_deployed: [{exp_slug}]
linked_idea_slugs: []
iteration_count: 0
---
## Stage Log
- Stage 0 (Bootstrap): skipped
- Stage 1: completed
- Gate 1: passed
- Stage 2: completed
- Stage 3a (Deploy): completed
- Stage 3b (Await): completed
- Stage 3c (Collect): pending
- Stage 4: pending
- Gate 2: skipped
- Stage 5: skipped
""",
                encoding="utf-8",
            )
            (wiki / f"ideas/{idea_slug}.md").write_text(
                f"""---
title: Codex Orchestration Idea
slug: {idea_slug}
status: tested
origin: local research orchestration smoke fixture
origin_gaps: []
tags: [codex, research]
priority: 3
novelty_score: 4
pilot_result: pass
failure_reason: ""
linked_experiments: [{exp_slug}]
date_proposed: 2026-07-08
date_resolved: ""
---

## Motivation
Exercise prepared `$research` orchestration.

## Hypothesis
The prepared pipeline can collect an experiment, evaluate it, and write a final report.

## Approach sketch
Use deterministic local evidence.

## Novelty argument
Smoke fixture only.

## Target venue

## Risks

## Pilot results
pass

## Lessons learned
""",
                encoding="utf-8",
            )
            exp_path = wiki / f"experiments/{exp_slug}.md"
            exp_path.write_text(
                f"""---
title: Codex Orchestration Exp
slug: {exp_slug}
status: running
linked_idea: {idea_slug}
evaluates_methods: []
hypothesis: The prepared pipeline reaches a final report.
tags: [codex, research]
setup:
  model: smoke
  dataset: fixture
  hardware: local
  framework: none
metrics: [accuracy]
baseline: deterministic baseline
outcome: ""
key_result: ""
date_planned: 2026-07-08
date_completed: ""
run_log: logs/{exp_slug}.log
started: "2026-07-08T00:00:00"
estimated_hours: 0
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Objective
Check the `$research --start-from stage3-collect` prepared path.

## Setup
Deterministic local fixture.

## Procedure
Collect result, evaluate the linked idea, and generate a report.

## Results

## Analysis

## Idea updates

## Follow-up
""",
                encoding="utf-8",
            )

            for field, value in (
                ("outcome", "succeeded"),
                ("key_result", "Prepared research pipeline collected a successful experiment."),
            ):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), "set-meta", str(exp_path), field, value],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)

            complete_exp = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "transition",
                    str(exp_path),
                    "--to",
                    "completed",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(complete_exp.returncode, 0, complete_exp.stderr)

            for field, value in (("current_stage", "stage4"),):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), "set-meta", str(progress), field, value],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
            stage3_log = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "log",
                    str(wiki),
                    f"research | stage3c | collected 1 experiments | pipeline: {pipeline_slug}",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(stage3_log.returncode, 0, stage3_log.stderr)

            validate_idea = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "transition",
                    str(wiki / f"ideas/{idea_slug}.md"),
                    "--to",
                    "validated",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(validate_idea.returncode, 0, validate_idea.stderr)
            add_support = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "add-edge",
                    str(wiki),
                    "--from",
                    f"experiments/{exp_slug}",
                    "--to",
                    f"ideas/{idea_slug}",
                    "--type",
                    "supports",
                    "--evidence",
                    "Prepared research pipeline collected a successful experiment.",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(add_support.returncode, 0, add_support.stderr)

            exp_text = exp_path.read_text(encoding="utf-8")
            exp_path.write_text(
                exp_text.replace(
                    "## Idea updates\n",
                    (
                        "## Idea updates\n"
                        "- **Verdict**: supported\n"
                        f"- **Linked idea**: [[{idea_slug}]] status tested -> validated\n"
                        "- **Judge agreement**: mocked prepared research fixture only\n"
                        "- **Date**: 2026-07-08\n"
                    ),
                ),
                encoding="utf-8",
            )
            for field, value in (
                ("linked_idea_slugs", f"[{idea_slug}]"),
                ("current_stage", "completed"),
                ("status", "completed"),
            ):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), "set-meta", str(progress), field, value],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)

            report = wiki / "outputs/PIPELINE_REPORT.md"
            report.write_text(
                f"""# Research Pipeline Report

## Stage Summary
| Stage | Status | Duration |
|-------|--------|----------|
| Stage 3c: Collect Results | completed | fixture |
| Stage 4: Verdict | completed | fixture |
| Stage 5: Paper Writing | skipped | --skip-paper |

## Selected Idea
- **Idea**: [[{idea_slug}]] — Codex Orchestration Idea

## Experiment Results
| Experiment | Outcome | Key Result |
|-----------|---------|------------|
| [[{exp_slug}]] | succeeded | Prepared research pipeline collected a successful experiment. |

## Deliverables
- Ideas: 1 validated
- Experiments: 1 completed
- Paper: skipped
""",
                encoding="utf-8",
            )
            final_log = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "log",
                    str(wiki),
                    f"research | completed | idea: {idea_slug} | linked ideas: 1 updated | paper: no",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(final_log.returncode, 0, final_log.stderr)

            for command in ("rebuild-index", "rebuild-context-brief", "rebuild-open-questions"):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), command, str(wiki)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)

            progress_meta = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "read-meta", str(progress)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(progress_meta.returncode, 0, progress_meta.stderr)
            progress_payload = json.loads(progress_meta.stdout)
            self.assertEqual(progress_payload["status"], "completed")
            self.assertEqual(progress_payload["current_stage"], "completed")
            self.assertEqual(progress_payload["linked_idea_slugs"], [idea_slug])

            idea_meta = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "read-meta", str(wiki / f"ideas/{idea_slug}.md")],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(idea_meta.returncode, 0, idea_meta.stderr)
            self.assertEqual(json.loads(idea_meta.stdout)["status"], "validated")

            report_text = report.read_text(encoding="utf-8")
            self.assertIn("Stage 4: Verdict | completed", report_text)
            self.assertIn(f"[[{idea_slug}]]", report_text)
            self.assertIn(f"[[{exp_slug}]] | succeeded", report_text)
            log_text = (wiki / "log.md").read_text(encoding="utf-8")
            self.assertIn("research | stage3c | collected 1 experiments", log_text)
            self.assertIn("research | completed | idea: codex-orchestration-idea", log_text)

            lint = subprocess.run(
                [sys.executable, str(ROOT / "tools/lint.py"), "--wiki-dir", str(wiki), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(lint.returncode, 0, lint.stderr)
            lint_payload = json.loads(lint.stdout)
            self.assertFalse(
                [issue for issue in lint_payload if issue.get("severity") == "🔴"],
                lint_payload,
            )

    def test_experiment_skills_keep_runtime_neutral_user_gates(self) -> None:
        exp_run = (ROOT / ".agents/skills/exp-run/SKILL.md").read_text(encoding="utf-8")
        pilot = (ROOT / ".agents/skills/exp-pilot-run/SKILL.md").read_text(encoding="utf-8")
        status = (ROOT / ".agents/skills/exp-status/SKILL.md").read_text(encoding="utf-8")

        for text in (exp_run, pilot):
            self.assertIn("User inspection gate", text)
            self.assertIn("explicit user approval", text)
            self.assertIn("**Post-approval sanity check**", text)
            self.assertLess(text.index("**Gate:"), text.index("**Post-approval sanity check**"))
            self.assertNotIn("Phase 1 sanity", text)
            self.assertNotIn("applicant", text.lower())

        self.assertIn("transition wiki/experiments/{slug}.md --to running", exp_run)
        self.assertIn("transition wiki/experiments/{slug}.md --to completed", exp_run)
        self.assertIn("set-meta wiki/experiments/{slug}.md remote.server", exp_run)
        self.assertIn("set-meta wiki/experiments/{slug}.md remote.session", exp_run)
        self.assertIn("set-meta wiki/experiments/{slug}.md remote.completed", exp_run)
        self.assertNotIn("Use five Edit calls", exp_run)
        self.assertNotIn("直接用 `Edit` 工具", exp_run)

        self.assertIn("Do not synthesize or create a Pilot Spec here", pilot)
        self.assertIn("$exp-pilot-eval", pilot)
        self.assertIn("$ideate", pilot)
        self.assertNotIn("create it following the steps", pilot)

        self.assertIn("Codex should use manual `$exp-status --collect-ready`", status)
        self.assertIn("Slash command or Codex `$skill` workflow invocation", status)
        self.assertIn("$research", status)
        self.assertIn("$exp-run --collect", status)
        self.assertIn("external scheduler", status)
        self.assertIn("collect-ready commands", status)
        self.assertIn("must not claim to have run `$exp-run --collect`", status)
        self.assertIn('report "stage4 ready"', status)
        self.assertIn("External schedulers do not invoke skills", status)
        self.assertIn("$research --start-from stage4", status)
        self.assertNotIn("Skill: exp-run", status)
        self.assertNotIn("Skill: research", status)
        self.assertIn("Codex-safe default", status)

    def test_research_wiki_local_init_and_check_are_temp_safe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-codex-smoke.") as tmp:
            wiki = Path(tmp) / "wiki"
            proc = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((wiki / "index.md").exists())
            self.assertTrue((wiki / "graph").is_dir())

            lint = subprocess.run(
                [sys.executable, str(ROOT / "tools/lint.py"), "--wiki-dir", str(wiki), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(lint.returncode, 0, lint.stderr)
            self.assertTrue(lint.stdout.strip())

    def test_ask_and_check_local_fixture_cover_read_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-ask-check-smoke.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw_papers = root / "raw/papers"
            raw_papers.mkdir(parents=True)
            raw_file = raw_papers / "user-owned-source.tex"
            raw_file.write_text("\\section{User-owned source}\n", encoding="utf-8")
            raw_before = raw_file.read_text(encoding="utf-8")

            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            (wiki / "papers/codex-context-smoke.md").write_text(
                """---
title: Codex Context Smoke
slug: codex-context-smoke
tags: [codex, retrieval]
importance: 3
---

## Problem & Context
This fixture checks whether Codex can retrieve local wiki evidence.

## Key idea
The paper links a concept for answer-only `$ask` retrieval.

## Method
The method is a deterministic local smoke test.

## Experiment & Results
The result should be visible in the compiled query pack.

## Limitations
It does not call external APIs.

## Open questions
- How should answer-only ask runs avoid durable writes?

## My take
Useful for migration validation.

## Related
- [[codex-retrieval-validation]]
""",
                encoding="utf-8",
            )
            (wiki / "concepts/codex-retrieval-validation.md").write_text(
                """---
title: Codex Retrieval Validation
tags: [codex, retrieval]
maturity: emerging
key_papers: [codex-context-smoke]
---

## Definition
Validation that answer-only retrieval can ground responses in local wiki pages.

## Intuition
The fixture should appear in context packs without modifying raw sources.

## Variants

## Comparison

## Known limitations

## Open problems

## Relationship to foundations

## Realized by

## My understanding
The concept is linked back to [[codex-context-smoke]].
""",
                encoding="utf-8",
            )

            add_edge = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "add-edge",
                    str(wiki),
                    "--from",
                    "papers/codex-context-smoke",
                    "--to",
                    "concepts/codex-retrieval-validation",
                    "--type",
                    "introduces_concept",
                    "--evidence",
                    "local ask/check smoke fixture",
                    "--confidence",
                    "high",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(add_edge.returncode, 0, add_edge.stderr)

            rebuild_context = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "rebuild-context-brief", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(rebuild_context.returncode, 0, rebuild_context.stderr)
            context_text = (wiki / "graph/context_brief.md").read_text(encoding="utf-8")
            self.assertIn("Codex Context Smoke", context_text)
            self.assertIn("concepts/codex-retrieval-validation", context_text)

            rebuild_questions = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "rebuild-open-questions", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(rebuild_questions.returncode, 0, rebuild_questions.stderr)
            questions_text = (wiki / "graph/open_questions.md").read_text(encoding="utf-8")
            self.assertIn("answer-only ask runs", questions_text)

            found = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "find",
                    str(wiki),
                    "concepts",
                    "--tags",
                    "retrieval",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(found.returncode, 0, found.stderr)
            self.assertIn("codex-retrieval-validation", found.stdout)

            stats = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "stats", str(wiki), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(stats.returncode, 0, stats.stderr)
            stats_payload = json.loads(stats.stdout)
            self.assertEqual(stats_payload["papers"], 1)
            self.assertEqual(stats_payload["concepts"], 1)
            self.assertEqual(stats_payload["edges"], 1)

            lint = subprocess.run(
                [sys.executable, str(ROOT / "tools/lint.py"), "--wiki-dir", str(wiki), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(lint.returncode, 0, lint.stderr)
            lint_payload = json.loads(lint.stdout)
            self.assertFalse(
                [issue for issue in lint_payload if issue.get("severity") == "🔴"],
                lint_payload,
            )
            self.assertEqual(raw_file.read_text(encoding="utf-8"), raw_before)

    def test_check_lint_report_and_dry_run_are_read_only_fix_is_explicit(self) -> None:
        def snapshot(base: Path) -> dict[str, bytes]:
            return {
                str(path.relative_to(base)): path.read_bytes()
                for path in sorted(base.rglob("*"))
                if path.is_file()
            }

        with tempfile.TemporaryDirectory(prefix="autosci-check-lint-smoke.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw/papers"
            raw.mkdir(parents=True)
            raw_file = raw / "user-owned-check.tex"
            raw_file.write_text("\\section{Do not touch raw}\n", encoding="utf-8")

            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            concept = wiki / "concepts/codex-check-fixable.md"
            concept.write_text(
                """---
title: Codex Check Fixable
---

## Definition
This page intentionally omits required fields that have deterministic defaults.

## Intuition
`$check` should report this by default and only modify the wiki when `--fix` is explicit.

## Variants

## Comparison

## Known limitations

## Open problems

## Relationship to foundations

## Realized by

## My understanding
""",
                encoding="utf-8",
            )

            before_wiki = snapshot(wiki)
            before_raw = snapshot(raw.parent)

            report = subprocess.run(
                [sys.executable, str(ROOT / "tools/lint.py"), "--wiki-dir", str(wiki), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(report.returncode, 1, report.stderr)
            issues = json.loads(report.stdout)
            missing_fields = {
                issue["message"].removeprefix("Missing required field: ")
                for issue in issues
                if issue.get("category") == "missing-field" and issue.get("file") == "concepts/codex-check-fixable.md"
            }
            self.assertTrue({"tags", "maturity", "key_papers"}.issubset(missing_fields))
            self.assertEqual(snapshot(wiki), before_wiki)
            self.assertEqual(snapshot(raw.parent), before_raw)

            dry_run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/lint.py"),
                    "--wiki-dir",
                    str(wiki),
                    "--fix",
                    "--dry-run",
                    "--json",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(dry_run.returncode, 1, dry_run.stderr)
            dry_payload = json.loads(dry_run.stdout)
            self.assertTrue(dry_payload["dry_run"])
            dry_fix_actions = {
                fix["action"]
                for fix in dry_payload["fixes"]
                if fix["file"] == "concepts/codex-check-fixable.md"
            }
            self.assertTrue(any("tags" in action for action in dry_fix_actions))
            self.assertTrue(any("maturity" in action for action in dry_fix_actions))
            self.assertTrue(any("key_papers" in action for action in dry_fix_actions))
            self.assertEqual(snapshot(wiki), before_wiki)
            self.assertEqual(snapshot(raw.parent), before_raw)

            fixed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/lint.py"),
                    "--wiki-dir",
                    str(wiki),
                    "--fix",
                    "--json",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(fixed.returncode, 1, fixed.stderr)
            fixed_payload = json.loads(fixed.stdout)
            self.assertFalse(fixed_payload["dry_run"])
            concept_text = concept.read_text(encoding="utf-8")
            self.assertIn("tags: []", concept_text)
            self.assertIn("maturity: active", concept_text)
            self.assertIn("key_papers: []", concept_text)
            self.assertEqual(raw_file.read_text(encoding="utf-8"), "\\section{Do not touch raw}\n")
            for graph_name in ("edges.jsonl", "citations.jsonl"):
                self.assertEqual(
                    before_wiki[f"graph/{graph_name}"],
                    (wiki / "graph" / graph_name).read_bytes(),
                )

    def test_ask_crystallize_fixture_writes_output_edges_and_log_only_when_explicit(self) -> None:
        def snapshot_files(base: Path) -> dict[str, str]:
            return {
                str(path.relative_to(base)): path.read_text(encoding="utf-8")
                for path in sorted(base.rglob("*"))
                if path.is_file()
            }

        def run_wiki(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), *args],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        with tempfile.TemporaryDirectory(prefix="autosci-ask-crystallize-smoke.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            for rel in ("papers", "notes", "web"):
                raw_dir = raw / rel
                raw_dir.mkdir(parents=True, exist_ok=True)
                (raw_dir / f"user-owned-{rel}.md").write_text(
                    f"# User-owned {rel}\n",
                    encoding="utf-8",
                )

            init = run_wiki("init", str(wiki))
            self.assertEqual(init.returncode, 0, init.stderr)

            paper_path = wiki / "papers/codex-ask-crystallize-source.md"
            concept_path = wiki / "concepts/codex-ask-crystallize-concept.md"
            paper_path.write_text(
                """---
title: Codex Ask Crystallize Source
slug: codex-ask-crystallize-source
tags: [codex, ask]
importance: 4
tldr: Shows that answer synthesis should cite local wiki pages.
---

## Problem & Context
Codex ask answers must be grounded in local wiki evidence.

## Key idea
The fixture links answer synthesis to an explicit concept.

## Method
Use local files only.

## Experiment & Results
The crystallized answer should preserve citations.

## Limitations
No external retrieval is covered here.

## Open questions
- How should crystallized ask outputs preserve provenance?

## My take
Useful for Codex migration validation.

## Related
- [[codex-ask-crystallize-concept]]
""",
                encoding="utf-8",
            )
            concept_path.write_text(
                """---
title: Codex Ask Crystallize Concept
tags: [codex, ask]
maturity: emerging
key_papers: [codex-ask-crystallize-source]
---

## Definition
A local invariant that `$ask --crystallize` writes only documented wiki artifacts.

## Intuition
Answer-only mode should remain read-only until the user explicitly requests crystallization.

## Variants

## Comparison

## Known limitations

## Open problems

## Relationship to foundations

## Realized by

## My understanding
The concept is grounded by [[codex-ask-crystallize-source]].
""",
                encoding="utf-8",
            )

            add_source_edge = run_wiki(
                "add-edge",
                str(wiki),
                "--from",
                "papers/codex-ask-crystallize-source",
                "--to",
                "concepts/codex-ask-crystallize-concept",
                "--type",
                "introduces_concept",
                "--evidence",
                "ask crystallize fixture source relationship",
                "--confidence",
                "high",
            )
            self.assertEqual(add_source_edge.returncode, 0, add_source_edge.stderr)

            for command in ("rebuild-index", "rebuild-context-brief", "rebuild-open-questions"):
                proc = run_wiki(command, str(wiki))
                self.assertEqual(proc.returncode, 0, proc.stderr)

            raw_before = snapshot_files(raw)
            source_before = {
                "paper": paper_path.read_text(encoding="utf-8"),
                "concept": concept_path.read_text(encoding="utf-8"),
                "index": (wiki / "index.md").read_text(encoding="utf-8"),
                "questions": (wiki / "graph/open_questions.md").read_text(encoding="utf-8"),
            }
            wiki_before_answer_only = snapshot_files(wiki)

            retrieve = run_wiki("find", str(wiki), "papers", "--tags", "ask")
            self.assertEqual(retrieve.returncode, 0, retrieve.stderr)
            answer_only = (
                "Codex ask crystallize outputs should cite "
                "[[codex-ask-crystallize-source]] and "
                "[[codex-ask-crystallize-concept]] before recommending writeback."
            )
            cited_slugs = re.findall(r"\[\[([a-z0-9-]+)\]\]", answer_only)
            self.assertEqual(
                sorted(cited_slugs),
                ["codex-ask-crystallize-concept", "codex-ask-crystallize-source"],
            )
            for slug in cited_slugs:
                self.assertTrue(
                    (wiki / "papers" / f"{slug}.md").exists()
                    or (wiki / "concepts" / f"{slug}.md").exists(),
                    slug,
                )
            self.assertEqual(snapshot_files(wiki), wiki_before_answer_only)
            self.assertEqual(snapshot_files(raw), raw_before)

            slug_proc = run_wiki("slug", "Codex retrieval synthesis")
            self.assertEqual(slug_proc.returncode, 0, slug_proc.stderr)
            output_slug = slug_proc.stdout.strip()
            output_path = wiki / "outputs" / f"{output_slug}.md"
            output_path.write_text(
                f"""---
title: Codex Retrieval Synthesis
slug: {output_slug}
query: How should Codex ask crystallize outputs preserve provenance?
source_pages: [codex-ask-crystallize-source, codex-ask-crystallize-concept]
date_created: 2026-07-08
---

Codex ask crystallization should preserve provenance by writing a traceable output note
that cites [[codex-ask-crystallize-source]] and [[codex-ask-crystallize-concept]].

Knowledge gap: the fixture does not cover remote retrieval.
""",
                encoding="utf-8",
            )

            for target in (
                "papers/codex-ask-crystallize-source",
                "concepts/codex-ask-crystallize-concept",
            ):
                edge = run_wiki(
                    "add-edge",
                    str(wiki),
                    "--from",
                    f"outputs/{output_slug}",
                    "--to",
                    target,
                    "--type",
                    "derived_from",
                    "--evidence",
                    "ask crystallize answer cites local source",
                )
                self.assertEqual(edge.returncode, 0, edge.stderr)

            log = run_wiki(
                "log",
                str(wiki),
                f"ask | codex retrieval synthesis | crystallized: wiki/outputs/{output_slug}.md",
            )
            self.assertEqual(log.returncode, 0, log.stderr)
            rebuild_context = run_wiki("rebuild-context-brief", str(wiki))
            self.assertEqual(rebuild_context.returncode, 0, rebuild_context.stderr)

            self.assertEqual(snapshot_files(raw), raw_before)
            self.assertEqual(paper_path.read_text(encoding="utf-8"), source_before["paper"])
            self.assertEqual(concept_path.read_text(encoding="utf-8"), source_before["concept"])
            self.assertEqual((wiki / "index.md").read_text(encoding="utf-8"), source_before["index"])
            self.assertEqual((wiki / "graph/open_questions.md").read_text(encoding="utf-8"), source_before["questions"])

            output_text = output_path.read_text(encoding="utf-8")
            self.assertIn("query: How should Codex ask crystallize outputs preserve provenance?", output_text)
            self.assertIn("source_pages: [codex-ask-crystallize-source, codex-ask-crystallize-concept]", output_text)

            edges = [
                json.loads(line)
                for line in (wiki / "graph/edges.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            derived_edges = [edge for edge in edges if edge["from"] == f"outputs/{output_slug}"]
            self.assertEqual({edge["to"] for edge in derived_edges}, {
                "papers/codex-ask-crystallize-source",
                "concepts/codex-ask-crystallize-concept",
            })
            self.assertTrue(all(edge["type"] == "derived_from" for edge in derived_edges))
            self.assertIn(
                f"ask | codex retrieval synthesis | crystallized: wiki/outputs/{output_slug}.md",
                (wiki / "log.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                f"outputs/{output_slug} --derived_from--> papers/codex-ask-crystallize-source",
                (wiki / "graph/context_brief.md").read_text(encoding="utf-8"),
            )

            stats = run_wiki("stats", str(wiki), "--json")
            self.assertEqual(stats.returncode, 0, stats.stderr)
            stats_payload = json.loads(stats.stdout)
            self.assertEqual(stats_payload["papers"], 1)
            self.assertEqual(stats_payload["concepts"], 1)
            self.assertEqual(stats_payload["edges"], 3)

    def test_exp_status_local_fixture_finds_running_experiments(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-exp-status-smoke.") as tmp:
            wiki = Path(tmp) / "wiki"
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            (wiki / "ideas/codex-status-idea.md").write_text(
                """---
title: Codex Status Idea
slug: codex-status-idea
status: in_progress
origin: local smoke fixture
origin_gaps: []
tags: [codex, experiments]
priority: 3
linked_experiments: [codex-running-experiment, codex-completed-experiment]
---

## Motivation
Exercise experiment status scans without launching real jobs.
""",
                encoding="utf-8",
            )
            (wiki / "experiments/codex-running-experiment.md").write_text(
                """---
title: Codex Running Experiment
slug: codex-running-experiment
status: running
linked_idea: codex-status-idea
evaluates_methods: []
hypothesis: A local status scan can find running experiments.
tags: [codex, status]
setup:
  model: smoke
  dataset: fixture
  hardware: local
  framework: none
metrics: [loss]
baseline: deterministic fixture
outcome: ""
key_result: ""
date_planned: 2026-07-08
date_completed: ""
run_log: logs/codex-running-experiment.log
started: "2026-07-08T00:00:00"
estimated_hours: 1
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Objective
Check that `$exp-status` can identify this page as running.
""",
                encoding="utf-8",
            )
            (wiki / "experiments/codex-completed-experiment.md").write_text(
                """---
title: Codex Completed Experiment
slug: codex-completed-experiment
status: completed
linked_idea: codex-status-idea
evaluates_methods: []
hypothesis: A completed experiment should not be in the running target list.
tags: [codex, status]
setup:
  model: smoke
  dataset: fixture
  hardware: local
  framework: none
metrics: [accuracy]
baseline: deterministic fixture
outcome: succeeded
key_result: Completed before status scan.
date_planned: 2026-07-08
date_completed: 2026-07-08
run_log: logs/codex-completed-experiment.log
started: "2026-07-08T00:00:00"
estimated_hours: 1
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Objective
Check that completed pages stay out of the default running target list.
""",
                encoding="utf-8",
            )

            running = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "find",
                    str(wiki),
                    "experiments",
                    "--status",
                    "running",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(running.returncode, 0, running.stderr)
            running_payload = json.loads(running.stdout)
            self.assertEqual([item["slug"] for item in running_payload], ["codex-running-experiment"])
            self.assertEqual(running_payload[0]["run_log"], "logs/codex-running-experiment.log")

            lint = subprocess.run(
                [sys.executable, str(ROOT / "tools/lint.py"), "--wiki-dir", str(wiki), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(lint.returncode, 0, lint.stderr)
            lint_payload = json.loads(lint.stdout)
            self.assertFalse(
                [issue for issue in lint_payload if issue.get("severity") == "🔴"],
                lint_payload,
            )

    def test_exp_design_fixture_creates_exp_run_ready_pages(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-exp-design-smoke.") as tmp:
            wiki = Path(tmp) / "wiki"
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            idea_slug = "codex-design-idea"
            exp_slug = "codex-design-main-exp"
            idea_path = wiki / f"ideas/{idea_slug}.md"
            exp_path = wiki / f"experiments/{exp_slug}.md"
            idea_path.write_text(
                f"""---
title: Codex Design Idea
slug: {idea_slug}
status: in_progress
origin: local exp-design smoke fixture
origin_gaps: []
tags: [codex, exp-design]
priority: 3
pilot_result: pass - tiny pilot met the success criterion
failure_reason: ""
linked_experiments: [{exp_slug}]
date_proposed: 2026-07-08
date_resolved: ""
---

## Motivation
Exercise `$exp-design` output shape.

## Hypothesis
A deterministic experiment page with every lifecycle field can be handed to `$exp-run`.

## Approach sketch
Create one main experiment fixture and connect it through the graph helper.

## Novelty argument
This is a migration smoke fixture.

## Target venue

## Risks

## Pilot results
pass

## Lessons learned
""",
                encoding="utf-8",
            )
            exp_path.write_text(
                f"""---
title: Codex Design Main Exp
slug: {exp_slug}
status: planned
linked_idea: {idea_slug}
evaluates_methods: []
hypothesis: A complete planned experiment page can be updated by exp-run.
tags: [main]
setup:
  model: smoke
  dataset: fixture
  hardware: local
  framework: none
metrics: [accuracy, loss]
baseline: deterministic baseline
outcome: ""
key_result: ""
date_planned: 2026-07-08
date_completed: ""
run_log: ""
started: ""
estimated_hours: 0
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Objective
Validate that `$exp-design` produces a page `$exp-run` can consume.

## Setup
Model: smoke. Dataset: fixture. Hardware: local.

## Procedure
Run the deterministic fixture, collect accuracy and loss, then update lifecycle fields.

## Results

## Analysis

## Idea updates

## Follow-up
Proceed to `$exp-run {exp_slug}`.
""",
                encoding="utf-8",
            )

            add_edge = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "add-edge",
                    str(wiki),
                    "--from",
                    f"ideas/{idea_slug}",
                    "--to",
                    f"experiments/{exp_slug}",
                    "--type",
                    "tested_by",
                    "--evidence",
                    "Designed by $exp-design L1 smoke fixture",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(add_edge.returncode, 0, add_edge.stderr)

            meta = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "read-meta", str(exp_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(meta.returncode, 0, meta.stderr)
            payload = json.loads(meta.stdout)
            expected_fields = {
                "title",
                "slug",
                "status",
                "linked_idea",
                "evaluates_methods",
                "hypothesis",
                "tags",
                "setup",
                "metrics",
                "baseline",
                "outcome",
                "key_result",
                "date_planned",
                "date_completed",
                "run_log",
                "started",
                "estimated_hours",
                "remote",
            }
            self.assertTrue(expected_fields.issubset(payload.keys()))
            self.assertEqual(payload["status"], "planned")
            self.assertEqual(payload["linked_idea"], idea_slug)
            self.assertEqual(payload["remote"], {"server": "", "gpu": "", "session": "", "started": "", "completed": ""})

            deploy_transition = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "transition",
                    str(exp_path),
                    "--to",
                    "running",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(deploy_transition.returncode, 0, deploy_transition.stderr)
            self.assertEqual(json.loads(deploy_transition.stdout)["new_status"], "running")

            for field, value in (
                ("run_log", f"logs/{exp_slug}.log"),
                ("started", "2026-07-08T00:00:00"),
                ("estimated_hours", "0.25"),
                ("outcome", "succeeded"),
                ("key_result", "The designed experiment page accepted exp-run lifecycle updates."),
            ):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), "set-meta", str(exp_path), field, value],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)

            complete = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "transition",
                    str(exp_path),
                    "--to",
                    "completed",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(complete.returncode, 0, complete.stderr)
            self.assertEqual(json.loads(complete.stdout)["new_status"], "completed")

            for command in ("rebuild-context-brief", "rebuild-open-questions"):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), command, str(wiki)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)

            edges = [
                json.loads(line)
                for line in (wiki / "graph/edges.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertIn(
                ("ideas/codex-design-idea", "experiments/codex-design-main-exp", "tested_by"),
                {(edge["from"], edge["to"], edge["type"]) for edge in edges},
            )
            context_text = (wiki / "graph/context_brief.md").read_text(encoding="utf-8")
            self.assertIn("codex-design-main-exp", context_text)

            lint = subprocess.run(
                [sys.executable, str(ROOT / "tools/lint.py"), "--wiki-dir", str(wiki), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(lint.returncode, 0, lint.stderr)
            lint_payload = json.loads(lint.stdout)
            self.assertFalse(
                [issue for issue in lint_payload if issue.get("severity") == "🔴"],
                lint_payload,
            )

    def test_exp_design_fixture_skips_duplicate_hypotheses_for_same_idea(self) -> None:
        def run_wiki(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), *args],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        def normalize_hypothesis(text: str) -> str:
            return re.sub(r"\s+", " ", text.strip().lower())

        def experiment_page(slug: str, title: str, idea_slug: str, hypothesis: str, tag: str) -> str:
            return f"""---
title: {title}
slug: {slug}
status: planned
linked_idea: {idea_slug}
evaluates_methods: []
hypothesis: {hypothesis}
tags: [{tag}]
setup:
  model: smoke
  dataset: fixture
  hardware: local
  framework: none
metrics: [accuracy]
baseline: deterministic baseline
outcome: ""
key_result: ""
date_planned: 2026-07-08
date_completed: ""
run_log: ""
started: ""
estimated_hours: 0
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Objective
{hypothesis}

## Setup
Local fixture only.

## Procedure
Run the deterministic local fixture and compare against baseline.

## Results

## Analysis

## Idea updates

## Follow-up
Proceed to `$exp-run {slug}`.
"""

        with tempfile.TemporaryDirectory(prefix="autosci-exp-design-dedupe-smoke.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw/papers"
            raw.mkdir(parents=True)
            raw_file = raw / "user-owned-exp-design.md"
            raw_file.write_text("# User-owned experiment notes\n", encoding="utf-8")
            raw_before = raw_file.read_text(encoding="utf-8")

            init = run_wiki("init", str(wiki))
            self.assertEqual(init.returncode, 0, init.stderr)

            idea_slug = "codex-design-dedupe-idea"
            existing_slug = "codex-existing-ablation"
            new_slug = "codex-main-followup"
            duplicate_candidate_slug = "codex-existing-ablation-repeat"
            duplicate_hypothesis = "Removing the routing gate should lower accuracy."
            new_hypothesis = "The finalized method should improve accuracy over the deterministic baseline."

            idea_path = wiki / f"ideas/{idea_slug}.md"
            idea_path.write_text(
                f"""---
title: Codex Design Dedupe Idea
slug: {idea_slug}
status: in_progress
origin: local exp-design duplicate smoke fixture
origin_gaps: []
tags: [codex, exp-design]
priority: 3
pilot_result: pass - tiny pilot met the success criterion
failure_reason: ""
linked_experiments: [{existing_slug}]
date_proposed: 2026-07-08
date_resolved: ""
---

## Motivation
Exercise `$exp-design` duplicate prevention.

## Hypothesis
Duplicate experiment hypotheses should not create duplicate wiki pages.

## Approach sketch
Check existing experiments before writing new ones.

## Novelty argument
This is a migration smoke fixture.

## Target venue

## Risks

## Pilot results
pass

## Lessons learned
""",
                encoding="utf-8",
            )
            existing_path = wiki / f"experiments/{existing_slug}.md"
            existing_path.write_text(
                experiment_page(existing_slug, "Codex Existing Ablation", idea_slug, duplicate_hypothesis, "ablation"),
                encoding="utf-8",
            )

            existing_edge = run_wiki(
                "add-edge",
                str(wiki),
                "--from",
                f"ideas/{idea_slug}",
                "--to",
                f"experiments/{existing_slug}",
                "--type",
                "tested_by",
                "--evidence",
                "Pre-existing experiment before exp-design duplicate scan",
            )
            self.assertEqual(existing_edge.returncode, 0, existing_edge.stderr)

            existing = run_wiki("find", str(wiki), "experiments", "--linked_idea", idea_slug)
            self.assertEqual(existing.returncode, 0, existing.stderr)
            seen = {
                (item["linked_idea"], normalize_hypothesis(item.get("hypothesis", "")))
                for item in json.loads(existing.stdout)
            }

            candidates = [
                (duplicate_candidate_slug, "Codex Duplicate Ablation Repeat", duplicate_hypothesis, "ablation"),
                (new_slug, "Codex Main Followup", new_hypothesis, "main"),
            ]
            skipped: list[str] = []
            created: list[str] = []

            for slug, title, hypothesis, tag in candidates:
                key = (idea_slug, normalize_hypothesis(hypothesis))
                if key in seen:
                    skipped.append(slug)
                    continue

                (wiki / f"experiments/{slug}.md").write_text(
                    experiment_page(slug, title, idea_slug, hypothesis, tag),
                    encoding="utf-8",
                )
                update_idea = run_wiki("set-meta", str(idea_path), "linked_experiments", slug, "--append")
                self.assertEqual(update_idea.returncode, 0, update_idea.stderr)
                edge = run_wiki(
                    "add-edge",
                    str(wiki),
                    "--from",
                    f"ideas/{idea_slug}",
                    "--to",
                    f"experiments/{slug}",
                    "--type",
                    "tested_by",
                    "--evidence",
                    "Designed by $exp-design duplicate smoke fixture",
                )
                self.assertEqual(edge.returncode, 0, edge.stderr)
                created.append(slug)
                seen.add(key)

            design_dir = root / "experiments/designs"
            design_dir.mkdir(parents=True)
            design_doc = design_dir / f"{idea_slug}-master.md"
            design_doc.write_text(
                f"""---
title: "Experiment Design: Codex Design Dedupe Idea"
slug: "{idea_slug}-design"
status: planned
linked_idea: "{idea_slug}"
tags: ["exp-design"]
date_planned: 2026-07-08
---

## Duplicate Scan
- Skipped duplicate hypothesis: {duplicate_candidate_slug} duplicates {existing_slug}
- Created experiments: {", ".join(created)}
""",
                encoding="utf-8",
            )

            log = run_wiki(
                "log",
                str(wiki),
                f"exp-design | {len(created)} experiments designed for idea {idea_slug} | skipped duplicates: {len(skipped)}",
            )
            self.assertEqual(log.returncode, 0, log.stderr)
            for command in ("rebuild-context-brief", "rebuild-open-questions"):
                proc = run_wiki(command, str(wiki))
                self.assertEqual(proc.returncode, 0, proc.stderr)

            self.assertEqual(skipped, [duplicate_candidate_slug])
            self.assertEqual(created, [new_slug])
            self.assertFalse((wiki / f"experiments/{duplicate_candidate_slug}.md").exists())
            self.assertTrue((wiki / f"experiments/{new_slug}.md").exists())
            self.assertEqual(raw_file.read_text(encoding="utf-8"), raw_before)

            idea_meta = run_wiki("read-meta", str(idea_path), "linked_experiments")
            self.assertEqual(idea_meta.returncode, 0, idea_meta.stderr)
            self.assertEqual(json.loads(idea_meta.stdout), [existing_slug, new_slug])

            edges = [
                json.loads(line)
                for line in (wiki / "graph/edges.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            tested_by_targets = [
                edge["to"]
                for edge in edges
                if edge["from"] == f"ideas/{idea_slug}" and edge["type"] == "tested_by"
            ]
            self.assertEqual(
                sorted(tested_by_targets),
                [f"experiments/{existing_slug}", f"experiments/{new_slug}"],
            )
            self.assertIn(
                f"skipped duplicates: {len(skipped)}",
                (wiki / "log.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                f"Skipped duplicate hypothesis: {duplicate_candidate_slug} duplicates {existing_slug}",
                design_doc.read_text(encoding="utf-8"),
            )

            lint = subprocess.run(
                [sys.executable, str(ROOT / "tools/lint.py"), "--wiki-dir", str(wiki), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(lint.returncode, 0, lint.stderr)
            lint_payload = json.loads(lint.stdout)
            self.assertFalse(
                [issue for issue in lint_payload if issue.get("severity") == "🔴"],
                lint_payload,
            )

    def test_exp_run_lifecycle_writeback_uses_transition_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-exp-run-smoke.") as tmp:
            wiki = Path(tmp) / "wiki"
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            (wiki / "ideas/codex-exp-run-idea.md").write_text(
                """---
title: Codex Exp Run Idea
slug: codex-exp-run-idea
status: in_progress
origin: local smoke fixture
origin_gaps: []
tags: [codex, experiments]
priority: 3
linked_experiments: [codex-exp-run-transition]
---

## Motivation
Exercise exp-run lifecycle writeback.
""",
                encoding="utf-8",
            )
            exp_path = wiki / "experiments/codex-exp-run-transition.md"
            exp_path.write_text(
                """---
title: Codex Exp Run Transition
slug: codex-exp-run-transition
status: planned
linked_idea: codex-exp-run-idea
evaluates_methods: []
hypothesis: Exp-run should use lifecycle transitions for status writes.
tags: [codex, lifecycle]
setup:
  model: smoke
  dataset: fixture
  hardware: local
  framework: none
metrics: [accuracy]
baseline: deterministic fixture
outcome: ""
key_result: ""
date_planned: 2026-07-08
date_completed: ""
run_log: ""
started: ""
estimated_hours: 0
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Objective
Check status writeback path.
""",
                encoding="utf-8",
            )

            deploy_transition = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "transition",
                    str(exp_path),
                    "--to",
                    "running",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(deploy_transition.returncode, 0, deploy_transition.stderr)
            self.assertEqual(json.loads(deploy_transition.stdout)["new_status"], "running")

            premature_complete = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "transition",
                    str(exp_path),
                    "--to",
                    "completed",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(premature_complete.returncode, 0)
            self.assertIn("key_result must be non-empty", premature_complete.stdout)

            for field, value in (
                ("run_log", "logs/codex-exp-run-transition.log"),
                ("remote.server", "codex-remote-smoke"),
                ("remote.gpu", "gpu-0"),
                ("remote.session", "exp-codex-exp-run-transition"),
                ("remote.started", "2026-07-08T00:00:00"),
                ("outcome", "succeeded"),
                ("key_result", "Lifecycle transition succeeded after result collection."),
            ):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), "set-meta", str(exp_path), field, value],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)

            missing_nested = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "set-meta",
                    str(exp_path),
                    "remote.missing",
                    "should-not-create",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(missing_nested.returncode, 0)
            self.assertIn("Field 'remote.missing' not found", missing_nested.stdout)

            complete = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "transition",
                    str(exp_path),
                    "--to",
                    "completed",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(complete.returncode, 0, complete.stderr)
            complete_payload = json.loads(complete.stdout)
            self.assertEqual(complete_payload["new_status"], "completed")
            self.assertIn("date_completed", complete_payload["auto_set"])

            meta = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "read-meta", str(exp_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(meta.returncode, 0, meta.stderr)
            meta_payload = json.loads(meta.stdout)
            self.assertEqual(meta_payload["status"], "completed")
            self.assertEqual(meta_payload["outcome"], "succeeded")
            self.assertEqual(
                meta_payload["remote"],
                {
                    "server": "codex-remote-smoke",
                    "gpu": "gpu-0",
                    "session": "exp-codex-exp-run-transition",
                    "started": "2026-07-08T00:00:00",
                    "completed": "",
                },
            )
            self.assertRegex(str(meta_payload["date_completed"]), r"^\d{4}-\d{2}-\d{2}$")

            remote_completed = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "read-meta", str(exp_path), "remote.completed"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(remote_completed.returncode, 0, remote_completed.stderr)
            self.assertEqual(json.loads(remote_completed.stdout), "")

            set_remote_completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "set-meta",
                    str(exp_path),
                    "remote.completed",
                    "2026-07-08T00:05:00",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(set_remote_completed.returncode, 0, set_remote_completed.stderr)
            remote_completed_after = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "read-meta", str(exp_path), "remote.completed"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(remote_completed_after.returncode, 0, remote_completed_after.stderr)
            self.assertEqual(json.loads(remote_completed_after.stdout), "2026-07-08T00:05:00")

    def test_exp_run_tiny_local_execution_path_collects_results(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-exp-run-tiny.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            slug = "codex-tiny-local-exp"
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            (wiki / "ideas/codex-tiny-local-idea.md").write_text(
                f"""---
title: Codex Tiny Local Idea
slug: codex-tiny-local-idea
status: in_progress
origin: local smoke fixture
origin_gaps: []
tags: [codex, experiments]
priority: 3
linked_experiments: [{slug}]
---

## Motivation
Exercise a tiny local `$exp-run` execution path.
""",
                encoding="utf-8",
            )
            exp_path = wiki / f"experiments/{slug}.md"
            exp_path.write_text(
                f"""---
title: Codex Tiny Local Exp
slug: {slug}
status: planned
linked_idea: codex-tiny-local-idea
evaluates_methods: []
hypothesis: A tiny local run can produce collectable JSON results.
tags: [codex, lifecycle]
setup:
  model: smoke
  dataset: fixture
  hardware: none
  framework: none
metrics: [accuracy, loss]
baseline: deterministic fixture
outcome: ""
key_result: ""
date_planned: 2026-07-08
date_completed: ""
run_log: ""
started: ""
estimated_hours: 0
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Objective
Check the local deploy, run, collect, and transition sequence.

## Results

## Analysis
""",
                encoding="utf-8",
            )

            code_dir = root / f"experiments/code/{slug}"
            code_dir.mkdir(parents=True)
            logs_dir = root / "logs"
            logs_dir.mkdir()
            run_script = code_dir / "run.sh"
            run_script.write_text(
                f"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p results/{slug}
"{sys.executable}" -c 'import json, pathlib; pathlib.Path("results/{slug}/seed_0.json").write_text(json.dumps({{"accuracy": 0.91, "loss": 0.12}}), encoding="utf-8")'
echo "tiny local exp completed"
""",
                encoding="utf-8",
            )

            for command in (
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "transition",
                    str(exp_path),
                    "--to",
                    "running",
                ],
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "set-meta",
                    str(exp_path),
                    "run_log",
                    f"logs/{slug}.log",
                ],
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "set-meta",
                    str(exp_path),
                    "started",
                    "2026-07-08T00:00",
                ],
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "set-meta",
                    str(exp_path),
                    "estimated_hours",
                    "0.01",
                ],
            ):
                proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
                self.assertEqual(proc.returncode, 0, proc.stderr)

            log_path = logs_dir / f"{slug}.log"
            with log_path.open("w", encoding="utf-8") as log_fh:
                run = subprocess.run(
                    ["bash", str(run_script)],
                    cwd=root,
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
            self.assertEqual(run.returncode, 0)
            self.assertIn("tiny local exp completed", log_path.read_text(encoding="utf-8"))

            result_path = root / f"results/{slug}/seed_0.json"
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(result["accuracy"], 0.9)
            self.assertLess(result["loss"], 0.2)

            for field, value in (
                ("outcome", "succeeded"),
                ("key_result", "Tiny local run produced accuracy 0.91 and finite loss 0.12."),
            ):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), "set-meta", str(exp_path), field, value],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)

            complete = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "transition",
                    str(exp_path),
                    "--to",
                    "completed",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(complete.returncode, 0, complete.stderr)
            self.assertEqual(json.loads(complete.stdout)["new_status"], "completed")

            meta = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "read-meta", str(exp_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(meta.returncode, 0, meta.stderr)
            meta_payload = json.loads(meta.stdout)
            self.assertEqual(meta_payload["status"], "completed")
            self.assertEqual(meta_payload["run_log"], f"logs/{slug}.log")
            self.assertEqual(meta_payload["key_result"], "Tiny local run produced accuracy 0.91 and finite loss 0.12.")

            lint = subprocess.run(
                [sys.executable, str(ROOT / "tools/lint.py"), "--wiki-dir", str(wiki), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(lint.returncode, 0, lint.stderr)
            lint_payload = json.loads(lint.stdout)
            self.assertFalse(
                [issue for issue in lint_payload if issue.get("severity") == "🔴"],
                lint_payload,
            )

    def test_exp_eval_local_verdict_paths_update_idea_and_graph(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-exp-eval-smoke.") as tmp:
            wiki = Path(tmp) / "wiki"
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            fixtures = [
                {
                    "idea": "codex-supported-idea",
                    "experiment": "codex-supported-exp",
                    "outcome": "succeeded",
                    "key_result": "Accuracy improved by 7 points across all seeds.",
                    "verdict": "supported",
                    "transition": "validated",
                    "edge_type": "supports",
                    "edge_evidence": "Accuracy improved by 7 points across all seeds.",
                    "reason": "",
                },
                {
                    "idea": "codex-failed-idea",
                    "experiment": "codex-failed-exp",
                    "outcome": "failed",
                    "key_result": "The method collapsed on the target metric and underperformed the baseline.",
                    "verdict": "not_supported",
                    "transition": "failed",
                    "edge_type": "invalidates",
                    "edge_evidence": "The method collapsed on the target metric and underperformed the baseline.",
                    "reason": "Target metric collapsed and baseline was not beaten.",
                },
            ]

            for item in fixtures:
                idea = item["idea"]
                exp = item["experiment"]
                (wiki / f"ideas/{idea}.md").write_text(
                    f"""---
title: {idea.replace('-', ' ').title()}
slug: {idea}
status: tested
origin: local exp-eval smoke fixture
origin_gaps: []
tags: [codex, exp-eval]
priority: 3
pilot_result: pass
failure_reason: ""
linked_experiments: [{exp}]
date_proposed: 2026-07-08
date_resolved: ""
---

## Motivation
Exercise `$exp-eval` verdict writeback.

## Hypothesis
The linked experiment determines whether this idea should advance or fail.

## Approach sketch
Use deterministic local fixture evidence.

## Novelty argument
This is a smoke fixture, not a real claim.

## Target venue

## Risks

## Pilot results
pass

## Lessons learned
""",
                    encoding="utf-8",
                )
                (wiki / f"experiments/{exp}.md").write_text(
                    f"""---
title: {exp.replace('-', ' ').title()}
slug: {exp}
status: completed
linked_idea: {idea}
evaluates_methods: []
hypothesis: Local verdict fixture exercises exp-eval writeback.
tags: [codex, exp-eval]
setup:
  model: smoke
  dataset: fixture
  hardware: local
  framework: none
metrics: [accuracy]
baseline: deterministic baseline
outcome: {item["outcome"]}
key_result: {item["key_result"]}
date_planned: 2026-07-08
date_completed: 2026-07-08
run_log: logs/{exp}.log
started: "2026-07-08T00:00:00"
estimated_hours: 0.01
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Objective
Check `$exp-eval` verdict path.

## Setup
Deterministic local fixture.

## Procedure
Apply a mocked final verdict after Review LLM would have judged the result.

## Results
{item["key_result"]}

## Analysis
The verdict is predetermined so this test covers writeback mechanics only.

## Idea updates

## Follow-up
""",
                    encoding="utf-8",
                )

            for item in fixtures:
                idea = item["idea"]
                exp = item["experiment"]
                idea_path = wiki / f"ideas/{idea}.md"
                command = [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "transition",
                    str(idea_path),
                    "--to",
                    item["transition"],
                ]
                if item["reason"]:
                    command.extend(["--reason", item["reason"]])
                transition = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
                self.assertEqual(transition.returncode, 0, transition.stderr)
                transition_payload = json.loads(transition.stdout)
                self.assertEqual(transition_payload["old_status"], "tested")
                self.assertEqual(transition_payload["new_status"], item["transition"])

                add_edge = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "tools/research_wiki.py"),
                        "add-edge",
                        str(wiki),
                        "--from",
                        f"experiments/{exp}",
                        "--to",
                        f"ideas/{idea}",
                        "--type",
                        item["edge_type"],
                        "--evidence",
                        item["edge_evidence"],
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(add_edge.returncode, 0, add_edge.stderr)

                exp_path = wiki / f"experiments/{exp}.md"
                exp_text = exp_path.read_text(encoding="utf-8")
                exp_path.write_text(
                    exp_text.replace(
                        "## Idea updates\n",
                        (
                            "## Idea updates\n"
                            f"- **Verdict**: {item['verdict']}\n"
                            f"- **Linked idea**: [[{idea}]] status tested -> {item['transition']}\n"
                            "- **Judge agreement**: mocked L1 fixture only; Review LLM not invoked\n"
                            "- **Date**: 2026-07-08\n"
                        ),
                    ),
                    encoding="utf-8",
                )

                log = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "tools/research_wiki.py"),
                        "log",
                        str(wiki),
                        f"exp-eval | {exp} -> ideas/{idea} | verdict: {item['verdict']} | idea status: tested->{item['transition']}",
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(log.returncode, 0, log.stderr)

            for command in ("rebuild-index", "rebuild-context-brief", "rebuild-open-questions"):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), command, str(wiki)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)

            for item in fixtures:
                meta = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "tools/research_wiki.py"),
                        "read-meta",
                        str(wiki / f"ideas/{item['idea']}.md"),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(meta.returncode, 0, meta.stderr)
                payload = json.loads(meta.stdout)
                self.assertEqual(payload["status"], item["transition"])
                if item["transition"] == "failed":
                    self.assertEqual(payload["failure_reason"], item["reason"])
                self.assertRegex(str(payload["date_resolved"]), r"^\d{4}-\d{2}-\d{2}$")
                exp_text = (wiki / f"experiments/{item['experiment']}.md").read_text(encoding="utf-8")
                self.assertIn(f"**Verdict**: {item['verdict']}", exp_text)
                self.assertIn(f"[[{item['idea']}]] status tested -> {item['transition']}", exp_text)

            edges = [
                json.loads(line)
                for line in (wiki / "graph/edges.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            edge_index = {(edge["from"], edge["to"], edge["type"]) for edge in edges}
            self.assertIn(("experiments/codex-supported-exp", "ideas/codex-supported-idea", "supports"), edge_index)
            self.assertIn(("experiments/codex-failed-exp", "ideas/codex-failed-idea", "invalidates"), edge_index)

            context_text = (wiki / "graph/context_brief.md").read_text(encoding="utf-8")
            self.assertIn("codex-supported-idea", context_text)
            self.assertIn("codex-failed-idea", context_text)
            log_text = (wiki / "log.md").read_text(encoding="utf-8")
            self.assertIn("exp-eval | codex-supported-exp", log_text)
            self.assertIn("exp-eval | codex-failed-exp", log_text)

            lint = subprocess.run(
                [sys.executable, str(ROOT / "tools/lint.py"), "--wiki-dir", str(wiki), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(lint.returncode, 0, lint.stderr)
            lint_payload = json.loads(lint.stdout)
            self.assertFalse(
                [issue for issue in lint_payload if issue.get("severity") == "🔴"],
                lint_payload,
            )

    def test_pilot_failure_can_transition_proposed_idea_to_failed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-pilot-eval-smoke.") as tmp:
            wiki = Path(tmp) / "wiki"
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            idea_path = wiki / "ideas/codex-pilot-failure.md"
            idea_path.write_text(
                """---
title: Codex Pilot Failure
slug: codex-pilot-failure
status: proposed
origin: local smoke fixture
origin_gaps: []
tags: [codex, pilot]
priority: 3
pilot_result: ""
failure_reason: ""
linked_experiments: []
---

## Motivation
Exercise pilot failure lifecycle transition.
""",
                encoding="utf-8",
            )

            pilot_result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "set-meta",
                    str(idea_path),
                    "pilot_result",
                    "fail - loss diverged in pilot",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(pilot_result.returncode, 0, pilot_result.stderr)

            transition = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "transition",
                    str(idea_path),
                    "--to",
                    "failed",
                    "--reason",
                    "[pilot] loss diverged after 50 steps",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(transition.returncode, 0, transition.stderr)
            payload = json.loads(transition.stdout)
            self.assertEqual(payload["old_status"], "proposed")
            self.assertEqual(payload["new_status"], "failed")
            self.assertIn("failure_reason", payload["auto_set"])
            self.assertIn("date_resolved", payload["auto_set"])

            meta = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "read-meta", str(idea_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(meta.returncode, 0, meta.stderr)
            meta_payload = json.loads(meta.stdout)
            self.assertEqual(meta_payload["status"], "failed")
            self.assertEqual(meta_payload["failure_reason"], "[pilot] loss diverged after 50 steps")
            self.assertRegex(str(meta_payload["date_resolved"]), r"^\d{4}-\d{2}-\d{2}$")

    def test_exp_pilot_run_tiny_execution_is_result_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-exp-pilot-tiny.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            slug = "codex-tiny-pilot"
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            (wiki / "ideas/codex-tiny-pilot-idea.md").write_text(
                """---
title: Codex Tiny Pilot Idea
slug: codex-tiny-pilot-idea
status: proposed
origin: local smoke fixture
origin_gaps: []
tags: [codex, pilot]
priority: 3
pilot_result: ""
failure_reason: ""
linked_experiments: []
---

## Motivation
This page must not be modified by `$exp-pilot-run`.
""",
                encoding="utf-8",
            )
            before_wiki = {
                path.relative_to(wiki): path.read_bytes()
                for path in wiki.rglob("*")
                if path.is_file()
            }

            pilot_dir = root / f"experiments/pilot/{slug}"
            pilot_dir.mkdir(parents=True)
            spec_path = root / f"experiments/pilot/{slug}.yaml"
            result_path = pilot_dir / "pilot_result.json"
            spec_path.write_text(
                f"""slug: {slug}
idea: codex-tiny-pilot-idea
setup:
  model: smoke
  dataset: fixture
  hardware: none
success_criterion:
  metric: loss
  max_value: 0.2
""",
                encoding="utf-8",
            )
            run_script = pilot_dir / "run_pilot.py"
            run_script.write_text(
                """import json
import pathlib
import sys

spec = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
if "success_criterion:" not in spec.read_text(encoding="utf-8"):
    raise SystemExit("invalid pilot spec")
out.write_text(
    json.dumps(
        {
            "slug": "codex-tiny-pilot",
            "metrics": {"loss": 0.13, "accuracy": 0.88},
            "verdict_input": "no obvious collapse",
        },
        sort_keys=True,
    ),
    encoding="utf-8",
)
""",
                encoding="utf-8",
            )

            run = subprocess.run(
                [sys.executable, str(run_script), str(spec_path), str(result_path)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["slug"], slug)
            self.assertLess(payload["metrics"]["loss"], 0.2)
            self.assertEqual(payload["verdict_input"], "no obvious collapse")

            after_wiki = {
                path.relative_to(wiki): path.read_bytes()
                for path in wiki.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before_wiki, after_wiki)

    def test_setup_and_core_skill_docs_are_codex_neutral(self) -> None:
        setup_guide = (ROOT / "config/setup-guide.md").read_text(encoding="utf-8")
        self.assertIn("Claude Code or Codex can register a free token", setup_guide)
        self.assertIn("`/setup` or `$setup`", setup_guide)
        self.assertTrue((ROOT / ".env.example").exists())

        for rel in ("i18n/en/skills/setup/SKILL.md", "i18n/zh/skills/setup/SKILL.md", "config/README.md"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("cp .env.example .env", text, rel)
            self.assertNotIn("cp config/.env.example .env", text, rel)

        server_template = (ROOT / "config/server.yaml.example").read_text(encoding="utf-8")
        self.assertIn("/exp-run --env remote", server_template)
        self.assertIn("$exp-run --env remote", server_template)
        self.assertNotIn("/run-experiment", server_template)

        ask = (ROOT / ".agents/skills/ask/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Crystallize requires confirmation", ask)
        self.assertIn("unless the user explicitly specifies `--crystallize`", ask)
        self.assertIn("raw/ is read-only", ask)

        check = (ROOT / ".agents/skills/check/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Report-only by default", check)
        self.assertIn("raw/ is read-only", check)
        self.assertIn("graph/ is read-only", check)

    def test_setup_env_status_probe_is_read_only_and_redacts_values(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-setup-smoke.") as tmp:
            project = Path(tmp)
            home = project / "home"
            home.mkdir()
            wiki = project / "wiki"
            raw = project / "raw/papers"
            wiki.mkdir()
            raw.mkdir(parents=True)
            (wiki / "sentinel.md").write_text("wiki must not be touched\n", encoding="utf-8")
            (raw / "sentinel.tex").write_text("\\section{raw must not be touched}\n", encoding="utf-8")
            env_path = project / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "SEMANTIC_SCHOLAR_API_KEY=",
                        "DEEPXIV_TOKEN=deepxiv_secret_value",
                        "LLM_API_KEY=review_secret_value",
                        "LLM_BASE_URL=https://review.example/v1",
                        "LLM_MODEL=review-model",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            before = {
                path.relative_to(project): path.read_bytes()
                for path in project.rglob("*")
                if path.is_file()
            }

            probe = """
import os, sys
sys.path.insert(0, %r)
try:
    import _env
except Exception:
    pass
keys = {
    'SEMANTIC_SCHOLAR_API_KEY': 'Semantic Scholar',
    'DEEPXIV_TOKEN':            'DeepXiv',
    'LLM_API_KEY':              'Review LLM (API key)',
    'LLM_BASE_URL':             'Review LLM (base URL)',
    'LLM_MODEL':                'Review LLM (model)',
}
for k, label in keys.items():
    v = os.environ.get(k, '').strip()
    print(f'SET:{k}' if v else f'UNSET:{k}')
""" % str(ROOT / "tools")
            env = os.environ.copy()
            env["HOME"] = str(home)
            for key in (
                "SEMANTIC_SCHOLAR_API_KEY",
                "DEEPXIV_TOKEN",
                "LLM_API_KEY",
                "LLM_BASE_URL",
                "LLM_MODEL",
            ):
                env.pop(key, None)

            proc = subprocess.run(
                [sys.executable, "-c", probe],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(
                proc.stdout.strip().splitlines(),
                [
                    "UNSET:SEMANTIC_SCHOLAR_API_KEY",
                    "SET:DEEPXIV_TOKEN",
                    "SET:LLM_API_KEY",
                    "SET:LLM_BASE_URL",
                    "SET:LLM_MODEL",
                ],
            )
            self.assertNotIn("deepxiv_secret_value", proc.stdout + proc.stderr)
            self.assertNotIn("review_secret_value", proc.stdout + proc.stderr)
            self.assertNotIn("https://review.example/v1", proc.stdout + proc.stderr)
            after = {
                path.relative_to(project): path.read_bytes()
                for path in project.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_utility_skills_have_codex_invocation_and_raw_boundaries(self) -> None:
        skill_expectations = {
            "prefill": ["$prefill", "$ingest"],
            "edit": ["$edit", "$ingest", "raw/papers/`, `raw/notes/`, and `raw/web/` are user-owned and read-only"],
            "reset": ["$reset", "$init", "$prefill", "$ingest", "User-owned raw is never deleted"],
            "visualize": ["$visualize", "$ingest", "Codex: a long-running shell session", "documented network escalation rule"],
        }
        for skill, snippets in skill_expectations.items():
            for lang in ("en", "zh"):
                text = (ROOT / f"i18n/{lang}/skills/{skill}/SKILL.md").read_text(encoding="utf-8")
                for snippet in snippets:
                    if lang == "zh" and snippet.startswith("User-owned"):
                        snippet = "用户 raw 永不删除"
                    elif lang == "zh" and snippet == "raw/papers/`, `raw/notes/`, and `raw/web/` are user-owned and read-only":
                        snippet = "`raw/papers/`、`raw/notes/`、`raw/web/` 归用户所有且只读"
                    elif lang == "zh" and snippet == "Codex: a long-running shell session":
                        snippet = "Codex：长跑 shell session"
                    elif lang == "zh" and snippet == "documented network escalation rule":
                        snippet = "network escalation rule"
                    self.assertIn(snippet, text, f"{lang}/{skill}")

        reset_tool = (ROOT / "tools/reset_wiki.py").read_text(encoding="utf-8")
        self.assertIn('SKILL_WRITABLE_RAW_SUBDIRS = ["discovered", "tmp"]', reset_tool)
        self.assertNotIn('RAW_SUBDIRS = ["papers", "discovered", "tmp", "notes", "web"]', reset_tool)

    def test_prefill_foundation_fixture_supports_ingest_dedup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-prefill.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            raw.mkdir()
            proc = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

            foundation = wiki / "foundations" / "gradient-descent.md"
            foundation.write_text(
                """---
title: Gradient Descent
slug: gradient-descent
domain: general
status: mainstream
aliases: [steepest descent]
first_introduced: "1847"
date_updated: "2026-07-08"
source_url: ""
---

## Definition
Gradient descent is an iterative optimization method for minimizing an objective.

## Intuition
Move parameters opposite the local gradient.

## Formal notation
LLM analysis (LLM analysis)

## Key variants
- Batch gradient descent
- Stochastic gradient descent

## Known limitations
Sensitive to step size.

## Open problems
LLM analysis (LLM analysis)

## Relevance to active research
Common baseline optimizer.
""",
                encoding="utf-8",
            )

            rebuild = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "rebuild-index", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(rebuild.returncode, 0, rebuild.stderr)
            log = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "log", str(wiki), "prefill | 1 foundations created for general"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(log.returncode, 0, log.stderr)

            similar = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "find-similar-concept",
                    str(wiki),
                    "Stochastic Gradient Descent",
                    "--aliases",
                    "gradient descent",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(similar.returncode, 0, similar.stderr)
            matches = json.loads(similar.stdout)
            self.assertGreaterEqual(len(matches), 1)
            self.assertEqual(matches[0]["entity_type"], "foundation")
            self.assertEqual(matches[0]["slug"], "gradient-descent")
            self.assertGreaterEqual(matches[0]["score"], 0.85)

            self.assertIn("gradient-descent", (wiki / "index.md").read_text(encoding="utf-8"))
            self.assertIn("prefill | 1 foundations created for general", (wiki / "log.md").read_text(encoding="utf-8"))
            self.assertFalse(any(raw.rglob("*")), "prefill should not write raw files")

    def test_survey_archive_fixture_uses_existing_papers_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-survey.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            raw.mkdir()
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            papers = {
                "codex-survey-foundation": ("Codex Survey Foundation", 5),
                "codex-survey-extension": ("Codex Survey Extension", 4),
                "codex-survey-challenge": ("Codex Survey Challenge", 3),
            }
            for slug, (title, importance) in papers.items():
                (wiki / f"papers/{slug}.md").write_text(
                    f"""---
title: {title}
slug: {slug}
tags: [codex, survey]
importance: {importance}
arxiv: ""
doi: ""
year: 2026
---

## Problem & Context
This paper contributes to a local Codex survey fixture.

## Key idea
{title} studies the same topic from a distinct angle.

## Experiment & Results
The fixture records deterministic local evidence.

## Related

## My take
Useful evidence for thematic related work.
""",
                    encoding="utf-8",
                )

            out_slug = "related-work-codex-survey-2026-07-08"
            output = wiki / f"outputs/{out_slug}.md"
            output.write_text(
                """---
title: "Related Work: Codex survey fixture"
type: related-work
format: markdown
paper_count: 3
date_generated: 2026-07-08
---

Parameter-efficient research workflows rely on foundation papers while also
tracking extensions and challenges. [[codex-survey-foundation]] establishes
the local baseline, [[codex-survey-extension]] expands the setting, and
[[codex-survey-challenge]] identifies limitations; unlike this fixture, a real
survey would turn those notes into polished prose.
""",
                encoding="utf-8",
            )

            for slug in papers:
                edge = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "tools/research_wiki.py"),
                        "add-edge",
                        str(wiki),
                        "--from",
                        f"outputs/{out_slug}",
                        "--to",
                        f"papers/{slug}",
                        "--type",
                        "derived_from",
                        "--evidence",
                        "Cited in related work section",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(edge.returncode, 0, edge.stderr)

            log = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "log", str(wiki), "survey | codex survey fixture | 3 papers, 1 groups, format: markdown"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(log.returncode, 0, log.stderr)

            edges = [
                json.loads(line)
                for line in (wiki / "graph/edges.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            derived = {(edge["from"], edge["to"], edge["type"]) for edge in edges}
            self.assertEqual(
                derived,
                {(f"outputs/{out_slug}", f"papers/{slug}", "derived_from") for slug in papers},
            )
            body = output.read_text(encoding="utf-8")
            for slug in papers:
                self.assertIn(f"[[{slug}]]", body)
            self.assertIn("survey | codex survey fixture | 3 papers", (wiki / "log.md").read_text(encoding="utf-8"))
            self.assertFalse(any(raw.rglob("*")), "survey should not write raw files")

    def test_paper_plan_fixture_maps_validated_idea_to_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-paper-plan.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            raw.mkdir()
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            idea_slug = "codex-paper-plan-idea"
            exp_slug = "codex-paper-plan-exp"
            paper_slugs = ["codex-paper-plan-source", "codex-paper-plan-baseline"]
            (wiki / f"ideas/{idea_slug}.md").write_text(
                f"""---
title: Codex Paper Plan Idea
slug: {idea_slug}
status: validated
origin: user
tags: [codex, paper-plan]
priority: 1
novelty_score: 4
target_venue: ICLR
origin_gaps: []
linked_experiments: [{exp_slug}]
date_created: 2026-07-08
date_resolved: 2026-07-08
failure_reason: ""
---

## Hypothesis
The Codex migration can produce a paper plan from local evidence.

## Motivation
The paper needs explicit evidence mapping before drafting.

## Approach sketch
Use validated local fixtures and cited wiki papers.

## Novelty argument
The plan is derived from validated Codex migration evidence.

## Risks

## Lessons learned
""",
                encoding="utf-8",
            )
            (wiki / f"experiments/{exp_slug}.md").write_text(
                f"""---
title: Codex Paper Plan Experiment
slug: {exp_slug}
status: completed
linked_idea: {idea_slug}
hypothesis: local paper plan evidence is sufficient
tags: [codex, paper-plan]
setup:
  dataset: fixture
  model: local
  metrics: [accuracy]
outcome: succeeded
key_result: "The local fixture produced a complete evidence map."
date_completed: 2026-07-08
run_log: logs/{exp_slug}.log
started: "2026-07-08T00:00:00"
estimated_hours: 0
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Results
The experiment succeeded with deterministic local evidence.

## Analysis
The result supports drafting from wiki evidence.

## Idea updates
""",
                encoding="utf-8",
            )
            for slug in paper_slugs:
                (wiki / f"papers/{slug}.md").write_text(
                    f"""---
title: {slug.replace('-', ' ').title()}
slug: {slug}
tags: [codex, paper-plan]
importance: 4
arxiv: ""
doi: ""
year: 2026
---

## Problem & Context
Source evidence for the paper plan fixture.

## Key idea
This paper grounds the local paper plan.

## Experiment & Results
Relevant evidence is available in the wiki.

## Related

## My take
Useful citation candidate.
""",
                    encoding="utf-8",
                )

            out_slug = "paper-plan-codex-paper-plan-2026-07-08"
            output = wiki / f"outputs/{out_slug}.md"
            output.write_text(
                f"""---
title: "Codex Paper Plan"
venue: ICLR
date: 2026-07-08
target_ideas: [{idea_slug}]
---

## Evidence Map
| Idea | Status | linked experiments | Methods/Concepts | Section |
|------|--------|--------------------|------------------|---------|
| [[{idea_slug}]] | validated | [[{exp_slug}]] (succeeded) | local fixture | Method + Experiments |

## Section Outline
### 1. Introduction
Ideas addressed: [[{idea_slug}]]

### 2. Related Work
Key citations: [[{paper_slugs[0]}]], [[{paper_slugs[1]}]]

### 3. Method
Ideas addressed: [[{idea_slug}]]

### 4. Experiments
Evidence: [[{exp_slug}]]

## Figure/Table Plan
- Table 1: result summary from [[{exp_slug}]]

## Citation Plan
- [[{paper_slugs[0]}]] [UNCONFIRMED]
- [[{paper_slugs[1]}]] [UNCONFIRMED]

## Review LLM Review Summary
single-model review — cross-model verification unavailable
""",
                encoding="utf-8",
            )

            targets = [f"ideas/{idea_slug}", *(f"papers/{slug}" for slug in paper_slugs)]
            for target in targets:
                edge = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "tools/research_wiki.py"),
                        "add-edge",
                        str(wiki),
                        "--from",
                        f"outputs/{out_slug}",
                        "--to",
                        target,
                        "--type",
                        "derived_from",
                        "--evidence",
                        "Paper plan built from local wiki evidence",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(edge.returncode, 0, edge.stderr)

            rebuild = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "rebuild-context-brief", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(rebuild.returncode, 0, rebuild.stderr)
            log = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "log", str(wiki), f"paper-plan | ICLR paper outline for [[{idea_slug}]] | ideas: {idea_slug} | citations: 0/2"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(log.returncode, 0, log.stderr)

            edges = [
                json.loads(line)
                for line in (wiki / "graph/edges.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            derived = {(edge["from"], edge["to"], edge["type"]) for edge in edges}
            self.assertEqual(
                derived,
                {(f"outputs/{out_slug}", target, "derived_from") for target in targets},
            )
            plan_text = output.read_text(encoding="utf-8")
            self.assertIn(f"[[{idea_slug}]] | validated | [[{exp_slug}]] (succeeded)", plan_text)
            self.assertIn("[UNCONFIRMED]", plan_text)
            self.assertIn(f"paper-plan | ICLR paper outline for [[{idea_slug}]]", (wiki / "log.md").read_text(encoding="utf-8"))
            self.assertFalse(any(raw.rglob("*")), "paper-plan should not write raw files")

    def test_paper_draft_fixture_writes_integrity_checked_latex_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-paper-draft.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            paper = root / "paper"
            raw.mkdir()
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            idea_slug = "codex-paper-draft-idea"
            exp_slug = "codex-paper-draft-exp"
            paper_slugs = ["codex-paper-draft-source", "codex-paper-draft-baseline"]
            (wiki / f"ideas/{idea_slug}.md").write_text(
                f"""---
title: Codex Paper Draft Idea
slug: {idea_slug}
status: validated
origin: user
tags: [codex, paper-draft]
priority: 1
novelty_score: 4
target_venue: ICLR
origin_gaps: []
linked_experiments: [{exp_slug}]
date_created: 2026-07-08
date_resolved: 2026-07-08
failure_reason: ""
---

## Hypothesis
The Codex migration can draft from local wiki evidence.

## Motivation
The draft needs traceable paper artifacts before compilation.

## Approach sketch
Use a deterministic fixture to validate file and citation integrity.

## Novelty argument
The fixture checks Codex-safe paper generation boundaries.

## Risks

## Lessons learned
""",
                encoding="utf-8",
            )
            (wiki / f"experiments/{exp_slug}.md").write_text(
                f"""---
title: Codex Paper Draft Experiment
slug: {exp_slug}
status: completed
linked_idea: {idea_slug}
hypothesis: local paper draft artifacts are sufficient
tags: [codex, paper-draft]
setup:
  dataset: fixture
  model: local
  metrics: [accuracy]
outcome: succeeded
key_result: "The local fixture produced complete LaTeX artifacts."
date_completed: 2026-07-08
run_log: logs/{exp_slug}.log
started: "2026-07-08T00:00:00"
estimated_hours: 0
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Results
The experiment produced deterministic artifacts.

## Analysis
The result supports drafting from wiki evidence.

## Idea updates
""",
                encoding="utf-8",
            )
            for slug in paper_slugs:
                (wiki / f"papers/{slug}.md").write_text(
                    f"""---
title: {slug.replace('-', ' ').title()}
slug: {slug}
tags: [codex, paper-draft]
importance: 4
arxiv: ""
doi: ""
year: 2026
---

## Problem & Context
Source evidence for the paper draft fixture.

## Key idea
This paper grounds the local draft.

## Experiment & Results
Relevant evidence is available in the wiki.

## Related

## My take
Useful citation candidate.
""",
                    encoding="utf-8",
                )

            out_slug = "paper-plan-codex-paper-draft-2026-07-08"
            (wiki / f"outputs/{out_slug}.md").write_text(
                f"""---
title: "Codex Paper Draft Plan"
venue: ICLR
date: 2026-07-08
target_ideas: [{idea_slug}]
---

## Evidence Map
| Idea | Status | linked experiments | Methods/Concepts | Section |
|------|--------|--------------------|------------------|---------|
| [[{idea_slug}]] | validated | [[{exp_slug}]] (succeeded) | local fixture | Method + Experiments |

## Section Outline
### 1. Introduction
Ideas addressed: [[{idea_slug}]]

### 2. Related Work
Key citations: [[{paper_slugs[0]}]], [[{paper_slugs[1]}]]

### 3. Method
Ideas addressed: [[{idea_slug}]]

### 4. Experiments
Evidence: [[{exp_slug}]]

### 5. Conclusion
Lessons learned: [[{idea_slug}]]

## Figure/Table Plan
- Figure 1: artifact flow from [[{idea_slug}]]

## Citation Plan
- [[{paper_slugs[0]}]] [UNCONFIRMED]
- [[{paper_slugs[1]}]] verified
""",
                encoding="utf-8",
            )

            (paper / "sections").mkdir(parents=True)
            (paper / "figures").mkdir()
            (paper / "tables").mkdir()
            (paper / "math_commands.tex").write_text(
                "\\newcommand{\\FixtureSet}{\\mathcal{D}}\n",
                encoding="utf-8",
            )
            (paper / "main.tex").write_text(
                r"""\documentclass{article}
\input{math_commands}
\usepackage{booktabs,graphicx,amsmath,hyperref}

\title{Codex Paper Draft Fixture}
\author{}

\begin{document}
\maketitle
\begin{abstract}
This fixture checks the paper draft artifact contract.
\end{abstract}
\input{sections/introduction}
\input{sections/related_work}
\input{sections/method}
\input{sections/experiments}
\input{sections/conclusion}
\bibliography{references}
\bibliographystyle{plain}
\end{document}
""",
                encoding="utf-8",
            )
            (paper / "sections/introduction.tex").write_text(
                r"""The Codex migration needs a draft path whose files are traceable to wiki evidence.
The fixture follows a local paper plan and cites the source evidence~\cite{UNCONFIRMED_codex2026draftsource}.
Figure~\ref{fig:artifact-flow} summarizes the artifact flow.
""",
                encoding="utf-8",
            )
            (paper / "sections/related_work.tex").write_text(
                r"""The local baseline defines the write boundary for the draft fixture~\cite{codex2026draftbaseline}.
Unlike a full draft, this fixture validates citation and file integrity instead of prose quality.
""",
                encoding="utf-8",
            )
            (paper / "sections/method.tex").write_text(
                r"""We write every section from a known plan and shared notation in \FixtureSet.
\begin{figure}
\centering
\includegraphics{figures/artifact-flow.pdf}
\caption{Paper draft artifacts generated from a local plan.}
\label{fig:artifact-flow}
\end{figure}
""",
                encoding="utf-8",
            )
            (paper / "sections/experiments.tex").write_text(
                r"""We claim that the local fixture is sufficient to catch missing files and citations.
Table~\ref{tab:integrity} records the checked artifact counts.
\begin{table}
\caption{Integrity checks for the paper draft fixture.}
\label{tab:integrity}
\centering
\begin{tabular}{lc}
\toprule
Check & Count \\
\midrule
Sections & 5 \\
Citations & 2 \\
\bottomrule
\end{tabular}
\end{table}
""",
                encoding="utf-8",
            )
            (paper / "sections/conclusion.tex").write_text(
                r"""The fixture covers the local artifact contract and leaves full prose review to L3.
""",
                encoding="utf-8",
            )
            (paper / "figures/artifact-flow.pdf").write_bytes(b"%PDF-1.4\n% fixture\n")
            (paper / "references.bib").write_text(
                """@article{codex2026draftbaseline,
  title = {Codex Paper Draft Baseline},
  author = {Fixture, Local},
  year = {2026}
}

% [UNCONFIRMED] BibTeX not confirmed from DBLP/CrossRef - manual check required
@article{UNCONFIRMED_codex2026draftsource,
  title = {Codex Paper Draft Source},
  author = {Fixture, Local},
  year = {2026}
}
""",
                encoding="utf-8",
            )
            log = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "log",
                    str(wiki),
                    "paper-draft | drafted ICLR paper 'Codex Paper Draft Fixture' | 5 sections, 1 figures, 2 citations (1 verified)",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(log.returncode, 0, log.stderr)

            main_tex = (paper / "main.tex").read_text(encoding="utf-8")
            section_paths = [paper / f"{target}.tex" for target in re.findall(r"\\input\{(sections/[^}]+)\}", main_tex)]
            self.assertEqual(len(section_paths), 5)
            for path in section_paths:
                self.assertTrue(path.is_file(), path)

            tex_files = [paper / "main.tex", paper / "math_commands.tex", *section_paths]
            joined_tex = "\n".join(path.read_text(encoding="utf-8") for path in tex_files)
            figure_paths = [paper / target for target in re.findall(r"\\includegraphics(?:\[[^\]]+\])?\{([^}]+)\}", joined_tex)]
            self.assertEqual(figure_paths, [paper / "figures/artifact-flow.pdf"])
            for path in figure_paths:
                self.assertTrue(path.is_file(), path)

            citation_keys = {
                key.strip()
                for cite_group in re.findall(r"\\cite\{([^}]+)\}", joined_tex)
                for key in cite_group.split(",")
            }
            bib_text = (paper / "references.bib").read_text(encoding="utf-8")
            bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib_text))
            self.assertEqual(citation_keys, {"UNCONFIRMED_codex2026draftsource", "codex2026draftbaseline"})
            self.assertLessEqual(citation_keys, bib_keys)
            self.assertNotIn(r"\nocite{*}", joined_tex)

            refs = set(re.findall(r"\\ref\{([^}]+)\}", joined_tex))
            labels = set(re.findall(r"\\label\{([^}]+)\}", joined_tex))
            self.assertEqual(refs, {"fig:artifact-flow", "tab:integrity"})
            self.assertLessEqual(refs, labels)
            self.assertIn("% [UNCONFIRMED]", bib_text)
            self.assertIn("paper-draft | drafted ICLR paper", (wiki / "log.md").read_text(encoding="utf-8"))
            self.assertFalse(any(raw.rglob("*")), "paper-draft should not write raw files")

    def test_paper_compile_fixture_runs_codex_safe_checklist(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-paper-compile.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            ready = root / "paper-ready"
            blocked = root / "paper-blocked"
            raw.mkdir()
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            def write_paper(paper: Path, *, blocked_mode: bool) -> None:
                (paper / "sections").mkdir(parents=True)
                (paper / "figures").mkdir()
                (paper / "math_commands.tex").write_text(
                    "\\newcommand{\\CompileSet}{\\mathcal{C}}\n",
                    encoding="utf-8",
                )
                author = "AutoSci Migration Team" if blocked_mode else ""
                cite = "missing2026key" if blocked_mode else "codex2026compile"
                extra_marker = "% TODO: resolve this before submission\n" if blocked_mode else ""
                extra_bib = (
                    "\n% [UNCONFIRMED] BibTeX not confirmed from DBLP/CrossRef - manual check required\n"
                    "@article{UNCONFIRMED_codex2026compile,\n"
                    "  title = {Unconfirmed Compile Fixture},\n"
                    "  author = {Fixture, Local},\n"
                    "  year = {2026}\n"
                    "}\n"
                    if blocked_mode
                    else ""
                )
                (paper / "main.tex").write_text(
                    rf"""\documentclass{{article}}
\input{{math_commands}}
\usepackage{{graphicx,booktabs}}
\title{{Codex Paper Compile Fixture}}
\author{{{author}}}

\begin{{document}}
\maketitle
\begin{{abstract}}
This fixture validates the local paper compile checklist.
\end{{abstract}}
\input{{sections/introduction}}
\input{{sections/method}}
\bibliography{{references}}
\bibliographystyle{{plain}}
\end{{document}}
""",
                    encoding="utf-8",
                )
                (paper / "sections/introduction.tex").write_text(
                    rf"""The checklist fixture cites local evidence~\cite{{{cite}}}.
Figure~\ref{{fig:compile-flow}} shows the source boundary.
{extra_marker}""",
                    encoding="utf-8",
                )
                (paper / "sections/method.tex").write_text(
                    r"""The method checks \CompileSet{} without invoking TeX.
\begin{figure}
\centering
\includegraphics{figures/compile-flow}
\caption{Compile checklist source boundary.}
\label{fig:compile-flow}
\end{figure}
""",
                    encoding="utf-8",
                )
                (paper / "figures/compile-flow.pdf").write_bytes(b"%PDF-1.4\n% fixture\n")
                (paper / "references.bib").write_text(
                    """@article{codex2026compile,
  title = {Codex Paper Compile Fixture},
  author = {Fixture, Local},
  year = {2026}
}
""" + extra_bib,
                    encoding="utf-8",
                )

            write_paper(ready, blocked_mode=False)
            write_paper(blocked, blocked_mode=True)

            ready_run = subprocess.run(
                [sys.executable, str(ROOT / "tools/paper_compile_checks.py"), str(ready), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(ready_run.returncode, 0, ready_run.stderr)
            ready_report = json.loads(ready_run.stdout)
            self.assertTrue(ready_report["ok"])
            self.assertEqual(ready_report["blockers"], [])
            self.assertEqual(ready_report["warnings"], [])
            self.assertEqual(ready_report["details"]["citation_keys"], ["codex2026compile"])

            blocked_run = subprocess.run(
                [sys.executable, str(ROOT / "tools/paper_compile_checks.py"), str(blocked), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(blocked_run.returncode, 1)
            blocked_report = json.loads(blocked_run.stdout)
            self.assertFalse(blocked_report["ok"])
            blocker_checks = {item["check"] for item in blocked_report["blockers"]}
            warning_checks = {item["check"] for item in blocked_report["warnings"]}
            self.assertIn("citations", blocker_checks)
            self.assertIn("unconfirmed", blocker_checks)
            self.assertIn("todo", warning_checks)
            self.assertIn("anonymous", warning_checks)

            log = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "log",
                    str(wiki),
                    "paper-compile | checklist fixture | 0 errors, 1 [UNCONFIRMED], blocker path verified",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(log.returncode, 0, log.stderr)
            self.assertIn("paper-compile | checklist fixture", (wiki / "log.md").read_text(encoding="utf-8"))
            self.assertFalse(any(raw.rglob("*")), "paper-compile checklist should not write raw files")

    def test_poster_fixture_builds_validated_html_from_drafted_paper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-poster.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            paper = root / "paper"
            poster = root / "poster"
            raw.mkdir()
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            (wiki / "outputs/paper-plan-codex-poster-2026-07-08.md").write_text(
                """---
title: "Codex Poster Plan"
venue: ICLR
date: 2026-07-08
---

## Evidence Map
The poster fixture is grounded in a local drafted paper.
""",
                encoding="utf-8",
            )

            (paper / "sections").mkdir(parents=True)
            (paper / "figures").mkdir()
            (paper / "math_commands.tex").write_text(
                "\\newcommand{\\PosterSet}{\\mathcal{P}}\n",
                encoding="utf-8",
            )
            (paper / "figures/flow.png").write_bytes(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
                b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe"
                b"\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            (paper / "main.tex").write_text(
                r"""\documentclass{article}
\input{math_commands}
\usepackage{graphicx,booktabs}
\title{Codex Poster Fixture}
\author{AutoSci Migration Team}

\begin{document}
\maketitle
\input{sections/introduction}
\input{sections/method}
\input{sections/experiments}
\input{sections/conclusion}
\end{document}
""",
                encoding="utf-8",
            )
            (paper / "sections/introduction.tex").write_text(
                r"""\section{Introduction}
The Codex migration needs poster generation that reads a drafted paper and writes only presentation artifacts.
""",
                encoding="utf-8",
            )
            (paper / "sections/method.tex").write_text(
                r"""\section{Method}
We build a local poster DAG from \PosterSet{} and keep the source paper unchanged.
\begin{figure}
\centering
\includegraphics{figures/flow.png}
\caption{Local poster artifact flow.}
\label{fig:poster-flow}
\end{figure}
""",
                encoding="utf-8",
            )
            (paper / "sections/experiments.tex").write_text(
                r"""\section{Experiments}
The fixture validates HTML, copied images, and section structure without external services.
""",
                encoding="utf-8",
            )
            (paper / "sections/conclusion.tex").write_text(
                r"""\section{Conclusion}
The local path covers deterministic poster artifacts while screenshot rendering remains an environment-dependent check.
""",
                encoding="utf-8",
            )
            before_paper_files = {
                path.relative_to(paper): path.read_bytes()
                for path in paper.rglob("*")
                if path.is_file()
            }

            dag = poster / "dag.json"
            build_dag = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/wiki2dag.py"),
                    "build",
                    "--paper-dir",
                    str(paper),
                    "--output",
                    str(dag),
                    "--anonymous",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(build_dag.returncode, 0, build_dag.stderr)

            dag_data = json.loads(dag.read_text(encoding="utf-8"))
            root_node = dag_data["nodes"][0]
            self.assertEqual(root_node["name"], "Codex Poster Fixture")
            self.assertEqual(root_node["content"], "Anonymous")
            section_names = [node["name"] for node in dag_data["nodes"] if node.get("level") == 1]
            self.assertEqual(section_names, ["Introduction", "Method", "Experiments", "Conclusion"])
            visual_nodes = [node for node in dag_data["nodes"] if node.get("level") == 2]
            self.assertEqual(len(visual_nodes), 1)
            self.assertEqual(visual_nodes[0]["name"], "![](images/flow.png)")

            outline = poster / "outline.html"
            outline.write_text(
                """<section class="section">
  <div class="section-bar" contenteditable="true">Introduction</div>
  <div class="section-body" contenteditable="true">
    <p>The poster introduces a Codex migration artifact path grounded in the drafted paper.</p>
  </div>
</section>
<section class="section">
  <div class="section-bar" contenteditable="true">Method</div>
  <div class="section-body" contenteditable="true">
    <p>The method builds a DAG, injects the template, and keeps paper sources unchanged.</p>
    <div class="img-section">
      <img src="images/flow.png" alt="Local poster artifact flow." class="figure" />
    </div>
  </div>
</section>
<section class="section">
  <div class="section-bar" contenteditable="true">Experiments</div>
  <div class="section-body" contenteditable="true">
    <p>The fixture checks HTML structure, copied images, and validation without external services.</p>
  </div>
</section>
<section class="section">
  <div class="section-bar" contenteditable="true">Conclusion</div>
  <div class="section-body" contenteditable="true">
    <p>The deterministic path leaves only browser screenshot rendering for environment-level verification.</p>
  </div>
</section>
""",
                encoding="utf-8",
            )

            poster_html = poster / "poster.html"
            steps = [
                [
                    sys.executable,
                    str(ROOT / "tools/poster.py"),
                    "build",
                    "--template",
                    str(ROOT / "templates/poster/poster_template.html"),
                    "--outline",
                    str(outline),
                    "--output",
                    str(poster_html),
                ],
                [
                    sys.executable,
                    str(ROOT / "tools/poster.py"),
                    "inject-title",
                    "--dag",
                    str(dag),
                    "--anonymous",
                    str(poster_html),
                ],
                [
                    sys.executable,
                    str(ROOT / "tools/poster.py"),
                    "inject-header",
                    "--venue",
                    "ICLR 2026",
                    "--layout",
                    "corners",
                    str(poster_html),
                ],
                [
                    sys.executable,
                    str(ROOT / "tools/poster.py"),
                    "inject-figures",
                    "--dag",
                    str(dag),
                    "--paper-dir",
                    str(paper),
                    "--poster-dir",
                    str(poster),
                ],
                [sys.executable, str(ROOT / "tools/poster.py"), "validate", str(poster_html)],
            ]
            for step in steps:
                result = subprocess.run(step, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

            log = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "log",
                    str(wiki),
                    "poster | generated poster for 'Codex Poster Fixture' | 4 sections, 1 figures | reviewed: no",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(log.returncode, 0, log.stderr)

            html_text = poster_html.read_text(encoding="utf-8")
            self.assertIn("Codex Poster Fixture", html_text)
            self.assertIn("Anonymous", html_text)
            self.assertIn("ICLR 2026", html_text)
            self.assertIn('src="images/flow.png"', html_text)
            self.assertTrue((poster / "images/flow.png").is_file())
            self.assertTrue((poster / "dag.json").is_file())
            self.assertTrue((poster / "outline.html").is_file())
            self.assertNotIn("TODO", html_text)
            self.assertNotIn("FIXME", html_text)
            self.assertNotIn("[UNCONFIRMED]", html_text)
            after_paper_files = {
                path.relative_to(paper): path.read_bytes()
                for path in paper.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before_paper_files, after_paper_files)
            self.assertIn("poster | generated poster for 'Codex Poster Fixture'", (wiki / "log.md").read_text(encoding="utf-8"))
            self.assertFalse(any(raw.rglob("*")), "poster should not write raw files")

    def test_rebuttal_fixture_generates_traceable_outputs_without_raw_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-rebuttal.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            raw_reviews = raw / "reviews"
            raw_reviews.mkdir(parents=True)
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            review_file = raw_reviews / "r1.txt"
            review_file.write_text(
                """Reviewer 1
Score: Borderline
Weaknesses:
1. The method lacks an ablation proving the artifact boundary is necessary.
2. The limitation about unsupported remote canaries is unclear.
""",
                encoding="utf-8",
            )
            raw_snapshot = {
                path.relative_to(raw): path.read_bytes()
                for path in raw.rglob("*")
                if path.is_file()
            }

            idea_slug = "codex-rebuttal-idea"
            method_slug = "codex-rebuttal-method"
            exp_slug = "codex-rebuttal-exp"
            (wiki / f"ideas/{idea_slug}.md").write_text(
                f"""---
title: Codex Rebuttal Idea
slug: {idea_slug}
status: validated
origin: user
tags: [codex, rebuttal]
priority: 1
novelty_score: 4
target_venue: ICLR
origin_gaps: []
linked_experiments: [{exp_slug}]
date_created: 2026-07-08
date_resolved: 2026-07-08
failure_reason: ""
---

## Hypothesis
Codex migration rebuttals can cite local evidence without fabricating data.

## Motivation
Reviewer responses need traceability to wiki experiments.

## Approach sketch
Map concerns to wiki entities and respond from recorded evidence.

## Novelty argument
The response is grounded in deterministic local fixtures.

## Risks

## Lessons learned
""",
                encoding="utf-8",
            )
            (wiki / f"methods/{method_slug}.md").write_text(
                f"""---
title: Codex Rebuttal Method
slug: {method_slug}
tags: [codex, rebuttal]
source_papers: []
parent_methods: []
child_methods: []
---

## Mechanism
The method maps atomic reviewer concerns to wiki entities.

## Procedure
1. Atomize concerns.
2. Check local evidence.
3. Draft traceable responses.

## Assumptions

## Tradeoff profile

## Limitations
""",
                encoding="utf-8",
            )
            (wiki / f"experiments/{exp_slug}.md").write_text(
                f"""---
title: Codex Rebuttal Experiment
slug: {exp_slug}
status: completed
linked_idea: {idea_slug}
hypothesis: rebuttal evidence is traceable
tags: [codex, rebuttal]
setup:
  dataset: fixture
  model: local
  metrics: [coverage]
outcome: succeeded
key_result: "2/2 reviewer concerns were mapped and answered from local evidence."
date_completed: 2026-07-08
run_log: logs/{exp_slug}.log
started: "2026-07-08T00:00:00"
estimated_hours: 0
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Results
The fixture answered every concern with recorded local evidence.

## Analysis
The response is sufficient for a deterministic smoke test.

## Idea updates
""",
                encoding="utf-8",
            )

            slug_run = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "slug", "codex rebuttal fixture"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(slug_run.returncode, 0, slug_run.stderr)
            rebuttal_slug = slug_run.stdout.strip().splitlines()[-1]
            self.assertEqual(rebuttal_slug, "codex-rebuttal-fixture")

            rich = wiki / f"outputs/rebuttal-{rebuttal_slug}.md"
            formal = wiki / f"outputs/rebuttal-{rebuttal_slug}.txt"
            rich.write_text(
                f"""# Rebuttal Analysis: Codex Rebuttal Fixture

## Coverage Summary
| Concern ID | Type | Severity | Entity | Evidence Status | Review LLM Score | Strategy |
|------------|------|----------|--------|-----------------|------------------|----------|
| Rv1-C1 | missing | major | [[{idea_slug}]] | sufficient | stress-test skipped: Review LLM unavailable | A |
| Rv1-C2 | clarity | minor | [[{method_slug}]] | partial | stress-test skipped: Review LLM unavailable | C |

## Responses
### Reviewer 1
**[Rv1-C1]** The ablation concern is addressed by [[{exp_slug}]], whose key result reports 2/2 concern coverage from local evidence. We will add an explicit ablation-boundary sentence to Section 4 rather than claim new results.

**[Rv1-C2]** We agree the remote-canary limitation was underspecified. We will revise the limitation text to state that GitHub auth and DeepXiv token failures block remote verification, while local Codex paths are covered.

## Evidence Gap Analysis
| Entity | Status / Novelty | Gap | Needed |
|--------|------------------|-----|--------|
| [[{method_slug}]] | method | Remote canary limitation needs clearer wording | Clarify limitations, no status transition |

## Action Items
### Paper Edits
| Section | Change | Reason |
|---------|--------|--------|
| Section 4 | Add ablation-boundary sentence | Rv1-C1 |
| Limitations | Explain remote canary blocker explicitly | Rv1-C2 |

### Wiki Updates
| Page | Update | Reason |
|------|--------|--------|
| ideas/{idea_slug} | Append concern to `## Risks` | Rv1-C1 evidence framing |
| methods/{method_slug} | Append concern to `## Limitations` | Rv1-C2 limitation clarity |

## Review LLM Stress-Test Summary
- stress-test skipped: Review LLM unavailable

## Safety Checklist
- [x] No fabrication: all cited data exists in wiki/experiments
- [x] No overpromise: all committed edits are specific
- [x] Full coverage: 2/2 concerns addressed
- [x] Invalidated/inconclusive ideas not presented as supported
""",
                encoding="utf-8",
            )
            formal.write_text(
                f"""We thank the reviewer for the constructive feedback. We address each concern below.

Reviewer 1:

[Rv1-C1] The method lacks an ablation proving the artifact boundary is necessary.
The concern is addressed by the local evidence record in {exp_slug}, which reports 2/2 reviewer-concern coverage from local evidence. We will add a precise ablation-boundary sentence to Section 4 rather than claim new experimental results.

[Rv1-C2] The limitation about unsupported remote canaries is unclear.
We agree and will revise the limitation text to state that GitHub auth and DeepXiv token failures block remote verification, while local Codex paths are covered.

Summary of Revisions:
- Add a Section 4 sentence explaining the artifact-boundary ablation.
- Clarify the remote-canary limitation.
""",
                encoding="utf-8",
            )

            idea_path = wiki / f"ideas/{idea_slug}.md"
            idea_text = idea_path.read_text(encoding="utf-8")
            idea_path.write_text(
                idea_text.replace(
                    "## Risks\n",
                    "## Risks\n- Reviewer Rv1-C1 asked for a clearer ablation-boundary explanation; address in the paper without inventing new results.\n",
                    1,
                ),
                encoding="utf-8",
            )
            method_path = wiki / f"methods/{method_slug}.md"
            method_text = method_path.read_text(encoding="utf-8")
            method_path.write_text(
                method_text.replace(
                    "## Limitations\n",
                    "## Limitations\n- Reviewer Rv1-C2 found the remote-canary limitation unclear; state the GitHub auth and DeepXiv token blockers explicitly.\n",
                    1,
                ),
                encoding="utf-8",
            )
            log = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "log",
                    str(wiki),
                    "rebuttal | 2 concerns addressed | 1 evidence gaps | stress-test skipped",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(log.returncode, 0, log.stderr)

            raw_after = {
                path.relative_to(raw): path.read_bytes()
                for path in raw.rglob("*")
                if path.is_file()
            }
            self.assertEqual(raw_snapshot, raw_after)
            rich_text = rich.read_text(encoding="utf-8")
            formal_text = formal.read_text(encoding="utf-8")
            for concern in ("Rv1-C1", "Rv1-C2"):
                self.assertIn(concern, rich_text)
                self.assertIn(concern, formal_text)
            self.assertIn(f"[[{idea_slug}]]", rich_text)
            self.assertIn(f"[[{method_slug}]]", rich_text)
            self.assertIn(f"[[{exp_slug}]]", rich_text)
            self.assertIn("Full coverage: 2/2 concerns addressed", rich_text)
            self.assertIn("status: validated", idea_path.read_text(encoding="utf-8"))
            self.assertIn("Reviewer Rv1-C1", idea_path.read_text(encoding="utf-8"))
            self.assertIn("Reviewer Rv1-C2", method_path.read_text(encoding="utf-8"))
            self.assertIn("rebuttal | 2 concerns addressed", (wiki / "log.md").read_text(encoding="utf-8"))
            edges_path = wiki / "graph/edges.jsonl"
            self.assertFalse(edges_path.exists() and edges_path.read_text(encoding="utf-8").strip())

    def test_refine_fixture_applies_one_mocked_review_round_in_place(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-refine.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            raw.mkdir()
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            artifact = wiki / "outputs/codex-refine-artifact.md"
            artifact.write_text(
                """---
title: "Codex Refine Artifact"
slug: codex-refine-artifact
---

## Method
TODO: describe method.

## Evidence
The current draft mentions local checks but does not connect them to the migration goal.
""",
                encoding="utf-8",
            )
            raw_snapshot = {
                path.relative_to(raw): path.read_bytes()
                for path in raw.rglob("*")
                if path.is_file()
            }
            before_paths = sorted(path.relative_to(wiki) for path in wiki.rglob("*") if path.is_file())

            mocked_review = {
                "score": 5,
                "verdict": "needs-work",
                "actionable_items": [
                    {
                        "category": "A",
                        "severity": "major",
                        "issue": "Method description too vague",
                        "fix": "Add specific Codex migration steps",
                    },
                    {
                        "category": "B",
                        "severity": "major",
                        "issue": "Missing external DeepXiv success evidence",
                        "suggested_action": "$discover after DeepXiv token is fixed",
                    },
                ],
            }
            original = artifact.read_text(encoding="utf-8")
            refined = original.replace(
                "TODO: describe method.",
                "The method runs a bounded Codex migration check in three steps: locate the artifact, apply only review-scoped edits, and rebuild derived wiki context after wiki writes.",
            )
            refined += f"""

## Refine Notes
- Round 1 review score: {mocked_review["score"]}/10, verdict: {mocked_review["verdict"]}.
- Fixed [MAJOR] Method description too vague: added specific Codex migration steps.
- Unresolved [MAJOR] Missing external DeepXiv success evidence: retry `$discover` after the DeepXiv token is fixed.
- Termination reason: max rounds for deterministic smoke fixture.
"""
            artifact.write_text(refined, encoding="utf-8")

            for command in ("rebuild-context-brief", "rebuild-open-questions"):
                rebuild = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), command, str(wiki)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(rebuild.returncode, 0, rebuild.stderr)

            log = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "log",
                    str(wiki),
                    "refine | codex-refine-artifact | 1 rounds | score 5->7 | verdict: needs-work",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(log.returncode, 0, log.stderr)

            after_paths = sorted(path.relative_to(wiki) for path in wiki.rglob("*") if path.is_file())
            allowed_new = {
                Path("graph/context_brief.md"),
                Path("graph/open_questions.md"),
            }
            self.assertLessEqual(set(after_paths) - set(before_paths), allowed_new)
            refined_text = artifact.read_text(encoding="utf-8")
            self.assertNotIn("TODO: describe method.", refined_text)
            self.assertIn("bounded Codex migration check in three steps", refined_text)
            self.assertIn("Round 1 review score: 5/10", refined_text)
            self.assertIn("Unresolved [MAJOR] Missing external DeepXiv success evidence", refined_text)
            self.assertIn("`$discover` after the DeepXiv token is fixed", refined_text)
            self.assertIn("refine | codex-refine-artifact | 1 rounds | score 5->7", (wiki / "log.md").read_text(encoding="utf-8"))
            self.assertTrue((wiki / "graph/context_brief.md").is_file())
            self.assertTrue((wiki / "graph/open_questions.md").is_file())
            raw_after = {
                path.relative_to(raw): path.read_bytes()
                for path in raw.rglob("*")
                if path.is_file()
            }
            self.assertEqual(raw_snapshot, raw_after)

    def test_review_fixture_outputs_structured_single_model_report_without_writes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-review.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            raw.mkdir()
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            idea_slug = "codex-review-idea"
            method_slug = "codex-review-method"
            exp_slug = "codex-review-exp"
            (wiki / f"ideas/{idea_slug}.md").write_text(
                f"""---
title: Codex Review Idea
slug: {idea_slug}
status: proposed
origin: user
tags: [codex, review]
priority: 2
novelty_score: 3
target_venue: ICLR
origin_gaps: []
linked_experiments: [{exp_slug}]
date_created: 2026-07-08
date_resolved: ""
failure_reason: ""
---

## Hypothesis
Codex migration review reports can map weaknesses to wiki entities.

## Motivation
Structured review output should remain read-only.

## Approach sketch
Use local context and annotate missing evidence.

## Novelty argument
The review fallback is deterministic.

## Risks

## Lessons learned
""",
                encoding="utf-8",
            )
            (wiki / f"methods/{method_slug}.md").write_text(
                f"""---
title: Codex Review Method
slug: {method_slug}
tags: [codex, review]
source_papers: []
parent_methods: []
child_methods: []
---

## Mechanism
The method reviews artifacts using local evidence.

## Procedure
1. Read the artifact.
2. Map claims to wiki entities.
3. Emit structured findings.

## Assumptions

## Tradeoff profile

## Limitations
""",
                encoding="utf-8",
            )
            (wiki / f"experiments/{exp_slug}.md").write_text(
                f"""---
title: Codex Review Experiment
slug: {exp_slug}
status: completed
linked_idea: {idea_slug}
hypothesis: review output is structured
tags: [codex, review]
setup:
  dataset: fixture
  model: local
  metrics: [coverage]
outcome: inconclusive
key_result: "The fixture has structured output but no independent Review LLM."
date_completed: 2026-07-08
run_log: logs/{exp_slug}.log
started: "2026-07-08T00:00:00"
estimated_hours: 0
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Results
The local fixture produced a structured report.

## Analysis
Evidence remains inconclusive without the external Review LLM.

## Idea updates
""",
                encoding="utf-8",
            )
            artifact = wiki / "outputs/codex-review-artifact.md"
            artifact.write_text(
                f"""# Codex Review Artifact

The artifact claims that [[{idea_slug}]] is ready for migration, but it relies on
[[{method_slug}]] and [[{exp_slug}]] without explaining why inconclusive evidence
is sufficient.
""",
                encoding="utf-8",
            )
            before_wiki = {
                path.relative_to(wiki): path.read_bytes()
                for path in wiki.rglob("*")
                if path.is_file()
            }
            before_raw = {
                path.relative_to(raw): path.read_bytes()
                for path in raw.rglob("*")
                if path.is_file()
            }

            report = f"""# Review Report: Codex Review Artifact

## Meta
- **Artifact type**: paper-draft
- **Difficulty**: standard
- **Focus**: evidence
- **Reviewer**: single-model review, cross-model verification unavailable
- **Rounds**: 1

## Score: 6/10 — needs-work

## Strengths
1. The artifact names concrete wiki entities.
2. The read-only review path preserves source files.
3. The migration claim is scoped to Codex behavior.

## Weaknesses (by severity)

### Critical
- None.

### Major
- Evidence is inconclusive: [[{exp_slug}]] does not support a readiness claim. **Fix**: downgrade the claim or run `$exp-run` after external blockers are resolved.

### Minor
- The method dependency is thin: [[{method_slug}]] has no source papers. **Fix**: add source evidence through `$ingest`.

## Questions
1. Which external blocker must clear before the readiness claim becomes supported?

## Wiki Entity Mapping

### Ideas / methods needing stronger support
| Entity | Signal | Issue | Suggested action |
|--------|--------|-------|------------------|
| [[{idea_slug}]] | status proposed / novelty_score 3 | Readiness claim is stronger than evidence | Run `$exp-run` after blockers clear |
| [[{method_slug}]] | source_papers empty | Missing source-paper backing | Use `$ingest` for supporting papers |

### Knowledge gaps identified
| Gap | Related to | Suggested action |
|-----|-----------|------------------|
| External Review LLM unavailable | [[{idea_slug}]] | Retry `$review` when Review LLM is configured |

### Suggested wiki updates
- `wiki/ideas/{idea_slug}.md`: add risk factor from review
- `wiki/methods/{method_slug}.md`: tighten Limitations

## Actionable Items (ranked)
1. [MAJOR] Downgrade unsupported readiness language or rerun `$exp-run`.
2. [MINOR] Add source papers for [[{method_slug}]] with `$ingest`.
"""
            self.assertIn("Score: 6/10", report)
            self.assertIn("needs-work", report)
            self.assertIn("single-model review, cross-model verification unavailable", report)
            self.assertIn("## Wiki Entity Mapping", report)
            self.assertIn(f"[[{idea_slug}]]", report)
            self.assertIn(f"[[{method_slug}]]", report)
            self.assertIn(f"[[{exp_slug}]]", report)
            self.assertIn("**Fix**:", report)
            self.assertIn("[MAJOR]", report)
            self.assertIn("$review", report)
            after_wiki = {
                path.relative_to(wiki): path.read_bytes()
                for path in wiki.rglob("*")
                if path.is_file()
            }
            after_raw = {
                path.relative_to(raw): path.read_bytes()
                for path in raw.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before_wiki, after_wiki)
            self.assertEqual(before_raw, after_raw)

    def test_novelty_fixture_respects_read_only_default_and_write_flag_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-novelty.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            raw.mkdir()
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            idea_slug = "codex-novelty-idea"
            idea_path = wiki / f"ideas/{idea_slug}.md"
            idea_path.write_text(
                f"""---
title: Codex Novelty Idea
slug: {idea_slug}
status: proposed
origin: user
tags: [codex, novelty]
priority: 3
novelty_score: ""
target_venue: ICLR
origin_gaps: []
linked_experiments: []
date_created: 2026-07-08
date_resolved: ""
failure_reason: ""
---

## Hypothesis
Codex novelty checks should be read-only unless --write is explicitly set.

## Motivation
Novelty scoring can affect idea prioritization, so persistence must be narrow.

## Approach sketch
Use a local fixture to verify that only novelty_score changes on write.

## Novelty argument
The behavior is a migration safety property.

## Risks

## Lessons learned
""",
                encoding="utf-8",
            )
            (wiki / "papers/codex-novelty-prior.md").write_text(
                """---
title: Codex Novelty Prior
slug: codex-novelty-prior
tags: [codex, novelty]
importance: 3
arxiv: ""
doi: ""
year: 2026
---

## Problem & Context
Prior work used only local checks.

## Key idea
The fixture differs by testing write boundaries.

## Experiment & Results

## Related

## My take
""",
                encoding="utf-8",
            )
            before_read_only = {
                path.relative_to(wiki): path.read_bytes()
                for path in wiki.rglob("*")
                if path.is_file()
            }
            raw_snapshot = {
                path.relative_to(raw): path.read_bytes()
                for path in raw.rglob("*")
                if path.is_file()
            }

            report = f"""# Novelty Report: Codex Novelty Idea

## Score: 4/5 — Novel Combination

## Closest Prior Work
1. **Codex Novelty Prior** (2026) — local checks overlap with the proposed migration safety property.
   - Difference: the fixture explicitly verifies the `--write` persistence boundary.
   - Wiki link: [[codex-novelty-prior]]

## Review LLM Assessment
Review LLM cross-verify unavailable, single-model assessment only.

## Anti-repetition Check
- Failed ideas in wiki: none relevant
- In-progress ideas in wiki: none overlapping

## Recommendation
- **proceed**
- Rationale: proceed only as a local migration fixture; external prior-work search remains L2.
"""
            self.assertIn("Score: 4/5", report)
            self.assertIn("[[codex-novelty-prior]]", report)
            self.assertIn("single-model assessment only", report)
            after_read_only = {
                path.relative_to(wiki): path.read_bytes()
                for path in wiki.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before_read_only, after_read_only)

            write = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "set-meta",
                    str(idea_path),
                    "novelty_score",
                    "4",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(write.returncode, 0, write.stderr)
            log = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "log",
                    str(wiki),
                    f"novelty | wrote novelty_score=4 to ideas/{idea_slug}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(log.returncode, 0, log.stderr)

            idea_text = idea_path.read_text(encoding="utf-8")
            self.assertIn("novelty_score: 4", idea_text)
            self.assertIn("status: proposed", idea_text)
            self.assertIn("priority: 3", idea_text)
            self.assertIn(f"novelty | wrote novelty_score=4 to ideas/{idea_slug}", (wiki / "log.md").read_text(encoding="utf-8"))
            raw_after = {
                path.relative_to(raw): path.read_bytes()
                for path in raw.rglob("*")
                if path.is_file()
            }
            self.assertEqual(raw_snapshot, raw_after)

            after_write_files = {
                path.relative_to(wiki)
                for path in wiki.rglob("*")
                if path.is_file()
            }
            self.assertEqual(set(before_read_only) | {Path("log.md")}, after_write_files)

    def test_ideate_fixture_writes_phase4_ideas_edges_and_report_locally(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-ideate.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            raw.mkdir()
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            raw_snapshot = {
                path.relative_to(raw): path.read_bytes()
                for path in raw.rglob("*")
                if path.is_file()
            }
            before_maturity = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "maturity", str(wiki), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(before_maturity.returncode, 0, before_maturity.stderr)
            before_metrics = json.loads(before_maturity.stdout)
            self.assertIn("level", before_metrics)

            (wiki / "concepts/codex-ideate-gap.md").write_text(
                """---
title: Codex Ideate Gap
tags: [codex, ideate]
maturity: active
key_papers: [codex-ideate-source]
aliases: []
linked_ideas: []
---

## Definition
A local gap used by the ideate migration fixture.

## Variants

## Comparison

## Known limitations

## Open problems
- Need a Codex-safe Phase 4 write path.
""",
                encoding="utf-8",
            )
            (wiki / "papers/codex-ideate-source.md").write_text(
                """---
title: Codex Ideate Source
slug: codex-ideate-source
tags: [codex, ideate]
importance: 4
arxiv: ""
doi: ""
year: 2026
---

## Problem & Context
Source page for the ideate fixture.

## Key idea
The source inspires a Phase 4 write-boundary idea.

## Experiment & Results

## Related

## My take
""",
                encoding="utf-8",
            )

            slug_run = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "slug", "Codex Ideate Phase Four Boundary"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(slug_run.returncode, 0, slug_run.stderr)
            proposed_slug = slug_run.stdout.strip().splitlines()[-1]
            self.assertEqual(proposed_slug, "codex-ideate-phase-four-boundary")
            failed_slug = "codex-ideate-filtered-duplicate"

            (wiki / f"ideas/{proposed_slug}.md").write_text(
                f"""---
title: Codex Ideate Phase Four Boundary
slug: {proposed_slug}
status: proposed
origin: "ideate: Codex-safe Phase 4 write boundary"
origin_gaps: [codex-ideate-gap]
tags: [codex, ideate]
target_venue: ""
novelty_score: ""
priority: 3
pilot_result: ""
failure_reason: ""
linked_experiments: []
date_proposed: 2026-07-08
date_resolved: ""
---

## Motivation
The idea targets [[codex-ideate-gap]] and is inspired by [[codex-ideate-source]].

## Hypothesis
Codex can write ideate Phase 4 outputs without touching raw sources.

## Approach sketch
Create the idea page, add graph edges through `tools/research_wiki.py`, rebuild derived context, and append a log entry. The fixture uses `--skip-validation` semantics, so priority defaults to 3 and novelty_score stays blank.

## Novelty argument
The idea verifies migration mechanics rather than claiming scientific novelty.

## Target venue

## Risks
Feasibility: high. External search and Review LLM validation remain L2.

## Pilot results

## Lessons learned
""",
                encoding="utf-8",
            )
            (wiki / f"ideas/{failed_slug}.md").write_text(
                f"""---
title: Codex Ideate Filtered Duplicate
slug: {failed_slug}
status: failed
origin: "ideate: anti-repetition memory"
origin_gaps: [codex-ideate-gap]
tags: [codex, ideate]
target_venue: ""
novelty_score: ""
priority: 1
pilot_result: ""
failure_reason: "[filter] duplicates existing Codex migration fixture"
linked_experiments: []
date_proposed: 2026-07-08
date_resolved: 2026-07-08
---

## Motivation
This eliminated idea records anti-repetition memory for future ideate runs.

## Hypothesis
A duplicate idea should be retained as failed banlist context.

## Approach sketch
Store the filtered idea with a concrete failure reason.

## Novelty argument
Not novel; eliminated by the Phase 3 filter.

## Target venue

## Risks
Eliminated before pilot.

## Pilot results

## Lessons learned
""",
                encoding="utf-8",
            )

            edge_commands = [
                [
                    "--from",
                    f"ideas/{proposed_slug}",
                    "--to",
                    "concepts/codex-ideate-gap",
                    "--type",
                    "addresses_gap",
                    "--evidence",
                    "Generated by ideate Phase 4 fixture",
                ],
                [
                    "--from",
                    f"ideas/{proposed_slug}",
                    "--to",
                    "papers/codex-ideate-source",
                    "--type",
                    "inspired_by",
                    "--evidence",
                    "Inspired by source page in ideate fixture",
                ],
            ]
            for args in edge_commands:
                edge = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), "add-edge", str(wiki), *args],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(edge.returncode, 0, edge.stderr)

            for command in ("rebuild-context-brief", "rebuild-open-questions"):
                rebuild = subprocess.run(
                    [sys.executable, str(ROOT / "tools/research_wiki.py"), command, str(wiki)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(rebuild.returncode, 0, rebuild.stderr)
            log = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "log",
                    str(wiki),
                    "ideate | 1 ideas proposed, 1 ideas filtered out | direction: Codex migration",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(log.returncode, 0, log.stderr)

            after_maturity = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "maturity", str(wiki), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(after_maturity.returncode, 0, after_maturity.stderr)
            after_metrics = json.loads(after_maturity.stdout)
            self.assertGreaterEqual(after_metrics["ideas"], before_metrics["ideas"] + 2)

            edges = [
                json.loads(line)
                for line in (wiki / "graph/edges.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            edge_set = {(edge["from"], edge["to"], edge["type"]) for edge in edges}
            self.assertEqual(
                edge_set,
                {
                    (f"ideas/{proposed_slug}", "concepts/codex-ideate-gap", "addresses_gap"),
                    (f"ideas/{proposed_slug}", "papers/codex-ideate-source", "inspired_by"),
                },
            )
            proposed_text = (wiki / f"ideas/{proposed_slug}.md").read_text(encoding="utf-8")
            failed_text = (wiki / f"ideas/{failed_slug}.md").read_text(encoding="utf-8")
            self.assertIn("status: proposed", proposed_text)
            self.assertIn('novelty_score: ""', proposed_text)
            self.assertIn("priority: 3", proposed_text)
            self.assertIn("status: failed", failed_text)
            self.assertIn('failure_reason: "[filter] duplicates existing Codex migration fixture"', failed_text)
            self.assertIn("priority: 1", failed_text)
            self.assertTrue((wiki / "graph/context_brief.md").is_file())
            self.assertTrue((wiki / "graph/open_questions.md").is_file())
            self.assertIn("ideate | 1 ideas proposed, 1 ideas filtered out", (wiki / "log.md").read_text(encoding="utf-8"))
            raw_after = {
                path.relative_to(raw): path.read_bytes()
                for path in raw.rglob("*")
                if path.is_file()
            }
            self.assertEqual(raw_snapshot, raw_after)

    def test_visualize_generates_obsidian_and_canvas_artifacts_locally(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-visualize.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            raw.mkdir()
            (root / "config").mkdir()
            (root / "config/visualize.json").write_text(
                (ROOT / "config/visualize.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            (wiki / "papers/codex-visual-paper.md").write_text(
                """---
title: Codex Visual Paper
slug: codex-visual-paper
tags: [codex, visualize]
importance: 5
arxiv: ""
doi: ""
year: 2026
---

## Problem & Context
Local visualization fixture.

## Key idea
The paper introduces a concept.

## Experiment & Results

## Related

## My take
""",
                encoding="utf-8",
            )
            (wiki / "concepts/codex-visual-concept.md").write_text(
                """---
title: Codex Visual Concept
tags: [codex, visualize]
maturity: active
key_papers: [codex-visual-paper]
aliases: []
linked_ideas: []
---

## Definition
Concept node for visualization.

## Variants

## Comparison

## Known limitations

## Open problems
""",
                encoding="utf-8",
            )
            edge = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/research_wiki.py"),
                    "add-edge",
                    str(wiki),
                    "--from",
                    "papers/codex-visual-paper",
                    "--to",
                    "concepts/codex-visual-concept",
                    "--type",
                    "introduces_concept",
                    "--evidence",
                    "visualize local fixture",
                    "--confidence",
                    "high",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(edge.returncode, 0, edge.stderr)

            obsidian_dir = wiki / ".obsidian"
            obsidian_dir.mkdir()
            app_json = obsidian_dir / "app.json"
            app_json.write_text('{"userSetting": true}\n', encoding="utf-8")
            obsidian = subprocess.run(
                [sys.executable, str(ROOT / "tools/visualize.py"), "generate-obsidian-config", str(wiki)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(obsidian.returncode, 0, obsidian.stderr)
            self.assertEqual(app_json.read_text(encoding="utf-8"), '{"userSetting": true}\n')
            graph_config = json.loads((obsidian_dir / "graph.json").read_text(encoding="utf-8"))
            self.assertIn("path:papers/", graph_config["search"])
            self.assertFalse(graph_config["showTags"])
            self.assertEqual(len(graph_config["colorGroups"]), 9)

            canvas = subprocess.run(
                [sys.executable, str(ROOT / "tools/visualize.py"), "generate-canvas", str(wiki)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(canvas.returncode, 0, canvas.stderr)
            canvas_data = json.loads((wiki / "canvases/knowledge-map.canvas").read_text(encoding="utf-8"))
            node_ids = {node["id"] for node in canvas_data["nodes"]}
            self.assertEqual(node_ids, {"papers/codex-visual-paper", "concepts/codex-visual-concept"})
            self.assertEqual(canvas_data["edges"][0]["label"], "introduces_concept")

            focus = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/visualize.py"),
                    "generate-canvas",
                    str(wiki),
                    "--focus",
                    "papers/codex-visual-paper",
                    "--depth",
                    "1",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(focus.returncode, 0, focus.stderr)
            focus_data = json.loads((wiki / "canvases/focus-papers-codex-visual-paper.canvas").read_text(encoding="utf-8"))
            self.assertEqual({node["id"] for node in focus_data["nodes"]}, node_ids)
            self.assertFalse(any(raw.rglob("*")), "visualize should not write raw files")

    def test_spa_intents_surface_codex_commands_and_docs(self) -> None:
        cases = {
            "ingest": ({"path": "raw/tmp/example.tex"}, "/ingest raw/tmp/example.tex"),
            "ask": ({"question": "what is in the wiki?"}, "/ask what is in the wiki?"),
            "check": ({}, "/check"),
            "discover": ({"topic": "retrieval augmented generation", "limit": "3"}, '/discover --topic "retrieval augmented generation" --limit 3'),
        }
        for skill, (body, command) in cases.items():
            payload = self._intent_payload(skill, body)
            self.assertEqual(payload["command"], command)
            self.assertEqual(payload["codex_command"], "$" + command[1:])
            self.assertEqual(payload["doc_url"], f".claude/skills/{skill}/SKILL.md")
            self.assertEqual(payload["codex_doc_url"], f".agents/skills/{skill}/SKILL.md")

    def test_discover_docs_keep_it_proposal_only(self) -> None:
        discover = (ROOT / ".agents/skills/discover/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Never auto-ingest", discover)
        self.assertIn("No writes to `raw/`", discover)
        self.assertIn("Venue runs: none", discover.replace("venue runs", "Venue runs"))
        self.assertIn("Do not ingest anything yourself. The user picks.", discover)

    def test_discover_topic_shortlist_checkpoint_is_proposal_only(self) -> None:
        discover = self._load_discover_without_sandbox()

        def snapshot(base: Path) -> dict[str, bytes]:
            return {
                str(path.relative_to(base)): path.read_bytes()
                for path in sorted(base.rglob("*"))
                if path.is_file()
            }

        with tempfile.TemporaryDirectory(prefix="autosci-discover-proposal-smoke.") as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw/papers"
            checkpoints = root / ".checkpoints"
            raw.mkdir(parents=True)
            checkpoints.mkdir()

            init = subprocess.run(
                [sys.executable, str(ROOT / "tools/research_wiki.py"), "init", str(wiki)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            raw_file = raw / "user-owned-discover.tex"
            raw_file.write_text("\\section{Discover should not write raw}\n", encoding="utf-8")
            known = wiki / "papers/already-known-discover-paper.md"
            known.write_text(
                """---
title: Already Known Discover Paper
slug: already-known-discover-paper
arxiv: "2601.00001"
tags: [discover]
importance: 3
---

## Problem & Context
This paper is already in the wiki and should be filtered out.
""",
                encoding="utf-8",
            )
            before_wiki = snapshot(wiki)
            before_raw = snapshot(raw.parent)

            original_gather = discover._gather_from_topic

            def fake_gather(topic: str, limit: int) -> list[dict]:
                self.assertEqual(topic, "codex proposal only")
                self.assertGreaterEqual(limit, 8)
                return [
                    {
                        "paperId": "duplicate",
                        "arxiv_id": "2601.00001",
                        "title": "Already Known Discover Paper",
                        "year": 2026,
                        "citation_count": 99,
                        "influential_citation_count": 10,
                        "max_h_index": 40,
                        "_sources": ["s2_search"],
                    },
                    {
                        "paperId": "new-a",
                        "arxiv_id": "2601.00002",
                        "title": "Codex Proposal Candidate A",
                        "year": 2026,
                        "citation_count": 12,
                        "influential_citation_count": 2,
                        "max_h_index": 20,
                        "tldr": "A deterministic candidate for proposal-only discovery.",
                        "_sources": ["s2_search"],
                    },
                    {
                        "paperId": "new-b",
                        "arxiv_id": "2601.00003",
                        "title": "Codex Proposal Candidate B",
                        "year": 2025,
                        "citation_count": 5,
                        "influential_citation_count": 1,
                        "max_h_index": 15,
                        "_sources": ["deepxiv"],
                    },
                ]

            try:
                discover._gather_from_topic = fake_gather
                payload = discover.build_shortlist(
                    mode="topic",
                    topic="codex proposal only",
                    wiki_root=wiki,
                    limit=2,
                )
            finally:
                discover._gather_from_topic = original_gather

            self.assertEqual(payload["seed"], {"mode": "topic", "topic": "codex proposal only"})
            self.assertEqual(payload["wiki_dedup_count"], 1)
            self.assertEqual(payload["shortlist_count"], 2)
            self.assertEqual(
                [item["arxiv_id"] for item in payload["shortlist"]],
                ["2601.00002", "2601.00003"],
            )
            self.assertNotIn("2601.00001", json.dumps(payload))
            self.assertIn("_score", payload["shortlist"][0])
            self.assertIn("_rationale", payload["shortlist"][0])

            out_path = discover._resolve_output_checkpoint_path(checkpoints, discover._slugify("codex proposal only"))
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            checkpoint_payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint_payload["shortlist_count"], 2)
            self.assertTrue(out_path.name.startswith("discover-codex-proposal-only-"))

            markdown = discover._format_markdown(payload)
            self.assertIn("# Discover shortlist (topic)", markdown)
            self.assertIn("Codex Proposal Candidate A", markdown)
            self.assertIn("Codex Proposal Candidate B", markdown)
            self.assertNotIn("Already Known Discover Paper", markdown)
            self.assertEqual(snapshot(wiki), before_wiki)
            self.assertEqual(snapshot(raw.parent), before_raw)

    def test_daily_arxiv_reference_docs_keep_secret_exposure_boundary(self) -> None:
        references = [
            ROOT / "i18n/en/skills/daily-arxiv/references/automation-scaffold.md",
            ROOT / "i18n/zh/skills/daily-arxiv/references/automation-scaffold.md",
        ]
        for path in references:
            text = path.read_text(encoding="utf-8")
            self.assertIn("Workflow Env Exposures", text, path)
            self.assertIn("SEMANTIC_SCHOLAR_API_KEY", text, path)
            self.assertIn("DEEPXIV_TOKEN", text, path)
            self.assertIn("Codex", text, path)
            self.assertIn("inform", text, path)

    def test_daily_arxiv_deployment_docs_keep_codex_auto_ingest_canary(self) -> None:
        docs = (ROOT / "docs/daily-arxiv-deployment.md").read_text(encoding="utf-8")
        self.assertIn("Codex CI auto-ingest is not implemented", docs)
        self.assertIn("Negative canary: must fail before prepare/recommend/commit", docs)
        self.assertIn("-f mode=auto-ingest", docs)
        self.assertIn("-f recommender=codex", docs)
        self.assertIn("Validate recommender credentials", docs)
        self.assertIn("A green result here is a regression", docs)
        self.assertIn("replace `main` with the branch under test", docs)
        self.assertIn("legacy Claude Code Action auth", docs)
        self.assertIn("force-stages only `wiki` and `raw/discovered`", docs)
        self.assertIn("raw/papers/`,", docs)
        self.assertIn("tools/lint.py --wiki-dir wiki --json", docs)

        matrix = (ROOT / "docs/codex-smoke-test-matrix.md").read_text(encoding="utf-8")
        self.assertIn("gh auth status -h github.com", matrix)
        self.assertIn("invalid token", matrix)
        self.assertIn("--ref <branch-under-test>", matrix)
        self.assertIn("use `--ref main` only after the migration is merged", matrix)

        workflow = (ROOT / ".github/workflows/daily-arxiv.yml").read_text(encoding="utf-8")
        self.assertIn(
            'if [ "$DAILY_ARXIV_MODE" = "auto-ingest" ] && [ "$DAILY_ARXIV_RECOMMENDER" != "auto" ] && [ "$DAILY_ARXIV_RECOMMENDER" != "claude-action" ]; then',
            workflow,
        )
        self.assertIn("Codex, review-llm, and tool recommenders are inform-mode only", workflow)
        self.assertIn("steps.resolve.outputs.mode == 'inform'", workflow)

    def test_smoke_matrix_records_review_llm_configuration_blocker(self) -> None:
        matrix = (ROOT / "docs/codex-smoke-test-matrix.md").read_text(encoding="utf-8")
        self.assertIn("Review LLM configuration probe", matrix)
        self.assertIn("`LLM_API_KEY`, `LLM_BASE_URL`, and", matrix)
        self.assertIn("`LLM_MODEL` are all unset", matrix)
        self.assertIn("$review", matrix)
        self.assertIn("$refine", matrix)
        self.assertIn("$rebuttal", matrix)
        self.assertIn("$novelty", matrix)
        self.assertIn("$exp-eval", matrix)
        self.assertIn("$paper-plan", matrix)
        self.assertIn("daily-arxiv `recommender=review-llm`", matrix)
        self.assertIn("minimal Review LLM call", matrix)

    def test_smoke_matrix_records_network_provider_configuration_blocker(self) -> None:
        matrix = (ROOT / "docs/codex-smoke-test-matrix.md").read_text(encoding="utf-8")
        self.assertIn("network-provider configuration", matrix)
        self.assertIn("`SEMANTIC_SCHOLAR_API_KEY`,", matrix)
        self.assertIn("`DEEPXIV_TOKEN`, `S2_MAX_RETRIES`, and", matrix)
        self.assertIn("`S2_RATE_LIMIT_WAIT_SECONDS` are all", matrix)
        self.assertIn("S2 calls use unauthenticated rate", matrix)
        self.assertIn("DeepXiv has no usable configured token", matrix)
        self.assertIn("$discover", matrix)
        self.assertIn("$daily-arxiv", matrix)


if __name__ == "__main__":
    unittest.main()
