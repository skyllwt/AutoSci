#!/usr/bin/env python3
"""Send a plain-text e-mail from GitHub Actions via SMTP."""

from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path


class ConfigError(ValueError):
    """Raised when required SMTP configuration is missing or invalid."""


def _split_recipients(raw: str) -> list[str]:
    return [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _load_config(args: argparse.Namespace) -> dict:
    host = os.environ.get("SMTP_HOST", "").strip()
    raw_port = os.environ.get("SMTP_PORT", "").strip() or "587"
    username = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    from_addr = (args.from_addr or os.environ.get("SMTP_FROM") or "").strip()
    to_addrs = _split_recipients(args.to or os.environ.get("DAILY_ARXIV_EMAIL_TO", ""))

    missing: list[str] = []
    for name, value in (
        ("SMTP_HOST", host),
        ("SMTP_USER", username),
        ("SMTP_PASSWORD", password),
        ("SMTP_FROM", from_addr),
        ("DAILY_ARXIV_EMAIL_TO", ",".join(to_addrs)),
    ):
        if not value:
            missing.append(name)
    if missing:
        raise ConfigError(
            "Missing SMTP configuration: "
            + ", ".join(missing)
            + ". Set these as GitHub Actions secrets or environment variables."
        )

    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ConfigError("SMTP_PORT must be an integer") from exc

    use_ssl = _bool_env("SMTP_SSL", port == 465)
    use_starttls = _bool_env("SMTP_STARTTLS", not use_ssl)

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "from_addr": from_addr,
        "to_addrs": to_addrs,
        "use_ssl": use_ssl,
        "use_starttls": use_starttls,
    }


def _build_message(args: argparse.Namespace, config: dict) -> EmailMessage:
    if not args.subject:
        raise ConfigError("--subject is required when sending mail")
    if not args.body_file:
        raise ConfigError("--body-file is required when sending mail")

    body = args.body_file.read_text(encoding="utf-8")
    msg = EmailMessage()
    msg["Subject"] = args.subject
    msg["From"] = config["from_addr"]
    msg["To"] = ", ".join(config["to_addrs"])
    msg.set_content(body)
    return msg


def send_message(args: argparse.Namespace) -> None:
    config = _load_config(args)
    if args.check_config:
        print(
            "SMTP configuration OK "
            f"({config['host']}:{config['port']} -> {len(config['to_addrs'])} recipient(s))"
        )
        return

    msg = _build_message(args, config)
    context = ssl.create_default_context()

    if config["use_ssl"]:
        with smtplib.SMTP_SSL(config["host"], config["port"], context=context, timeout=30) as smtp:
            smtp.login(config["username"], config["password"])
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(config["host"], config["port"], timeout=30) as smtp:
            smtp.ehlo()
            if config["use_starttls"]:
                smtp.starttls(context=context)
                smtp.ehlo()
            smtp.login(config["username"], config["password"])
            smtp.send_message(msg)

    print(f"Sent e-mail to {len(config['to_addrs'])} recipient(s)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a Markdown digest via SMTP")
    parser.add_argument("--subject", help="E-mail subject")
    parser.add_argument("--body-file", type=Path, help="Plain-text Markdown body")
    parser.add_argument("--to", help="Comma-separated recipient override")
    parser.add_argument("--from", dest="from_addr", help="Sender override")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate SMTP environment variables without sending mail",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        send_message(args)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
