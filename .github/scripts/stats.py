#!/usr/bin/env python3
"""Generate stats/overview.svg and stats/top-langs.svg (standard library only)."""
import json, os, urllib.request
from datetime import datetime, timezone
from html import escape

USER = os.environ.get("STATS_USER", "Mik-TF")
TOKEN = os.environ["GH_TOKEN"]
BG, TITLE, TEXT, ICON = "#1a1b27", "#70a5fd", "#38bdae", "#bf91f3"
FONT = "'Segoe UI', Ubuntu, Sans-Serif"

def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.load(r)
    if "errors" in out:
        raise SystemExit("GraphQL error: " + json.dumps(out["errors"])[:300])
    return out["data"]["user"]

Q = """
query($login:String!, $since:DateTime!, $after:String) {
  user(login:$login) {
    name
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(first:1, contributionTypes:[COMMIT,ISSUE,PULL_REQUEST,REPOSITORY]) { totalCount }
    contributionsCollection(from:$since) { totalCommitContributions restrictedContributionsCount }
    repositories(first:100, after:$after, ownerAffiliations:OWNER, isFork:false) {
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount
        languages(first:10, orderBy:{field:SIZE, direction:DESC}) { edges { size node { name color } } } }
    }
  }
}"""

year = datetime.now(timezone.utc)
since = year.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
stars, langs, after, first = 0, {}, None, None
while True:
    u = gql(Q, {"login": USER, "since": since, "after": after})
    first = first or u
    for n in u["repositories"]["nodes"]:
        stars += n["stargazerCount"]
        for e in n["languages"]["edges"]:
            d = langs.setdefault(e["node"]["name"], [0, e["node"]["color"] or "#888888"])
            d[0] += e["size"]
    pi = u["repositories"]["pageInfo"]
    if not pi["hasNextPage"]:
        break
    after = pi["endCursor"]

cc = first["contributionsCollection"]
commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
rows = [
    ("Total Stars Earned", stars, "M8 .25a.75.75 0 0 1 .67.42l1.88 3.81 4.2.61a.75.75 0 0 1 .42 1.28l-3.04 2.96.72 4.18a.75.75 0 0 1-1.09.79L8 12.3l-3.76 1.98a.75.75 0 0 1-1.09-.79l.72-4.18L.83 6.37a.75.75 0 0 1 .42-1.28l4.2-.61L7.33.67A.75.75 0 0 1 8 .25z"),
    (f"Commits ({year.year})", commits, "M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5zM8 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"),
    ("Total PRs", first["pullRequests"]["totalCount"], "M1.5 3.25a2.25 2.25 0 1 1 3 2.12v5.26a2.25 2.25 0 1 1-1.5 0V5.37A2.25 2.25 0 0 1 1.5 3.25zm7.28-1.03L9.5 2.94V2h1.5v4h-4V4.5h1.19L7.97 3.28zM12.5 10.63V6.5H14v4.13a2.25 2.25 0 1 1-1.5 0z"),
    ("Total Issues", first["issues"]["totalCount"], "M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0zM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0z"),
    ("Contributed to", first["repositoriesContributedTo"]["totalCount"], "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.71 1.7.75.75 0 0 1-1.06 1.06A2.5 2.5 0 0 1 2 11.5v-9zm10.5-1h-8a1 1 0 0 0-1 1v6.7A2.5 2.5 0 0 1 4.5 9h8v-7.5z"),
]

def svg(w, h, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">\n'
            f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="4.5" fill="{BG}" stroke="#e4e2e2" stroke-opacity="0.2"/>\n'
            f'<text x="25" y="35" font-family="{FONT}" font-size="18" font-weight="600" fill="{TITLE}">{escape(title)}</text>\n{body}</svg>\n')

body = ""
for i, (label, val, path) in enumerate(rows):
    y = 60 + i * 25
    body += (f'<g transform="translate(25,{y})"><path fill="{ICON}" transform="translate(0,-1)" d="{path}"/>'
             f'<text x="25" y="12" font-family="{FONT}" font-size="14" font-weight="600" fill="{TEXT}">{escape(label)}:</text>'
             f'<text x="230" y="12" font-family="{FONT}" font-size="14" font-weight="700" fill="{TEXT}">{val:,}</text></g>\n')
os.makedirs("stats", exist_ok=True)
open("stats/overview.svg", "w").write(svg(495, 195, f"{first['name'] or USER}'s GitHub Stats", body))

top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:5]
total = sum(v[0] for _, v in top) or 1
body = ""
for i, (name, (size, color)) in enumerate(top):
    y = 55 + i * 20
    pct = 100 * size / total
    body += (f'<g transform="translate(25,{y})">'
             f'<text x="0" y="10" font-family="{FONT}" font-size="12" font-weight="600" fill="{TEXT}">{escape(name)}</text>'
             f'<text x="250" y="10" text-anchor="end" font-family="{FONT}" font-size="12" fill="{TEXT}">{pct:.1f}%</text>'
             f'<rect x="0" y="14" width="250" height="4" rx="2" fill="#ffffff" fill-opacity="0.1"/>'
             f'<rect x="0" y="14" width="{max(250*pct/100,3):.1f}" height="4" rx="2" fill="{escape(color)}"/></g>\n')
open("stats/top-langs.svg", "w").write(svg(300, 165 + 15, "Most Used Languages", body))
print("stars", stars, "commits", commits, "langs", [(n, round(100*v[0]/total, 1)) for n, v in top])
