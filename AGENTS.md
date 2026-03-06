# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds


## Repository Hygiene
- Always use a dedicated linked git worktree for any code change, PR review, or PR fix. Never work from the primary checkout.
- Never make code changes on `main` or `master`. Create a topic branch in a worktree first.
- Before editing, run `bash scripts/hygiene_check.sh` from the repo root if the script exists.
- Prefer `bash scripts/new_worktree.sh <branch-name>` to create task branches in `../_worktrees/`.
- Before commit or push, run the narrowest relevant test command for the repo and then `bash scripts/hygiene_check.sh` again.
- If repo state changes unexpectedly, stop and inspect `git status`, `git branch --show-current`, and `git reflog --date=iso -5` before continuing.
- Before push, run `bash scripts/review_guard.sh` and `bash scripts/validate_repo.sh` in addition to `bash scripts/hygiene_check.sh`.
