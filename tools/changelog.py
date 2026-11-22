"""Changelog rows from CodeRabbit's reviews: what it found that we missed, and what we did.

    python tools/changelog.py 8 9 11        print a "Reviewed by CodeRabbit" table for these PRs

For every CodeRabbit inline comment on a PR it takes the severity and the one-line finding,
and the status from our reply in the thread:
  "Fixed in <sha>: ..."    -> Fixed (with the commit)
  "Deferred: ..." / "Won't fix: ..." -> as written, with the reason
  no reply                 -> Open
Paste the output into CHANGELOG.md under the release. Needs the GitHub CLI (gh), logged in.
"""
import json
import re
import subprocess
import sys

REPO = "joethesaint/savemylinks"
SEVERITY = re.compile(r"\*\*\s*(Critical|Major|Minor|Trivial|Nitpick)\s*\*\*", re.I)


def gh(path):
    out = subprocess.run(["gh", "api", "--paginate", path], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    # --paginate concatenates JSON arrays ("][") across pages
    return json.loads(re.sub(r"\]\s*\[", ",", out)) if out.strip().startswith("[") else json.loads(out)


def clean(body):
    body = re.sub(r"<details>.*?</details>", "", body, flags=re.S)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    return re.sub(r"<picture>.*?</picture>", "", body, flags=re.S)


def finding(body):
    """(severity, one-line finding) from a CodeRabbit comment."""
    body = clean(body)
    sev = SEVERITY.search(body)
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    title = next((l.strip("*").strip() for l in lines[1:] if l.startswith("**") and l.endswith("**")), lines[0] if lines else "")
    return (sev.group(1).title() if sev else "Note"), title.rstrip(".")


def status(reply):
    if reply is None:
        return "Open"
    m = re.match(r"\s*Fixed in ([0-9a-f]{7,40})", reply)
    if m:
        return f"Fixed in `{m.group(1)[:7]}`"
    m = re.match(r"\s*(Deferred|Won't fix|Not a bug)\b[:\s-]*(.*)", reply, re.I | re.S)
    if m:
        return f"{m.group(1).capitalize()}: {m.group(2).strip().splitlines()[0][:120]}"
    return "Answered (see thread)"


def rows(pr):
    comments = gh(f"repos/{REPO}/pulls/{pr}/comments")
    replies = {}
    for c in comments:
        if c.get("in_reply_to_id") and "coderabbit" not in c["user"]["login"]:
            replies.setdefault(c["in_reply_to_id"], c["body"])
    out = []
    for c in comments:
        if c.get("in_reply_to_id") or "coderabbit" not in c["user"]["login"]:
            continue
        sev, title = finding(c["body"])
        where = f"`{c['path']}`"
        out.append(f"| [#{pr}](https://github.com/{REPO}/pull/{pr}) | {title.replace('|', '/')} | {where} | {sev} | {status(replies.get(c['id']))} |")
    return out


def main(prs):
    print("| PR | What CodeRabbit found that we missed | Where | Severity | Status |")
    print("|---|---|---|---|---|")
    for pr in prs:
        r = rows(pr)
        print("\n".join(r) if r else f"| [#{pr}](https://github.com/{REPO}/pull/{pr}) | No findings | | | |")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
