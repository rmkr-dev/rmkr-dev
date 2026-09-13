#!/usr/bin/env python3
"""Build profile stats SVGs from the GitHub API (no third-party Vercel hosts)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

OWNER = os.environ.get("GITHUB_OWNER", "rmkr-dev")


def gh_json(args: list[str]):
    out = subprocess.check_output(["gh", "api"] + args, text=True)
    return json.loads(out)


def gh_json_paginate(path: str, jq: str | None = None):
    args = ["--paginate", path]
    if jq:
        args += ["--jq", jq]
    out = subprocess.check_output(["gh", "api"] + args, text=True)
    # --paginate may concatenate JSON arrays or newline objects
    text = out.strip()
    if not text:
        return []
    if text.startswith("["):
        # possible concatenated arrays
        items = []
        dec = json.JSONDecoder()
        idx = 0
        while idx < len(text):
            while idx < len(text) and text[idx].isspace():
                idx += 1
            if idx >= len(text):
                break
            obj, end = dec.raw_decode(text, idx)
            if isinstance(obj, list):
                items.extend(obj)
            else:
                items.append(obj)
            idx = end
        return items
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def card(title: str, rows: list[tuple[str, str]], width: int = 420, row_h: int = 28) -> str:
    height = 56 + len(rows) * row_h + 16
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        "<style>",
        "  .title { font: 600 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: #FFC300; }",
        "  .label { font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9; }",
        "  .value { font: 600 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #f0f6fc; }",
        "  .border { stroke: #30363d; fill: #0d1117; }",
        "</style>",
        f'<rect class="border" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8"/>',
        f'<text class="title" x="20" y="32">{escape(title)}</text>',
    ]
    y = 62
    for label, value in rows:
        lines.append(f'<text class="label" x="20" y="{y}">{escape(label)}</text>')
        lines.append(f'<text class="value" x="{width - 20}" y="{y}" text-anchor="end">{escape(value)}</text>')
        y += row_h
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def langs_card(langs: list[tuple[str, int]], width: int = 420) -> str:
    total = sum(n for _, n in langs) or 1
    colors = ["#FFC300", "#58a6ff", "#3fb950", "#f78166", "#d2a8ff", "#79c0ff", "#ffa198", "#7ee787"]
    bar_y = 52
    bar_h = 10
    height = 70 + len(langs) * 26 + 20
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        "<style>",
        "  .title { font: 600 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: #FFC300; }",
        "  .label { font: 400 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9; }",
        "  .pct { font: 600 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #f0f6fc; }",
        "  .border { stroke: #30363d; fill: #0d1117; }",
        "</style>",
        f'<rect class="border" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8"/>',
        f'<text class="title" x="20" y="32">Top Languages</text>',
        f'<rect x="20" y="{bar_y}" width="{width - 40}" height="{bar_h}" rx="5" fill="#21262d"/>',
    ]
    x = 20
    inner_w = width - 40
    for i, (name, n) in enumerate(langs):
        w = max(2, int(inner_w * (n / total)))
        color = colors[i % len(colors)]
        lines.append(f'<rect x="{x}" y="{bar_y}" width="{w}" height="{bar_h}" fill="{color}"/>')
        x += w
    y = bar_y + 36
    for i, (name, n) in enumerate(langs):
        pct = f"{(100.0 * n / total):.1f}%"
        color = colors[i % len(colors)]
        lines.append(f'<circle cx="28" cy="{y - 4}" r="5" fill="{color}"/>')
        lines.append(f'<text class="label" x="42" y="{y}">{escape(name)}</text>')
        lines.append(f'<text class="pct" x="{width - 20}" y="{y}" text-anchor="end">{pct}</text>')
        y += 26
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main() -> int:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out_dir.mkdir(parents=True, exist_ok=True)

    user = gh_json([f"users/{OWNER}"])
    repos = gh_json_paginate(f"users/{OWNER}/repos?per_page=100&type=owner&sort=updated")
    public = [r for r in repos if not r.get("private")]

    stars = sum(r.get("stargazers_count") or 0 for r in public)
    forks = sum(r.get("forks_count") or 0 for r in public)
    public_count = len(public)

    # Contributions this year via search (best-effort)
    try:
        prs = gh_json([f"search/issues?q=author:{OWNER}+type:pr&per_page=1"])
        pr_count = prs.get("total_count", 0)
    except Exception:
        pr_count = 0
    try:
        issues = gh_json([f"search/issues?q=author:{OWNER}+type:issue&per_page=1"])
        issue_count = issues.get("total_count", 0)
    except Exception:
        issue_count = 0

    stats_svg = card(
        f"@{OWNER} GitHub Stats",
        [
            ("Public repositories", str(public_count)),
            ("Stars earned", str(stars)),
            ("Forks earned", str(forks)),
            ("Public PRs authored", str(pr_count)),
            ("Public issues authored", str(issue_count)),
            ("Followers", str(user.get("followers") or 0)),
        ],
    )
    (out_dir / "github-stats.svg").write_text(stats_svg)

    lang_bytes: Counter[str] = Counter()
    for r in public:
        if r.get("fork"):
            continue
        name = r["name"]
        try:
            langs = gh_json([f"repos/{OWNER}/{name}/languages"])
        except Exception:
            continue
        for lang, n in langs.items():
            lang_bytes[lang] += int(n)

    top = lang_bytes.most_common(8)
    if not top:
        top = [("Unknown", 1)]
    (out_dir / "github-top-langs.svg").write_text(langs_card(top))

    # Lightweight streak substitute: recent public push activity count from events
    try:
        events = gh_json([f"users/{OWNER}/events/public?per_page=100"])
        pushes = sum(1 for e in events if e.get("type") == "PushEvent")
        creates = sum(1 for e in events if e.get("type") in ("CreateEvent", "PullRequestEvent"))
    except Exception:
        pushes, creates = 0, 0
    streak_svg = card(
        f"@{OWNER} Recent Activity",
        [
            ("Push events (last 100 public)", str(pushes)),
            ("PR / create events (last 100)", str(creates)),
            ("Account created", str(user.get("created_at", "")[:10] or "—")),
        ],
        width=420,
    )
    (out_dir / "github-streak.svg").write_text(streak_svg)
    print(f"Wrote SVGs to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
