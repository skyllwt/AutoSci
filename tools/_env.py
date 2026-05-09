"""Shared environment loader for OmegaWiki tools.

Loads environment variables from .env files so that API keys configured
by the user are available even when Claude Code spawns a fresh shell.

Load order (later files do NOT override earlier ones):
  1. ~/.env          (global, e.g. DEEPXIV_TOKEN auto-registered here)
  2. ./.env          (project-level, created by setup.sh)
  3. os.environ      (always takes precedence — already-set vars are never overwritten)

Usage in any tool:
    import _env  # noqa: F401  (side-effect import, loads env vars)
"""

from __future__ import annotations

import os
import pathlib

_LOADED = False


def load() -> None:
    """Load .env files into os.environ (idempotent)."""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True

    for env_path in [pathlib.Path.home() / ".env", pathlib.Path(".env")]:
        if not env_path.exists():
            continue
        try:
            for line in env_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Never override existing env vars
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            pass


# Auto-load on import
load()
