#!/usr/bin/env node
// Agent coexistence guard. One file, three uses:
//   Claude Code PreToolUse hook  : node .claude/hooks/coexist-guard.cjs pretool
//   Claude Code SessionStart hook: node .claude/hooks/coexist-guard.cjs session
//   Any agent / human, by hand   : node .claude/hooks/coexist-guard.cjs status|claim|release
//   Git hooks (every agent, any tool): prepush <remote> | precommit | reftx
// Claims live in <git common dir>/agent-claims, shared by every worktree and never committed.
const { execSync } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const CLAIM_HOURS = 4
const PROTECTED = ['main', 'master', 'production', 'staging', 'demo']
// A claim belongs to a worktree (one worktree per session), labelled with AGENT_NAME if set.
const AGENT = process.env.AGENT_NAME || 'agent'
const holder = cwd => git('rev-parse --show-toplevel', cwd) || path.resolve(cwd || '.')

const git = (args, cwd) => {
  try { return execSync(`git ${args}`, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim() } catch { return '' }
}
const claimDir = cwd => {
  const common = git('rev-parse --git-common-dir', cwd)
  if (!common) return null
  const dir = path.resolve(cwd || process.cwd(), common, 'agent-claims')
  fs.mkdirSync(dir, { recursive: true })
  return dir
}
const safe = branch => branch.replace(/[^\w.-]/g, '_')
const liveClaims = cwd => {
  const dir = claimDir(cwd)
  if (!dir) return []
  return fs.readdirSync(dir).filter(f => f.endsWith('.json')).map(f => {
    try { return JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')) } catch { return null }
  }).filter(c => c && Date.now() - c.at < CLAIM_HOURS * 3600e3)
}
const heldByOther = (branch, cwd) => liveClaims(cwd).find(c => c.branch === branch && c.worktree !== holder(cwd))

// Each rule: pattern on the shell command, reason shown to the agent.
const RULES = [
  [/\bgit\s+push\b[^|;&]*(\s-f\b|--force\b|--force-with-lease|\s\+\S)/, 'Force push rewrites history other agents have pulled. Fetch, merge their commits, push without force.'],
  [/\bgit\s+reset\s+[^|;&]*--hard\b/, 'reset --hard throws away work. Make a backup/<branch>-<date> branch and revert or branch instead.'],
  [/\bgit\s+(checkout|restore)\s+[^|;&]*(\s--\s+\.|\s\.(\s|$))/, 'Discarding all working-tree changes can erase another agent\'s edits.'],
  [/\bgit\s+clean\s+[^|;&]*-\w*f/, 'git clean deletes untracked files that may belong to another session.'],
  [/\bgit\s+branch\s+[^|;&]*(-D\b|--delete\s+--force)/, 'Force-deleting a branch loses unmerged work.'],
  [/\bgit\s+push\s+[^|;&]*(--delete\b|\s:\S)/, 'Deleting a remote branch affects every agent.'],
  [/\bgit\s+stash\b(?!\s+(list|show))/, 'Stashing can hide another session\'s uncommitted work. Commit to your own branch instead.'],
  [/\bgit\s+rebase\b/, 'Rebasing rewrites commits. Merge or cherry-pick onto a new branch instead.'],
  [/\bgit\s+commit\s+[^|;&]*--amend\b/, 'Amend rewrites the last commit, which may already be pushed or be another agent\'s. Add a new commit.'],
  [/--no-verify\b/, 'Hooks and checks are the shared contract. Fix the failure instead of skipping it.'],
  [/core\.hooksPath|COEXIST_ALLOW|agent-claims/, 'Changing the hook path, setting the override or editing claims by hand switches off the shared guard.'],
]
// Strip git's global options so `git -C dir -c x=y push -f` reads as `git push -f`.
const normalize = cmd => cmd.replace(/\bgit((?:\s+(?:-C|-c|--git-dir|--work-tree|--namespace)(?:\s+|=)("[^"]*"|'[^']*'|\S+)|\s+(?:--no-pager|-P|--bare|--no-replace-objects|--literal-pathspecs))*)\s+/g, 'git ')
// Files that make up the guard itself: an agent editing them needs the human's yes.
const GUARD_FILES = /(coexist-guard\.cjs|[\\/]\.githooks[\\/][^\\/]+|[\\/]\.git[\\/]hooks[\\/][^\\/]+|[\\/]\.claude[\\/]settings(\.local)?\.json|agent-coexist[\\/]SKILL\.md)$/

const block = msg => { process.stderr.write(`[coexist-guard] BLOCKED: ${msg}\nIf the human explicitly asked for this, they can run it themselves with the ! prefix.\n`); process.exit(2) }

const pretool = input => {
  const file = input?.tool_input?.file_path || input?.tool_input?.notebook_path
  if (typeof file === 'string' && GUARD_FILES.test(file)) {
    process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'ask', permissionDecisionReason: `${path.basename(file)} is part of the shared agent guard. Only change it if the human asked.` } }))
    return
  }
  const raw = input?.tool_input?.command
  if (typeof raw !== 'string') return
  const cmd = normalize(raw)
  const cwd = input.cwd || process.cwd()
  for (const [re, why] of RULES) if (re.test(cmd) || re.test(raw)) block(why)

  const branch = git('branch --show-current', cwd)
  const primary = path.resolve(git('rev-parse --path-format=absolute --git-common-dir', cwd) || '.', '..')
  const top = git('rev-parse --show-toplevel', cwd)
  if (/\bgit\s+(checkout|switch)\s+(?!--\s)(?!-- )\S/.test(cmd) && !/\s(-b|-c|--orphan)\s/.test(cmd) && !/\s--\s/.test(cmd) &&
      top && path.resolve(top) === primary) {
    block('The primary checkout belongs to the human. Make your own worktree: git worktree add ../<repo>-<agent>-<topic> -b <agent>/<topic>')
  }
  if (/\bgit\s+(commit|push|merge|cherry-pick)\b/.test(cmd) && branch) {
    const other = heldByOther(branch, cwd)
    if (other) block(`Branch "${branch}" is claimed by ${other.agent} in ${other.worktree} since ${new Date(other.at).toISOString()} (${other.note}). Work on your own branch or ask the human.`)
  }
  const pushTarget = cmd.match(/\bgit\s+push\s+\S+\s+(?:\S+:)?(\S+)/)
  if (pushTarget && PROTECTED.includes(pushTarget[1].replace(/^refs\/heads\//, ''))) {
    process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'ask', permissionDecisionReason: `Push to shared branch "${pushTarget[1]}". Fetched and merged others' commits first?` } }))
  }
}

