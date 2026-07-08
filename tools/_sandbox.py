"""Shared sandbox gate for AutoSci network tools.

When a tool runs inside a Codex sandbox, socket(2) is blocked by seccomp and
the tool cannot reach any network (Semantic Scholar, DeepXiv, arXiv, or
binding localhost ports).  This module probes for that condition at import
time and, if sandboxed, prints an actionable message to stderr and exits
with code 126.

The message tells the coding agent exactly which prefix rule to request and
what justification to include, so the agent can emit a single
`require_escalated` call rather than silently degrading.

Tools that need network access should import this module _after_ `_env`:

    import _env   # noqa: F401 — loads API keys from .env files
    import _sandbox  # noqa: F401 — sandbox gate, exits if blocked
"""

from __future__ import annotations

import os
import sys


JUSTIFICATIONS: dict[str, str] = {
    "discover.py": "AutoSci discover needs network access (S2/DeepXiv)",
    "init_discovery.py": "AutoSci init discovery needs network access (S2/DeepXiv/arXiv)",
    "fetch_s2.py": "AutoSci fetch_s2 needs network access",
    "fetch_deepxiv.py": "AutoSci fetch_deepxiv needs network access",
    "fetch_arxiv.py": "AutoSci fetch_arxiv needs network access",
    "fetch_wikipedia.py": "AutoSci fetch_wikipedia needs network access",
    "daily_arxiv.py": "AutoSci daily_arxiv needs network access",
    "prepare_paper_source.py": "AutoSci prepare_paper_source needs network access",
    "backfill_citations.py": "AutoSci backfill_citations needs network access",
    "serve.py": "AutoSci serve needs network access",
}


def _check() -> None:
    """Probe socket access.  If blocked, print escalation guide and exit 126."""

    sandboxed = False
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.close()
    except PermissionError:
        sandboxed = True
    except Exception:
        pass

    if not sandboxed:
        return

    tool = os.path.basename(sys.argv[0]) if sys.argv else "this tool"
    justification = JUSTIFICATIONS.get(tool, f"AutoSci {tool} needs network access")

    print(
        f"\n╔══════════════════════════════════════════════════════════════╗\n"
        f"║  SANDBOX GATE: {tool} needs network access\n"
        f"║\n"
        f"║  The Codex sandbox blocks socket(2).  This tool cannot\n"
        f"║  make outbound connections or bind localhost ports.\n"
        f"║\n"
        f"║  The agent must rerun the command with:\n"
        f"║    sandbox_permissions = \"require_escalated\"\n"
        f"║    justification = \"{justification}\"\n"
        f"║    prefix_rule = [\"{sys.executable}\", \"tools/{tool}\"]\n"
        f"║\n"
        f"║  See AGENTS.md § \"Sandbox—escalation contract\" for the\n"
        f"║  full prefix-rule table and escalation playbook.\n"
        f"╚══════════════════════════════════════════════════════════════╝\n\n",
        file=sys.stderr,
    )
    sys.exit(126)


_check()
