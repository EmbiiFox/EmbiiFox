"""Render pink/black GitHub stat cards into assets/ (stdlib only).
Run in GitHub Actions with GITHUB_TOKEN set, or with --mock for a local preview."""
import json, os, sys, urllib.request, datetime
from xml.sax.saxutils import escape as E

USER = os.environ.get("GH_USER", "EmbiiFox")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")
BG, PINK, PINK2, LIGHT, MUTED, LINE = "#000000", "#F48FB1", "#F06292", "#FCE4EC", "#C48B9F", "#3A0A1F"
FONT = "'Segoe UI', Helvetica, Arial, sans-serif"
SERIF = "Georgia, 'Times New Roman', serif"

Q = """query($login:String!){ user(login:$login){
  followers{totalCount}
  repositories(ownerAffiliations:OWNER, isFork:false, first:100, privacy:PUBLIC){
    totalCount
    nodes{ stargazerCount languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name color } } } } }
  contributionsCollection{
    totalCommitContributions totalPullRequestContributions totalIssueContributions totalPullRequestReviewContributions
    contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } } } } }"""

def fetch():
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": Q, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    if "errors" in data: raise SystemExit(data["errors"])
    return data["data"]["user"]

def mock():
    import random; r = random.Random(1); today = datetime.date.today()
    days = [{"date": (today - datetime.timedelta(days=i)).isoformat(), "contributionCount": r.choice([0,0,1,2,3,5,8])} for i in range(370)][::-1]
    return {"followers": {"totalCount": 12}, "repositories": {"totalCount": 18, "nodes": [
        {"stargazerCount": 3, "languages": {"edges": [{"size": 50000, "node": {"name": "C#", "color": "#178600"}},
         {"size": 30000, "node": {"name": "TypeScript", "color": "#3178c6"}}, {"size": 12000, "node": {"name": "HTML", "color": "#e34c26"}},
         {"size": 8000, "node": {"name": "SCSS", "color": "#c6538c"}}, {"size": 5000, "node": {"name": "JavaScript", "color": "#f1e05a"}},
         {"size": 3000, "node": {"name": "Python", "color": "#3572A5"}}]}}]},
        "contributionsCollection": {"totalCommitContributions": 120, "totalPullRequestContributions": 14, "totalIssueContributions": 4,
         "totalPullRequestReviewContributions": 9, "contributionCalendar": {"totalContributions": 167, "weeks": [{"contributionDays": days}]}}}

def frame(w, h, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="14" fill="{BG}" stroke="{LINE}"/>'
            f'<text x="26" y="40" font-family="{SERIF}" font-size="21" fill="{PINK}">{E(title)}</text>'
            f'<rect x="26" y="52" width="{w-52}" height="1.2" fill="{LINE}"/>{body}</svg>')

def stats_card(u):
    c = u["contributionsCollection"]
    stars = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
    rows = [("Total contributions (1y)", c["contributionCalendar"]["totalContributions"]),
            ("Commits (1y)", c["totalCommitContributions"]), ("Pull requests (1y)", c["totalPullRequestContributions"]),
            ("Code reviews (1y)", c["totalPullRequestReviewContributions"]), ("Issues (1y)", c["totalIssueContributions"]),
            ("Public repos · Stars", f'{u["repositories"]["totalCount"]} · {stars}')]
    body = ""
    for i, (k, v) in enumerate(rows):
        y = 84 + i * 26
        body += (f'<circle cx="34" cy="{y-5}" r="4" fill="{PINK2}"/>'
                 f'<text x="48" y="{y}" font-family="{FONT}" font-size="14" fill="{LIGHT}">{E(k)}</text>'
                 f'<text x="454" y="{y}" font-family="{FONT}" font-size="14" font-weight="bold" fill="{PINK}" text-anchor="end">{E(str(v))}</text>')
    return frame(480, 240, "GitHub Stats", body)