const status = cwd => {
  const claims = liveClaims(cwd)
  const lines = ['Agent coexistence: read the agent-coexist skill before writing.', 'Live branch claims:']
  lines.push(...(claims.length ? claims.map(c => `  ${c.branch}  <- ${c.agent} in ${c.worktree}  (${c.note}, ${Math.round((Date.now() - c.at) / 60000)} min ago)`) : ['  none']))
  lines.push('Worktrees:', ...git('worktree list', cwd).split('\n').map(l => `  ${l}`))
  return lines.join('\n')
}

const prepush = remote => {
  // stdin: <local ref> <local sha> <remote ref> <remote sha>
  const lines = fs.readFileSync(0, 'utf8').trim().split('\n').filter(Boolean)
  for (const line of lines) {
    const [, localSha, remoteRef, remoteSha] = line.split(' ')
    const branch = remoteRef.replace('refs/heads/', '')
    if (/^0+$/.test(localSha)) { console.error(`[coexist-guard] Refusing to delete ${remote}/${branch}.`); process.exit(1) }
    if (!/^0+$/.test(remoteSha) && !execSyncOk(`git merge-base --is-ancestor ${remoteSha} ${localSha}`)) {
      console.error(`[coexist-guard] ${remote}/${branch} has commits you do not have. Fetch and merge them; do not overwrite.`); process.exit(1)
    }
    const other = heldByOther(branch)
    if (other) { console.error(`[coexist-guard] ${branch} is claimed by ${other.agent} in ${other.worktree} (${other.note}).`); process.exit(1) }
  }
}
// reference-transaction hook: git calls it for every ref change, from any tool or agent.
// Blocks local branch deletion and any move that drops commits (reset to older, amend, rebase, branch -f).
// A local branch MAY be deleted when its tip is already on a remote (a remote-tracking branch contains it, so
// nothing can be lost) and no other session holds a live claim on it (Director, 8 Nov 2026: merged branches
// must clean up without the override). Git itself refuses to delete a branch checked out in any worktree.
// Human override for one command: COEXIST_ALLOW=1 git ...
const reftx = () => {
  if (process.env.COEXIST_ALLOW === '1') return
  const zero = /^0+$/
  const updates = fs.readFileSync(0, 'utf8').trim().split('\n').filter(Boolean).map(l => l.split(' '))
    .filter(([, , ref]) => ref && ref.startsWith('refs/heads/'))
  for (const [oldSha, newSha, ref] of updates) {
    // git branch -d/-D reports "0 0" for a ref that exists; a rename reports "<sha> 0" and is allowed.
    if (zero.test(oldSha) && zero.test(newSha) && execSyncOk(`git rev-parse --verify -q ${ref}`)) {
      const branch = ref.slice('refs/heads/'.length)
      const tip = git(`rev-parse ${ref}`)
      const onRemote = Boolean(tip) && git(`branch -r --contains ${tip}`).length > 0
      const other = heldByOther(branch)
      if (onRemote && !other) continue
      const why = other ? `It is claimed by ${other.agent} in ${other.worktree} (${other.note}).`
        : `Its tip ${tip.slice(0, 7)} is on no remote, so deleting it would lose work. Push it (or tag it) first.`
      console.error(`[coexist-guard] Refusing to delete ${ref}. ${why} Override: COEXIST_ALLOW=1 git ...`); process.exit(1)
    }
    if (zero.test(oldSha) || zero.test(newSha) || oldSha === newSha) continue
    if (!execSyncOk(`git merge-base --is-ancestor ${oldSha} ${newSha}`)) {
      console.error(`[coexist-guard] ${ref} would drop commits (${oldSha.slice(0, 7)} is not in ${newSha.slice(0, 7)}): reset, amend or rebase. Add a new or revert commit instead. Override: COEXIST_ALLOW=1 git ...`); process.exit(1)
    }
  }
}

