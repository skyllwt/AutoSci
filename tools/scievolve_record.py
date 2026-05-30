#!/usr/bin/env python3
"""Thin CLI wrapper around scievolve_record_signal() for skill bash blocks.

Usage:
    python3 tools/scievolve_record.py \
        --wiki-root wiki \
        --source {user|task|open} \
        --dimension {memory|workflow|orchestration} \
        --target <skill-or-entity> \
        --kind <kind> \
        --summary "<one-line>" \
        [--evidence-path <path>] \
        [--evidence-text "<quote>"] \
        [--severity {info|low|medium|high|critical}] \
        [--confidence {low|medium|high}]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scievolve import scievolve_record_signal


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record a SciEvolve signal (thin CLI wrapper)")
    parser.add_argument("--wiki-root", required=True)
    parser.add_argument("--source", required=True,
                        choices=("user", "task", "open"))
    parser.add_argument("--dimension", required=True,
                        choices=("memory", "workflow", "orchestration"))
    parser.add_argument("--target", default="",
                        help="Entity slug, skill name, DAG/template, or blank")
    parser.add_argument("--kind", required=True,
                        help="Signal kind, e.g. correction, failure, warning, success, cost, review, experiment, external-update")
    parser.add_argument("--summary", required=True,
                        help="Short human-readable signal summary")
    parser.add_argument("--evidence-path", default="")
    parser.add_argument("--evidence-text", default="")
    parser.add_argument("--severity", default="info",
                        choices=("info", "low", "medium", "high", "critical"))
    parser.add_argument("--confidence", default="medium",
                        choices=("low", "medium", "high"))

    args = parser.parse_args()

    scievolve_record_signal(
        wiki_root=args.wiki_root,
        source=args.source,
        dimension=args.dimension,
        target=args.target,
        kind=args.kind,
        summary=args.summary,
        evidence_path=args.evidence_path,
        evidence_text=args.evidence_text,
        confidence=args.confidence,
        severity=args.severity,
    )


if __name__ == "__main__":
    main()