def langs_card(u):
    tot = {}
    for n in u["repositories"]["nodes"]:
        for e in n["languages"]["edges"]:
            nm = e["node"]["name"]; tot.setdefault(nm, [0, e["node"]["color"] or MUTED]); tot[nm][0] += e["size"]
    top = sorted(tot.items(), key=lambda kv: -kv[1][0])[:6]
    s = sum(v[0] for _, v in top) or 1
    body, x = '<clipPath id="bar"><rect x="26" y="72" width="428" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">', 26.0
    for nm, (sz, col) in top:
        w = 428 * sz / s; body += f'<rect x="{x:.1f}" y="72" width="{w+.5:.1f}" height="10" fill="{col}"/>'; x += w
    body += "</g>"
    for i, (nm, (sz, col)) in enumerate(top):
        cx, cy = 34 + (i % 2) * 220, 118 + (i // 2) * 34
        body += (f'<circle cx="{cx}" cy="{cy-5}" r="6" fill="{col}"/>'
                 f'<text x="{cx+14}" y="{cy}" font-family="{FONT}" font-size="14" fill="{LIGHT}">{E(nm)} '
                 f'<tspan fill="{MUTED}">{100*sz/s:.1f}%</tspan></text>')
    if not top:
        body += f'<text x="240" y="140" font-family="{FONT}" font-size="14" fill="{MUTED}" text-anchor="middle">No public code yet</text>'
    return frame(480, 240, "Most Used Languages", body)

def activity_card(u):
    weeks = u["contributionsCollection"]["contributionCalendar"]["weeks"][-52:]
    days = [{"date": w["contributionDays"][0]["date"], "contributionCount": sum(d["contributionCount"] for d in w["contributionDays"])} for w in weeks if w["contributionDays"]]
    W, H, L, R, T, B = 1000, 300, 60, 30, 70, 50
    vals = [d["contributionCount"] for d in days]; mx = max(vals + [4])
    pw, ph = W - L - R, H - T - B
    pts = [(L + i * pw / max(len(vals) - 1, 1), T + ph - v / mx * ph) for i, v in enumerate(vals)]
    grid = ""
    for k in range(5):
        y = T + ph * k / 4; val = round(mx * (4 - k) / 4)
        grid += (f'<line x1="{L}" y1="{y:.0f}" x2="{W-R}" y2="{y:.0f}" stroke="{LINE}" stroke-dasharray="3 5"/>'
                 f'<text x="{L-12}" y="{y+4:.0f}" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="end">{val}</text>')
    for i, d in enumerate(days):
        if i % 6 == 0 or i == len(days) - 1:
            dt = datetime.date.fromisoformat(d["date"])
            grid += f'<text x="{pts[i][0]:.0f}" y="{H-B+22}" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="middle">{dt.strftime("%b %y")}</text>'
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{L},{T+ph} " + line + f" {W-R},{T+ph}"
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.8" fill="{LIGHT}" stroke="{PINK2}" stroke-width="1.5"/>' for x, y in pts)
    body = (f'<defs><linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PINK2}" stop-opacity=".55"/>'
            f'<stop offset="1" stop-color="#880E4F" stop-opacity="0"/></linearGradient></defs>{grid}'
            f'<polygon points="{area}" fill="url(#ar)"/><polyline points="{line}" fill="none" stroke="{PINK2}" stroke-width="2.5" stroke-linejoin="round"/>{dots}'
            f'<text x="{W-26}" y="40" font-family="{FONT}" font-size="13" fill="{MUTED}" text-anchor="end">last 12 months · weekly · {sum(vals)} public contributions</text>')
    return frame(W, H, "Contribution Graph", body)

if __name__ == "__main__":
    u = mock() if "--mock" in sys.argv else fetch()
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("stats", stats_card), ("langs", langs_card), ("activity", activity_card)]:
        with open(os.path.join(OUT, f"card-{name}.svg"), "w", encoding="utf-8") as fh: fh.write(fn(u))
    print("cards written")
