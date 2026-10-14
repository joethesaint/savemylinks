---
name: agent-coexist
description: Use at the start of every session in a repo that several AI agents (Claude, Codex, Agy, Gemini, DeepSeek) work on at once, and before any git branch switch, commit, push, reset or deploy. Sets the rules that keep parallel sessions from overwriting each other.
---

# Agent coexistence

Several agent sessions work on this repo at the same time. Each one is
obedient to the same small system: one worktree per session, a claim on
every branch you write to, no history rewrites, and a written handoff.
The guard hook enforces the dangerous parts; this file explains the rest.

## 1. Start of session

1. Run `node .claude/hooks/coexist-guard.cjs status`. It lists live claims
   (who holds which branch, since when) and the worktrees on disk.
2. Read the newest handoff note (see section 6) before touching code.
3. Run `git fetch --all --prune`. Never trust a local branch tip you did
   not fetch this session; another agent may have pushed since.

## 2. One worktree per session

- The primary checkout belongs to the human. Do not switch its branch,
  stash its changes or delete its untracked files.
- Make your own worktree for each task:
  `git worktree add ../<repo>-<agent>-<topic> -b <agent>/<topic> <base>`
- Remove it when the work is merged: `git worktree remove <path>`.

## 3. Claim before you write

- `node .claude/hooks/coexist-guard.cjs claim <branch> "<what you are doing>"`
- A claim lasts 4 hours unless renewed. The guard blocks commits and pushes
  to a branch another live session holds.
- `release <branch>` when you finish or hand off.
- Shared branches (`main`, `staging`, `demo`, `production`) are never
  claimed long-term: claim, push, release.

## 4. History is append-only

Never, without the human saying so in this session:
- `push --force` / `-f` / `--force-with-lease`
- `reset --hard`, `checkout -- .`, `restore .`, `clean -f`
- `branch -D`, deleting a remote branch, `rebase` of a pushed branch
- `stash` in a worktree you did not create

To undo a commit, add a revert commit. To change a branch's base, make a new
branch. Before rolling anything back, create `backup/<branch>-<date>`.

## 5. Pushing to a shared branch

1. `git fetch <remote> <branch>`.
2. `git log --oneline HEAD..<remote>/<branch>`. If that prints anything,
   someone else pushed. Read those commits, then cherry-pick or merge them.
   Do not drop them.
3. Run the project's lint, tests and build.
4. Push without force. If the push is rejected, go back to step 1.
5. Never push to production branches without the human's confirmation.

## 6. Handoff note

After every push, and when you stop, append a short note to the shared
thread (for example `council-threads/<date>-<topic>.txt`):

```
<date time> <agent> on <branch> @ <short sha>
Did: <one line>
Left open: <one line or "nothing">
Do not touch: <files mid-edit, or "nothing">
--<Agent name>
```

## 7. When something is already broken

- Find the commit that broke it (`git log`, `git bisect`) and name it.
- Back up first, then fix forward on a new branch.
- Report what other agents did plainly, by commit, never by guess.

## 8. Commits

- One concern per commit. The message says what the user can now do.
- No AI attribution lines (`Co-Authored-By`, session links, "Generated with")
  unless the repo says otherwise; agents sign in chat, not in git.
- Never commit `.env`, secrets, or another agent's half-finished files.
