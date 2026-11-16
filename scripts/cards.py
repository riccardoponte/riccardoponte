#!/usr/bin/env python3
"""
cards.py - render GitHub stat, language bar, and repo cards as SVGs. Stdlib only.

    python scripts/cards.py --user riccardoponte --out assets
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

UA = {"User-Agent": "cards.py"}

THEMES = {
    "dark": {
        "bg": "#0C1322",
        "border": "#1E2D4A",
        "title": "#38BDF8",
        "text": "#CBD5E1",
        "muted": "#7C90B0",
        "value": "#E2ECF8",
        "accent": "#2DD4BF",
    },
    "light": {
        "bg": "#FFFFFF",
        "border": "#CBD7E1",
        "title": "#0369A1",
        "text": "#1E293B",
        "muted": "#64748B",
        "value": "#0F172A",
        "accent": "#0D9488",
    },
}

LANG_COLOR = {
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Kotlin": "#A97BFF",
    "C#": "#178600",
    "C++": "#f34b7d",
    "C": "#555555",
    "Java": "#b07219",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Shell": "#89e051",
    "PowerShell": "#012456",
    "Bicep": "#519ABA",
    "Dockerfile": "#384d54",
    "Batchfile": "#C1F12E",
}

FONT = "ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"

ICON_STAR = (
    "M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 "
    "2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 "
    "01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"
)
ICON_FORK = (
    "M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75v-.878a2.25 2.25 0 "
    "111.5 0v.878a2.25 2.25 0 01-2.25 2.25h-1.5v2.128a2.251 2.251 0 11-1.5 "
    "0V8.5h-1.5A2.25 2.25 0 013.5 6.25v-.878a2.25 2.25 0 111.5 0zM5 3.25a.75.75 0 "
    "10-1.5 0 .75.75 0 001.5 0zm6.75.75a.75.75 0 100-1.5.75.75 0 000 1.5zm-3 "
    "8.75a.75.75 0 100-1.5.75.75 0 000 1.5z"
)
ICON_REPO = (
    "M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 "
    "0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 "
    "012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 "
    "12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 "
    "00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z"
)


def icon(path, x, y, size, fill):
    s = size / 16
    return (
        f'<path transform="translate({x:.1f},{y:.1f}) scale({s:.3f})" '
        f'fill="{fill}" d="{path}"/>'
    )


def rest(path: str, token: str | None):
    req = urllib.request.Request("https://api.github.com" + path, headers=dict(UA))
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def rest_url(url: str, token: str | None):
    req = urllib.request.Request(url, headers=dict(UA))
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def graphql(query: str, variables: dict, token: str):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={**UA, "Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


CONTRIB_QUERY = """
query($login:String!){
  user(login:$login){
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount } }
      }
    }
  }
}
"""


def fetch_contributions(user: str, token: str | None):
    if not token:
        return None
    try:
        data = graphql(CONTRIB_QUERY, {"login": user}, token)
    except urllib.error.HTTPError as e:
        print(f"  contributions unavailable (HTTP {e.code})", file=sys.stderr)
        return None
    if data.get("errors"):
        print(f"  contributions unavailable: {data['errors'][0].get('message')}", file=sys.stderr)
        return None

    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [
        (dt.date.fromisoformat(d["date"]), d["contributionCount"])
        for w in cal["weeks"]
        for d in w["contributionDays"]
    ]
    days.sort()

    longest = run = 0
    for _, c in days:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)

    current = 0
    for date, c in reversed(days):
        if c > 0:
            current += 1
        elif date != days[-1][0]:
            break
    return cal["totalContributions"], current, longest


def esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def text_width(s: str, size: float) -> float:
    return len(s) * size * 0.53


def wrap(text: str, size: float, max_w: float, max_lines: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if text_width(trial, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and words:
        used = len(" ".join(lines).split())
        if used < len(words):
            while lines and text_width(lines[-1] + "…", size) > max_w:
                lines[-1] = lines[-1].rsplit(" ", 1)[0]
            lines[-1] += "…"
    return lines


def frame(w, h, c, body, label):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-label="{esc(label)}" '
        f'font-family="{FONT}">'
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" '
        f'fill="{c["bg"]}" stroke="{c["border"]}"/>'
        f"{body}</svg>"
    )


def render_stats(user, stats, theme):
    c = THEMES[theme]
    pad = 22
    tiles = [(v, k) for k, v in stats]
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    rh, W = 46, 480
    H = pad + 52 + (rows - 1) * rh + 17 + pad
    tw = (W - 2 * pad) / cols

    out = [
        f'<text x="{pad}" y="{pad + 14}" font-size="15" font-weight="700" '
        f'fill="{c["title"]}">@{esc(user)}</text>',
        f'<text x="{W - pad}" y="{pad + 14}" font-size="11" text-anchor="end" '
        f'fill="{c["muted"]}">at a glance</text>',
        f'<line x1="{pad}" y1="{pad + 26}" x2="{W - pad}" y2="{pad + 26}" '
        f'stroke="{c["border"]}"/>',
    ]
    top = pad + 52
    for i, (value, label) in enumerate(tiles):
        cx = pad + (i % cols) * tw
        cy = top + (i // cols) * rh
        out.append(
            f'<text x="{cx:.0f}" y="{cy:.0f}" font-size="23" font-weight="700" '
            f'fill="{c["value"]}">{esc(value)}</text>'
        )
        out.append(
            f'<text x="{cx:.0f}" y="{cy + 17:.0f}" font-size="10.5" '
            f'fill="{c["muted"]}">{esc(label)}</text>'
        )
    return frame(W, H, c, "".join(out), f"{user} GitHub statistics")


def render_languages(user, langs: list[tuple[str, int]], theme: str):
    """Render a clean most-used languages bar card (dark & light)."""
    c = THEMES[theme]
    W, H = 480, 152
    pad = 22
    total = sum(b for _, b in langs) or 1

    out = [
        f'<text x="{pad}" y="{pad + 14}" font-size="14" font-weight="700" '
        f'fill="{c["title"]}">Most Used Languages</text>',
        f'<text x="{W - pad}" y="{pad + 14}" font-size="11" text-anchor="end" '
        f'fill="{c["muted"]}">code breakdown</text>',
    ]

    bar_x = pad
    bar_y = pad + 28
    bar_w = W - 2 * pad
    bar_h = 10
    clip_id = f"langbar-{theme}"
    out.append(
        f'<defs><clipPath id="{clip_id}"><rect x="{bar_x}" y="{bar_y}" '
        f'width="{bar_w}" height="{bar_h}" rx="5"/></clipPath></defs>'
    )
    out.append(f'<g clip-path="url(#{clip_id})">')
    cur_x = float(bar_x)
    for name, count in langs:
        seg_w = max(2.0, bar_w * (count / total))
        col = LANG_COLOR.get(name, c["accent"])
        out.append(
            f'<rect x="{cur_x:.1f}" y="{bar_y}" width="{seg_w + 0.5:.1f}" '
            f'height="{bar_h}" fill="{col}"/>'
        )
        cur_x += seg_w
    out.append("</g>")

    cols = 2
    col_w = (W - 2 * pad) / cols
    start_y = bar_y + 30
    for idx, (name, count) in enumerate(langs[:6]):
        col_i = idx % cols
        row_i = idx // cols
        lx = pad + col_i * col_w
        ly = start_y + row_i * 22
        pct = 100.0 * count / total
        col = LANG_COLOR.get(name, c["accent"])
        out.append(f'<circle cx="{lx + 5:.1f}" cy="{ly - 4:.1f}" r="4.5" fill="{col}"/>')
        out.append(
            f'<text x="{lx + 15:.1f}" y="{ly:.1f}" font-size="11.5" font-weight="600" '
            f'fill="{c["text"]}">{esc(name)}</text>'
        )
        out.append(
            f'<text x="{lx + col_w - 14:.1f}" y="{ly:.1f}" text-anchor="end" '
            f'font-size="11" fill="{c["muted"]}">{pct:.1f}%</text>'
        )
    return frame(W, H, c, "".join(out), f"{user} most used languages")


def render_repo(repo, theme):
    c = THEMES[theme]
    W, H = 420, 140
    pad = 18
    out = []

    out.append(icon(ICON_REPO, pad, pad, 15, c["muted"]))
    out.append(
        f'<text x="{pad + 22}" y="{pad + 12}" font-size="14" font-weight="700" '
        f'fill="{c["title"]}">{esc(repo["name"])}</text>'
    )

    desc = repo.get("description") or "No description yet."
    for i, line in enumerate(wrap(desc, 11.5, W - 2 * pad, 3)):
        out.append(
            f'<text x="{pad}" y="{pad + 37 + i * 16}" font-size="11.5" '
            f'fill="{c["text"]}">{esc(line)}</text>'
        )

    fy = H - pad - 2
    x = pad
    if repo.get("language"):
        col = LANG_COLOR.get(repo["language"], c["muted"])
        out.append(f'<circle cx="{x + 5}" cy="{fy - 4}" r="5" fill="{col}"/>')
        out.append(
            f'<text x="{x + 15}" y="{fy}" font-size="11" fill="{c["muted"]}">'
            f'{esc(repo["language"])}</text>'
        )
        x += 15 + text_width(repo["language"], 11) + 18

    for path, count in ((ICON_STAR, repo.get("stars", 0)), (ICON_FORK, repo.get("forks", 0))):
        out.append(icon(path, x, fy - 11, 12, c["muted"]))
        out.append(
            f'<text x="{x + 17}" y="{fy}" font-size="11" fill="{c["muted"]}">'
            f'{count}</text>'
        )
        x += 17 + text_width(str(count), 11) + 18

    return frame(W, H, c, "".join(out), f'{repo["name"]} repository card')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--user", required=True)
    p.add_argument("--out", type=Path, default=Path("assets"))
    p.add_argument("--projects", type=Path, default=Path("assets/projects.json"))
    args = p.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    args.out.mkdir(parents=True, exist_ok=True)

    user = rest(f"/users/{args.user}", token)
    repos = []
    page = 1
    while True:
        batch = rest(f"/users/{args.user}/repos?per_page=100&page={page}&type=owner", token)
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    owned = [r for r in repos if not r["fork"] and r["name"].lower() != args.user.lower()]
    stars = sum(r["stargazers_count"] for r in owned)

    tiles = [
        ("Total stars", f"{stars:,}"),
        ("Public repos", f"{user['public_repos']:,}"),
        ("Followers", f"{user['followers']:,}"),
    ]

    contrib = fetch_contributions(args.user, token)
    if contrib:
        total, current, longest = contrib
        tiles += [
            ("Contributions (1y)", f"{total:,}"),
            ("Current streak", f"{current:,}d"),
            ("Longest streak", f"{longest:,}d"),
        ]
    else:
        print("  note: no usable token, skipping contribution tiles", file=sys.stderr)

    for theme in ("dark", "light"):
        dest = args.out / f"card-stats-{theme}.svg"
        dest.write_text(render_stats(args.user, tiles, theme), encoding="utf-8")
    print(f"wrote card-stats-*.svg  ({len(tiles)} tiles)")

    # Aggregate real coding languages (excluding large bundled HTML/vendor assets).
    lang_totals: dict[str, int] = {}
    skip_langs = {"html", "tcl", "xslt", "go template", "smarty", "batchfile"}
    for r in owned:
        try:
            langs = rest_url(r["languages_url"], token)
        except urllib.error.HTTPError:
            continue
        for lname, bcount in langs.items():
            if lname.lower() in skip_langs:
                continue
            # Cap MarkItDown-Converter bundled asset skew if needed
            lang_totals[lname] = lang_totals.get(lname, 0) + bcount
    top_langs = sorted(lang_totals.items(), key=lambda kv: -kv[1])[:6]
    if top_langs:
        for theme in ("dark", "light"):
            dest = args.out / f"metrics-languages-{theme}.svg"
            dest.write_text(render_languages(args.user, top_langs, theme), encoding="utf-8")
        print(f"wrote metrics-languages-*.svg  ({len(top_langs)} languages)")

    if not args.projects.exists():
        print(f"no {args.projects}, skipping repo cards")
        return
    wanted = json.loads(args.projects.read_text(encoding="utf-8"))["projects"]
    by_name = {r["name"].lower(): r for r in repos}

    for entry in wanted:
        src = by_name.get(entry["repo"].lower())
        if not src:
            print(f"  !! {entry['repo']} not found on the account, skipped")
            continue
        card = {
            "name": src["name"],
            "description": entry.get("description") or src.get("description"),
            "language": entry.get("language") or src.get("language"),
            "stars": src["stargazers_count"],
            "forks": src["forks_count"],
        }
        for theme in ("dark", "light"):
            dest = args.out / f"card-{src['name']}-{theme}.svg"
            dest.write_text(render_repo(card, theme), encoding="utf-8")
        print(f"wrote card-{src['name']}-*.svg  ({card['stars']}star {card['forks']}fork {card['language']})")


if __name__ == "__main__":
    main()
