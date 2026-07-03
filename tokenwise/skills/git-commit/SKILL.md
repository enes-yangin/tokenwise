---
name: git-commit
description: >-
  Atomic commits and branch hygiene for Git. Use this WHENEVER you're about to commit,
  are asked to "commit this", "save my work", "split these changes", "write a commit
  message", or are starting work that should go on its own branch. It produces small,
  single-purpose commits with clear conventional messages and sane branch names, so
  history stays reviewable, revertable, and bisectable. Reach for it even on a quick
  commit — a tidy atomic commit costs almost nothing now and saves a painful git
  archaeology session later.
---

# Atomic commits & branching

A commit is a unit of history, not a save button. The goal is a log where each commit is
**one logical change** that builds, passes tests, and can be understood, reviewed, or
reverted on its own. That discipline is also token-cheap: a clean atomic commit is
trivial to review and `git revert`, while a tangled mega-commit forces everyone (human
or agent) to re-derive what happened.

## Before committing — branch check

Don't commit straight to the default branch (`main`/`master`). If you're on it, create a
branch first:

- Name it `<type>/<short-kebab-summary>`: `feat/user-auth`, `fix/null-name-crash`,
  `refactor/extract-mailer`, `docs/readme-setup`.
- Keep one branch to one coherent piece of work.

`git status` and `git branch --show-current` tell you where you are. Branch only when
the user hasn't said to commit in place.

## What "atomic" means

One commit = one logical change. Concretely:

- A bug fix and an unrelated refactor are **two** commits, even if you touched both in
  one session.
- A formatting sweep goes in its own commit, separate from behavior changes — mixing
  them buries the real change in noise.
- Each commit should leave the tree in a working state (builds, tests pass). This is
  what makes `git bisect` and `git revert` actually usable.

If your working tree has several unrelated changes, **split them** (see below) rather
than committing one blob.

## Splitting changes

Stage by logical unit, not all at once:

- `git status` to see everything changed; group the files/hunks by intent.
- `git add <specific files>` per logical group. **Never run `git add -p` or `git add -i`**
  — both are interactive (they prompt per-hunk over stdin) and will hang an agent's
  non-interactive terminal indefinitely.
- If one file mixes two unrelated changes, split it non-interactively instead: run
  `git diff -- <file>` to see the hunks, write a patch containing only the hunks for one
  logical group, and apply it with `git apply --cached` (fed via a heredoc or a temp
  file, not stdin prompts). Commit that group, then repeat for the rest of the file.
- Commit each group with its own message before staging the next.

Before staging, look at the actual diff (`git diff`) — don't commit what you haven't
read. Watch for accidental inclusions: debug prints, secrets, large generated files,
unrelated edits.

## Commit message format

Conventional Commits — a structured subject so history is scannable and tooling-friendly:

```
<type>(<optional scope>): <imperative summary, ≤ ~72 chars>

<optional body: WHY the change, not what — the diff shows what.
 Wrap at ~72 cols. Explain context, trade-offs, consequences.>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `style`, `build`,
`ci`. Subject is imperative mood ("add", not "added"/"adds") and not capitalized after
the colon, no trailing period.

**Examples**

Input: implemented JWT login and added tests
Output: `feat(auth): add JWT-based login`

Input: fixed the crash when user has no last name
Output:
```
fix(users): handle missing last name in full_name

full_name assumed both fields were set; a user created via the import
path can have last=None, which raised AttributeError on .strip().
Default to empty string and trim.
```

Input: ran the formatter across the repo
Output: `style: apply ruff format across repo`

Input: pulled the email sending into its own module
Output: `refactor(mailer): extract send logic from views`

Keep the subject about *one* thing. If you need "and" in the subject, it's probably two
commits.

## Body: when to include one

- **Skip** the body for self-evident changes (`docs: fix typo in README`).
- **Include** it when the *why* isn't obvious from the diff: a non-obvious fix, a
  trade-off, a workaround, anything a future reader would otherwise have to reconstruct.
  The body is where you spend tokens that save someone a future investigation.

## Committing — practical notes

- Commit or push **only when the user asks**. Don't auto-push.
- Don't skip hooks (`--no-verify`) or signing unless the user explicitly says so. If a
  pre-commit hook fails, fix the underlying issue rather than bypassing it.
- Prefer a new commit over amending one that may already be shared.
- For multi-line messages on the shell, use a heredoc (or your harness's preferred
  mechanism) so the body formats correctly.

## The one check

Before you commit, read your own diff and ask: "is this exactly one logical change, and
does the subject line describe it in one breath?" If the diff has two unrelated changes,
split it. If the subject needs an "and", split it.