// pre-commit hook: claims apply to every agent, not just Claude Code.
const precommit = () => {
  if (process.env.COEXIST_ALLOW === '1') return
  const branch = git('branch --show-current')
  const other = branch && heldByOther(branch)
  if (other) { console.error(`[coexist-guard] ${branch} is claimed by ${other.agent} in ${other.worktree} (${other.note}). Commit on your own branch.`); process.exit(1) }
}

const execSyncOk = cmd => { try { execSync(cmd, { stdio: 'ignore' }); return true } catch { return false } }

const [mode, ...args] = process.argv.slice(2)
const readStdin = () => { try { return JSON.parse(fs.readFileSync(0, 'utf8') || '{}') } catch { return {} } }

if (mode === 'pretool') pretool(readStdin())
else if (mode === 'session') { const i = readStdin(); process.stdout.write(status(i.cwd) + '\n') }
else if (mode === 'status') console.log(status())
else if (mode === 'claim') {
  const [branch = git('branch --show-current'), ...note] = args
  const held = heldByOther(branch)
  if (held) { console.error(`${branch} is already claimed by ${held.agent} in ${held.worktree} (${held.note}).`); process.exit(1) }
  fs.writeFileSync(path.join(claimDir(), `${safe(branch)}.json`), JSON.stringify({ branch, agent: AGENT, worktree: holder(), note: note.join(' ') || 'working', at: Date.now() }))
  console.log(`Claimed ${branch} for ${CLAIM_HOURS}h as ${AGENT} (${holder()}).`)
} else if (mode === 'release') {
  const branch = args[0] || git('branch --show-current')
  fs.rmSync(path.join(claimDir(), `${safe(branch)}.json`), { force: true })
  console.log(`Released ${branch}.`)
} else if (mode === 'prepush') prepush(args[0] || 'remote')
else if (mode === 'reftx') reftx()
else if (mode === 'precommit') precommit()
else { console.log('usage: coexist-guard.cjs pretool|session|status|claim <branch> <note>|release <branch>|prepush <remote>'); process.exit(1) }
