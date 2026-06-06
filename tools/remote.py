#!/usr/bin/env python3
"""Remote GPU Server Operations.

Unified SSH tool for remote experiment execution: server status, GPU
monitoring, code sync, environment setup, job launch/monitor, and result
retrieval.

Called by skills via:  Bash: python3 tools/remote.py <command> [args]

Commands:
    status                              Server connectivity + GPU overview
    gpu-status                          Detailed GPU usage per card
    sync-code [--dry-run]               rsync project code to remote
    setup-env [--requirements FILE]     Install Python dependencies on remote
    launch --name S --cmd C [--gpu N]   Start screen session on remote
    check --name S                      Check session alive + anomaly detection
    tail-log --name S [--lines N]       Get recent log output from remote
    pull-results --remote-path P --local-path P   Download result files
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATHS = [
    "config/server.yaml",
    "../config/server.yaml",
]

REQUIRED_FIELDS = {"host", "user", "work_dir"}

DEFAULT_SYNC_INCLUDE = [
    "*.py", "*.yaml", "*.yml", "*.json", "*.txt", "*.sh",
    "*.toml", "*.cfg", "Makefile", "Dockerfile", "requirements*.txt",
]

DEFAULT_SYNC_EXCLUDE = [
    ".git/", "__pycache__/", "*.pyc", "data/", "wandb/",
    "checkpoints/", "*.pt", "*.pth", "*.ckpt", "*.safetensors",
    "*.bin", ".venv/", "node_modules/",
]

PULL_DEFAULT_EXCLUDE = [
    "*.pt", "*.pth", "*.ckpt", "*.safetensors", "*.bin",
]

FREE_GPU_THRESHOLD_MIB = 500

# Anomaly patterns in training logs
ANOMALY_PATTERNS = [
    (re.compile(r"\bnan\b", re.IGNORECASE), "NaN detected"),
    (re.compile(r"CUDA out of memory|OutOfMemoryError|OOM", re.IGNORECASE), "OOM"),
    (re.compile(r"Traceback \(most recent call last\)"), "Traceback/crash"),
    (re.compile(r"RuntimeError|ValueError|KeyError|FileNotFoundError"), "Runtime error"),
    (re.compile(r"loss\s*[:=]\s*inf\b", re.IGNORECASE), "Infinite loss"),
]

# ---------------------------------------------------------------------------
# YAML parser (lightweight, no PyYAML dependency)
# ---------------------------------------------------------------------------


def _parse_yaml(text: str) -> dict:
    """Parse a simple YAML file into a dict.

    Supports: scalars, inline lists [a, b], block lists (- item),
    nested dicts (via indentation), comments (#), quoted strings.
    Enough for server.yaml; not a full YAML parser.
    """
    result: dict = {}
    stack: list[tuple[int, dict]] = [(-1, result)]
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.split("#")[0].rstrip() if "#" in line and not _in_quotes(line) else line.rstrip()
        i += 1
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        indent = len(stripped) - len(stripped.lstrip())
        stripped = stripped.lstrip()
        # Pop stack to find parent
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            stack = [(-1, result)]
        parent = stack[-1][1]

        if stripped.startswith("- "):
            # List item — parent should already be a list
            val = _parse_scalar(stripped[2:].strip())
            if isinstance(parent, list):
                parent.append(val)
            continue

        if ":" not in stripped:
            continue
        colon_idx = stripped.index(":")
        key = stripped[:colon_idx].strip().strip('"').strip("'")
        rest = stripped[colon_idx + 1:].strip()

        if not rest:
            # Could be dict or list — peek at next non-empty line
            j = i
            while j < len(lines):
                nxt = lines[j].split("#")[0].rstrip() if "#" in lines[j] and not _in_quotes(lines[j]) else lines[j].rstrip()
                if nxt.strip():
                    break
                j += 1
            if j < len(lines) and nxt.lstrip().startswith("- "):
                child: list | dict = []
            else:
                child = {}
            parent[key] = child
            stack.append((indent, child))
        elif rest.startswith("[") and rest.endswith("]"):
            # Inline list
            inner = rest[1:-1]
            items = [_parse_scalar(s.strip()) for s in inner.split(",") if s.strip()]
            parent[key] = items
        elif rest.startswith("{") and rest.endswith("}"):
            # Inline dict
            inner = rest[1:-1].strip()
            if not inner:
                parent[key] = {}
            else:
                d = {}
                for pair in inner.split(","):
                    if ":" in pair:
                        k, v = pair.split(":", 1)
                        d[k.strip().strip('"').strip("'")] = _parse_scalar(v.strip())
                parent[key] = d
        else:
            parent[key] = _parse_scalar(rest)
    return result


def _in_quotes(line: str) -> bool:
    """Check if # appears inside quotes (rough heuristic)."""
    in_single = False
    in_double = False
    for ch in line:
        if ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == "#" and not in_single and not in_double:
            return False
    return True


def _parse_scalar(val: str):
    """Parse a YAML scalar value."""
    if not val or val == '""' or val == "''":
        return ""
    # Strip quotes
    if (val.startswith('"') and val.endswith('"')) or \
       (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    # Booleans
    if val.lower() in ("true", "yes"):
        return True
    if val.lower() in ("false", "no"):
        return False
    # Numbers
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def _find_config(explicit_path: str | None) -> Path:
    """Find server config file."""
    if explicit_path:
        p = Path(explicit_path)
        if not p.exists():
            _error(f"Config file not found: {explicit_path}")
        return p
    for candidate in DEFAULT_CONFIG_PATHS:
        p = Path(candidate)
        if p.exists():
            return p
    _error(
        "No server config found. Create config/server.yaml from "
        "config/server.yaml.example"
    )
    return Path()  # unreachable


def load_config(config_path: str | None = None) -> dict:
    """Load and validate server configuration."""
    path = _find_config(config_path)
    text = path.read_text(encoding="utf-8")
    cfg = _parse_yaml(text)

    # Validate required fields
    missing = REQUIRED_FIELDS - set(cfg.keys())
    if missing:
        _error(f"Missing required fields in {path}: {', '.join(sorted(missing))}")

    # Must have conda or env_setup
    has_conda = isinstance(cfg.get("conda"), dict) and cfg["conda"].get("path") and cfg["conda"].get("env")
    has_env_setup = bool(cfg.get("env_setup"))
    if not has_conda and not has_env_setup:
        _error(
            f"Config must have either 'conda' (with path + env) or "
            f"'env_setup' in {path}"
        )

    # Defaults
    cfg.setdefault("port", 22)
    cfg.setdefault("identity_file", "")
    cfg.setdefault("proxy_jump", "")
    cfg.setdefault("ssh_options", {})
    cfg.setdefault("gpus", "unknown")
    cfg.setdefault("free_gpu_threshold_mib", FREE_GPU_THRESHOLD_MIB)
    sync = cfg.setdefault("sync", {})
    sync.setdefault("include", DEFAULT_SYNC_INCLUDE)
    sync.setdefault("exclude", DEFAULT_SYNC_EXCLUDE)

    return cfg


# ---------------------------------------------------------------------------
# SSH helpers
# ---------------------------------------------------------------------------


def build_ssh_cmd(cfg: dict) -> list[str]:
    """Build base SSH command array from config."""
    cmd = ["ssh"]
    port = cfg.get("port", 22)
    if port != 22:
        cmd += ["-p", str(port)]
    identity = cfg.get("identity_file", "")
    if identity:
        cmd += ["-i", os.path.expanduser(identity)]
    proxy = cfg.get("proxy_jump", "")
    if proxy:
        cmd += ["-J", proxy]
    for k, v in cfg.get("ssh_options", {}).items():
        cmd += ["-o", f"{k}={v}"]
    cmd += ["-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
    cmd.append(f"{cfg['user']}@{cfg['host']}")
    return cmd


def build_ssh_transport(cfg: dict) -> str:
    """Build SSH transport string for rsync -e option."""
    parts = ["ssh"]
    port = cfg.get("port", 22)
    if port != 22:
        parts.append(f"-p {port}")
    identity = cfg.get("identity_file", "")
    if identity:
        parts.append(f"-i {os.path.expanduser(identity)}")
    proxy = cfg.get("proxy_jump", "")
    if proxy:
        parts.append(f"-J {proxy}")
    for k, v in cfg.get("ssh_options", {}).items():
        parts.append(f"-o {k}={v}")
    parts += ["-o ConnectTimeout=10", "-o BatchMode=yes"]
    return " ".join(parts)


def run_ssh(cfg: dict, remote_cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    """Execute a command on the remote server via SSH."""
    cmd = build_ssh_cmd(cfg) + [remote_cmd]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"SSH command timed out after {timeout}s"
    except FileNotFoundError:
        return -1, "", "ssh command not found"


def conda_prefix(cfg: dict) -> str:
    """Generate conda activation prefix command."""
    conda_cfg = cfg.get("conda")
    if conda_cfg and conda_cfg.get("path") and conda_cfg.get("env"):
        conda_bin = shlex.quote(conda_cfg["path"].rstrip("/") + "/bin/conda")
        env_name = shlex.quote(conda_cfg["env"])
        return (
            f'eval "$({conda_bin} shell.bash hook)" && '
            f'conda activate {env_name}'
        )
    env_setup = cfg.get("env_setup", "")
    if env_setup:
        return env_setup
    return ""


# ---------------------------------------------------------------------------
# nvidia-smi parsing
# ---------------------------------------------------------------------------


def parse_nvidia_smi(csv_output: str, threshold: int = FREE_GPU_THRESHOLD_MIB) -> list[dict]:
    """Parse nvidia-smi CSV output into structured GPU info."""
    gpus = []
    for line in csv_output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            continue
        try:
            gpu = {
                "index": int(parts[0]),
                "name": parts[1],
                "memory_used_mib": int(float(parts[2])),
                "memory_total_mib": int(float(parts[3])),
            }
            if len(parts) >= 5:
                gpu["utilization_pct"] = int(float(parts[4]))
            if len(parts) >= 6:
                gpu["temperature_c"] = int(float(parts[5]))
            gpu["free"] = gpu["memory_used_mib"] < threshold
            gpu["free_memory_mib"] = gpu["memory_total_mib"] - gpu["memory_used_mib"]
            gpus.append(gpu)
        except (ValueError, IndexError):
            continue
    return gpus


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------


def detect_anomalies(lines: list[str]) -> list[dict]:
    """Scan log lines for training anomalies."""
    found = []
    seen_types = set()
    for i, line in enumerate(lines):
        for pattern, label in ANOMALY_PATTERNS:
            if label not in seen_types and pattern.search(line):
                found.append({
                    "type": label,
                    "line_number": i,
                    "content": line.strip()[:200],
                })
                seen_types.add(label)
    return found


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _ok(data: dict) -> None:
    data["status"] = "ok"
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(0)


def _error(msg: str) -> None:
    print(json.dumps({"status": "error", "message": msg}, ensure_ascii=False))
    sys.exit(1)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_status(cfg: dict) -> None:
    """Check server connectivity and GPU overview."""
    # Connectivity
    rc, stdout, stderr = run_ssh(cfg, "echo ok", timeout=10)
    if rc != 0:
        _ok({
            "reachable": False,
            "host": cfg["host"],
            "error": stderr.strip() or "Connection failed",
        })

    # GPU status
    rc, stdout, stderr = run_ssh(
        cfg,
        "nvidia-smi --query-gpu=index,name,memory.used,memory.total,"
        "utilization.gpu,temperature.gpu --format=csv,noheader,nounits",
        timeout=15,
    )
    gpus = []
    if rc == 0:
        gpus = parse_nvidia_smi(stdout, cfg.get("free_gpu_threshold_mib", FREE_GPU_THRESHOLD_MIB))

    free_indices = [g["index"] for g in gpus if g.get("free")]
    _ok({
        "reachable": True,
        "host": cfg["host"],
        "user": cfg["user"],
        "gpus_description": cfg.get("gpus", "unknown"),
        "work_dir": cfg["work_dir"],
        "gpu_count": len(gpus),
        "free_gpus": free_indices,
        "gpus": gpus,
    })


def cmd_gpu_status(cfg: dict) -> None:
    """Detailed GPU usage per card."""
    rc, stdout, stderr = run_ssh(
        cfg,
        "nvidia-smi --query-gpu=index,name,memory.used,memory.total,"
        "utilization.gpu,temperature.gpu --format=csv,noheader,nounits",
        timeout=15,
    )
    if rc != 0:
        _error(f"nvidia-smi failed: {stderr.strip() or 'command not found or SSH error'}")

    threshold = cfg.get("free_gpu_threshold_mib", FREE_GPU_THRESHOLD_MIB)
    gpus = parse_nvidia_smi(stdout, threshold)
    free_indices = [g["index"] for g in gpus if g.get("free")]
    _ok({
        "host": cfg["host"],
        "gpus": gpus,
        "free_gpus": free_indices,
        "total_free_memory_mib": sum(g["free_memory_mib"] for g in gpus if g.get("free")),
    })


def cmd_sync_code(cfg: dict, args: argparse.Namespace) -> None:
    """Sync project code to remote server via rsync."""
    local_path = args.local_path or "."
    work_dir = cfg["work_dir"]

    # Ensure remote directory exists
    run_ssh(cfg, f"mkdir -p {shlex.quote(work_dir)}", timeout=10)

    # Build rsync command
    sync_cfg = cfg.get("sync", {})
    includes = sync_cfg.get("include", DEFAULT_SYNC_INCLUDE)
    excludes = sync_cfg.get("exclude", DEFAULT_SYNC_EXCLUDE)

    transport = build_ssh_transport(cfg)
    cmd = ["rsync", "-avz", "--delete", "-e", transport]

    # rsync evaluates filters top-to-bottom, first match wins. Excludes for
    # directories like .venv/ must precede the include rules — otherwise
    # --include=*/ (and --include=*.py) match first, rsync descends into them
    # and --delete clobbers remote files that live there. See issue #65.
    for pat in excludes:
        cmd += [f"--exclude={pat}"]
    # Recurse into remaining directories, then keep only wanted file patterns
    cmd += ["--include=*/"]
    for pat in includes:
        cmd += [f"--include={pat}"]
    cmd += ["--exclude=*"]

    if args.dry_run:
        cmd.append("--dry-run")

    # Source must end with / for rsync to sync contents
    src = local_path.rstrip("/") + "/"
    dst = f"{cfg['user']}@{cfg['host']}:{work_dir}/"
    cmd += [src, dst]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            _error(f"rsync failed: {proc.stderr.strip()}")

        # Count transferred files from rsync output
        lines = proc.stdout.strip().splitlines()
        # Files are listed before the summary; rough count
        file_count = sum(1 for l in lines if not l.startswith("sending") and
                         not l.startswith("sent ") and
                         not l.startswith("total ") and
                         not l.startswith("building ") and
                         not l.endswith("/") and l.strip())
        _ok({
            "host": cfg["host"],
            "remote_path": work_dir,
            "dry_run": args.dry_run,
            "files_transferred": file_count,
        })
    except subprocess.TimeoutExpired:
        _error("rsync timed out after 120s")
    except FileNotFoundError:
        _error("rsync command not found")


def cmd_setup_env(cfg: dict, args: argparse.Namespace) -> None:
    """Install Python dependencies on remote server."""
    req_file = args.requirements or "requirements.txt"
    if not Path(req_file).exists():
        _error(f"Requirements file not found locally: {req_file}")

    work_dir = cfg["work_dir"]

    # scp requirements file to remote
    transport_parts = ["scp"]
    port = cfg.get("port", 22)
    if port != 22:
        transport_parts += ["-P", str(port)]
    identity = cfg.get("identity_file", "")
    if identity:
        transport_parts += ["-i", os.path.expanduser(identity)]
    proxy = cfg.get("proxy_jump", "")
    if proxy:
        transport_parts += ["-o", f"ProxyJump={proxy}"]
    transport_parts += ["-o", "BatchMode=yes"]
    transport_parts += [req_file, f"{cfg['user']}@{cfg['host']}:{work_dir}/"]

    proc = subprocess.run(transport_parts, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        _error(f"scp failed: {proc.stderr.strip()}")

    # Install via pip
    prefix = conda_prefix(cfg)
    q_work_dir = shlex.quote(work_dir)
    install_cmd = f"cd {q_work_dir} && {prefix} && pip install -q -r {q_work_dir}/requirements.txt"
    rc, stdout, stderr = run_ssh(cfg, install_cmd, timeout=300)
    if rc != 0:
        _error(f"pip install failed: {stderr.strip()}")

    # Count installed packages from pip output
    out_lines = stdout.strip().splitlines() if stdout.strip() else []
    _ok({
        "host": cfg["host"],
        "requirements": req_file,
        "pip_output_tail": out_lines[-10:] if out_lines else ["(no output)"],
    })


def _validate_name(name: str) -> str:
    """Validate a screen session name (alphanumeric, hyphens, underscores)."""
    if not re.match(r'^[A-Za-z0-9_-]+$', name):
        _error(f"Invalid session name '{name}': only alphanumeric, hyphens, underscores allowed")
    return name


def cmd_launch(cfg: dict, args: argparse.Namespace) -> None:
    """Launch a screen session on the remote server."""
    session_name = _validate_name(args.name)
    user_cmd = args.cmd
    work_dir = cfg["work_dir"]
    q_work_dir = shlex.quote(work_dir)

    # Check if session already exists
    rc, stdout, _ = run_ssh(cfg, "screen -ls", timeout=10)
    if session_name in (stdout or ""):
        _error(f"Screen session '{session_name}' already exists on {cfg['host']}")

    # Build log file path
    log_file = args.log_file or f"logs/{session_name}.log"
    log_dir = os.path.dirname(log_file) if "/" in log_file else "logs"

    # Ensure log directory exists on remote
    run_ssh(cfg, f"mkdir -p {q_work_dir}/{shlex.quote(log_dir)}", timeout=10)

    # Build the full remote command
    prefix = conda_prefix(cfg)
    gpu_part = ""
    if args.gpu is not None:
        # Validate GPU index (digits and commas only)
        if not re.match(r'^[0-9,]+$', str(args.gpu)):
            _error(f"Invalid GPU index: {args.gpu}")
        gpu_part = f"CUDA_VISIBLE_DEVICES={args.gpu} "

    # Construct the screen command
    q_log_file = shlex.quote(log_file)
    inner_cmd = f"cd {q_work_dir}"
    if prefix:
        inner_cmd += f" && {prefix}"
    inner_cmd += f" && {gpu_part}{shlex.quote(user_cmd)} 2>&1 | tee {q_log_file}"

    # Escape for SSH + screen
    escaped_inner = inner_cmd.replace("'", "'\\''")
    screen_cmd = f"screen -dmS {session_name} bash -c '{escaped_inner}'"
    rc, stdout, stderr = run_ssh(cfg, screen_cmd, timeout=15)
    if rc != 0:
        _error(f"Failed to launch screen session: {stderr.strip()}")

    # Verify launch
    rc, stdout, _ = run_ssh(cfg, "screen -ls", timeout=10)
    verified = session_name in (stdout or "")

    _ok({
        "host": cfg["host"],
        "session": session_name,
        "gpu": str(args.gpu) if args.gpu is not None else "all",
        "log_file": log_file,
        "remote_cmd": inner_cmd,
        "verified": verified,
    })


def cmd_check(cfg: dict, args: argparse.Namespace) -> None:
    """Check if a screen session is alive and detect anomalies."""
    session_name = _validate_name(args.name)
    work_dir = cfg["work_dir"]
    q_work_dir = shlex.quote(work_dir)

    # Check screen session
    rc, stdout, _ = run_ssh(cfg, "screen -ls", timeout=10)
    alive = session_name in (stdout or "")

    # Try to get last lines from log file
    log_file = f"logs/{session_name}.log"
    q_log_path = shlex.quote(f"{work_dir}/{log_file}")
    rc2, log_out, _ = run_ssh(
        cfg, f"tail -30 {q_log_path} 2>/dev/null", timeout=10
    )
    last_lines = log_out.strip().splitlines() if rc2 == 0 and log_out.strip() else []

    # Fallback: screen hardcopy
    if not last_lines:
        tmp_file = f"/tmp/screen_{session_name}.txt"
        run_ssh(cfg, f"screen -S {session_name} -X hardcopy {shlex.quote(tmp_file)}", timeout=5)
        rc3, hc_out, _ = run_ssh(cfg, f"tail -30 {shlex.quote(tmp_file)} 2>/dev/null", timeout=10)
        if rc3 == 0 and hc_out.strip():
            last_lines = hc_out.strip().splitlines()

    # Anomaly detection
    anomalies = detect_anomalies(last_lines)

    result: dict = {
        "host": cfg["host"],
        "session": session_name,
        "alive": alive,
        "last_lines": last_lines[-20:],
        "anomalies": anomalies,
        "log_file": log_file,
    }

    if not alive:
        if anomalies:
            result["exit_reason"] = "crashed"
        else:
            result["exit_reason"] = "completed"

    _ok(result)


MAX_TAIL_LINES = 10000


def cmd_tail_log(cfg: dict, args: argparse.Namespace) -> None:
    """Get recent log output from remote."""
    session_name = _validate_name(args.name)
    work_dir = cfg["work_dir"]
    lines = min(max(args.lines or 50, 1), MAX_TAIL_LINES)

    log_file = f"logs/{session_name}.log"
    q_log_path = shlex.quote(f"{work_dir}/{log_file}")
    rc, stdout, _ = run_ssh(
        cfg, f"tail -{lines} {q_log_path} 2>/dev/null", timeout=15
    )

    if rc == 0 and stdout.strip():
        log_lines = stdout.strip().splitlines()
        _ok({
            "host": cfg["host"],
            "session": session_name,
            "source": "log_file",
            "lines": log_lines,
            "line_count": len(log_lines),
        })

    # Fallback: screen hardcopy
    tmp_file = f"/tmp/screen_{session_name}.txt"
    run_ssh(cfg, f"screen -S {session_name} -X hardcopy {shlex.quote(tmp_file)}", timeout=5)
    rc2, hc_out, _ = run_ssh(
        cfg, f"cat {shlex.quote(tmp_file)} 2>/dev/null", timeout=10
    )
    if rc2 == 0 and hc_out.strip():
        log_lines = hc_out.strip().splitlines()[-lines:]
        _ok({
            "host": cfg["host"],
            "session": session_name,
            "source": "screen_hardcopy",
            "lines": log_lines,
            "line_count": len(log_lines),
        })

    _error(f"No log output found for session '{session_name}'")


def cmd_pull_results(cfg: dict, args: argparse.Namespace) -> None:
    """Download result files from remote server."""
    work_dir = cfg["work_dir"]
    remote_path = args.remote_path
    local_path = args.local_path

    # Reject path traversal attempts
    if ".." in remote_path.split("/"):
        _error("remote-path must not contain '..' components")

    # If remote_path is relative, prepend work_dir
    if not remote_path.startswith("/"):
        remote_path = f"{work_dir}/{remote_path}"

    # Ensure local directory exists
    Path(local_path).mkdir(parents=True, exist_ok=True)

    # Build rsync command
    transport = build_ssh_transport(cfg)
    cmd = ["rsync", "-avz", "-e", transport]

    # Default: exclude large model files
    for pat in PULL_DEFAULT_EXCLUDE:
        cmd += [f"--exclude={pat}"]

    src = f"{cfg['user']}@{cfg['host']}:{remote_path.rstrip('/')}/"
    dst = local_path.rstrip("/") + "/"
    cmd += [src, dst]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            _error(f"rsync pull failed: {proc.stderr.strip()}")

        lines = proc.stdout.strip().splitlines()
        file_count = sum(1 for l in lines if not l.startswith("receiving") and
                         not l.startswith("sent ") and
                         not l.startswith("total ") and
                         not l.endswith("/") and l.strip())
        _ok({
            "host": cfg["host"],
            "remote_path": remote_path,
            "local_path": local_path,
            "files_transferred": file_count,
        })
    except subprocess.TimeoutExpired:
        _error("rsync pull timed out after 300s")
    except FileNotFoundError:
        _error("rsync command not found")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remote GPU server operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config", default=None,
        help="Path to server.yaml (default: config/server.yaml)",
    )
    sub = parser.add_subparsers(dest="command")

    # status
    sub.add_parser("status", help="Server connectivity + GPU overview")

    # gpu-status
    sub.add_parser("gpu-status", help="Detailed GPU usage per card")

    # sync-code
    p_sync = sub.add_parser("sync-code", help="Sync project code to remote")
    p_sync.add_argument("--local-path", default=".", help="Local directory to sync")
    p_sync.add_argument("--dry-run", action="store_true", help="Show what would be synced")

    # setup-env
    p_env = sub.add_parser("setup-env", help="Install Python dependencies on remote")
    p_env.add_argument("--requirements", default=None, help="Requirements file (default: requirements.txt)")

    # launch
    p_launch = sub.add_parser("launch", help="Start screen session on remote")
    p_launch.add_argument("--name", required=True, help="Screen session name")
    p_launch.add_argument("--cmd", required=True, help="Command to run")
    p_launch.add_argument("--gpu", default=None, help="GPU index (e.g. 0 or 0,1)")
    p_launch.add_argument("--log-file", default=None, help="Log file path on remote")

    # check
    p_check = sub.add_parser("check", help="Check session alive + anomaly detection")
    p_check.add_argument("--name", required=True, help="Screen session name")

    # tail-log
    p_tail = sub.add_parser("tail-log", help="Get recent log output")
    p_tail.add_argument("--name", required=True, help="Screen session name")
    p_tail.add_argument("--lines", type=int, default=50, help="Number of lines (default: 50)")

    # pull-results
    p_pull = sub.add_parser("pull-results", help="Download result files from remote")
    p_pull.add_argument("--remote-path", required=True, help="Remote path (relative to work_dir or absolute)")
    p_pull.add_argument("--local-path", required=True, help="Local destination path")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cfg = load_config(args.config)

    dispatch = {
        "status": lambda: cmd_status(cfg),
        "gpu-status": lambda: cmd_gpu_status(cfg),
        "sync-code": lambda: cmd_sync_code(cfg, args),
        "setup-env": lambda: cmd_setup_env(cfg, args),
        "launch": lambda: cmd_launch(cfg, args),
        "check": lambda: cmd_check(cfg, args),
        "tail-log": lambda: cmd_tail_log(cfg, args),
        "pull-results": lambda: cmd_pull_results(cfg, args),
    }
    dispatch[args.command]()


if __name__ == "__main__":
    main()
