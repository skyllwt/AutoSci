#!/usr/bin/env python3
"""Fetch summary and section content from Wikipedia for /prefill.

Uses the MediaWiki action=parse API exclusively (the REST mobile-sections
endpoint is deprecated). All output is JSON on stdout.

Usage:
    python3 tools/fetch_wikipedia.py summary "Transformer (machine learning model)"
    python3 tools/fetch_wikipedia.py sections "Gradient descent"
    python3 tools/fetch_wikipedia.py section "Gradient descent" --index 3
    python3 tools/fetch_wikipedia.py wikitext "Backpropagation"

Exit codes:
    0  success
    2  page not found (HTTP 404 or API error indicating missing page)
    3  network or parse error
"""
from __future__ import annotations


import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://en.wikipedia.org/w/api.php"
REST_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"
USER_AGENT = "OmegaWiki-prefill/0.1 (https://github.com/skyllwt/OmegaWiki)"


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(json.dumps({"status": "not_found", "url": url}), file=sys.stderr)
            sys.exit(2)
        print(json.dumps({"status": "http_error", "code": e.code, "url": url}), file=sys.stderr)
        sys.exit(3)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(json.dumps({"status": "error", "message": str(e), "url": url}), file=sys.stderr)
        sys.exit(3)


def _api(params: dict) -> dict:
    params = {**params, "format": "json", "formatversion": "2"}
    url = f"{API}?{urllib.parse.urlencode(params)}"
    data = _get(url)
    if "error" in data:
        code = data["error"].get("code", "")
        if code in ("missingtitle", "invalidtitle"):
            print(json.dumps({"status": "not_found", "title": params.get("page", "")}),
                  file=sys.stderr)
            sys.exit(2)
        print(json.dumps({"status": "api_error", "error": data["error"]}), file=sys.stderr)
        sys.exit(3)
    return data


def fetch_summary(title: str) -> dict:
    encoded = urllib.parse.quote(title.replace(" ", "_"), safe="")
    return _get(REST_SUMMARY + encoded)


def fetch_sections(title: str) -> list[dict]:
    data = _api({"action": "parse", "page": title, "prop": "sections"})
    return data.get("parse", {}).get("sections", [])


def fetch_section(title: str, index: int) -> str:
    data = _api({"action": "parse", "page": title, "prop": "wikitext", "section": str(index)})
    wt = data.get("parse", {}).get("wikitext", "")
    if isinstance(wt, dict):
        return wt.get("*", "")
    return wt


def fetch_wikitext(title: str) -> str:
    data = _api({"action": "parse", "page": title, "prop": "wikitext"})
    wt = data.get("parse", {}).get("wikitext", "")
    if isinstance(wt, dict):
        return wt.get("*", "")
    return wt


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("summary", help="Fetch page summary (REST API)")
    s1.add_argument("title")

    s2 = sub.add_parser("sections", help="List section indexes")
    s2.add_argument("title")

    s3 = sub.add_parser("section", help="Fetch one section's wikitext")
    s3.add_argument("title")
    s3.add_argument("--index", type=int, required=True)

    s4 = sub.add_parser("wikitext", help="Fetch full page wikitext")
    s4.add_argument("title")

    args = p.parse_args()

    if args.cmd == "summary":
        out = fetch_summary(args.title)
        print(json.dumps({
            "title": out.get("title", args.title),
            "extract": out.get("extract", ""),
            "url": out.get("content_urls", {}).get("desktop", {}).get("page", ""),
        }, ensure_ascii=False))
    elif args.cmd == "sections":
        sections = fetch_sections(args.title)
        print(json.dumps([
            {"index": s.get("index"), "line": s.get("line"), "level": s.get("level")}
            for s in sections
        ], ensure_ascii=False))
    elif args.cmd == "section":
        print(json.dumps({"wikitext": fetch_section(args.title, args.index)}, ensure_ascii=False))
    elif args.cmd == "wikitext":
        print(json.dumps({"wikitext": fetch_wikitext(args.title)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
