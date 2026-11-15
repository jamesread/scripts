---
name: jwr-dep-update
description: >-
  Updates project dependencies for npm and Go ecosystems, prefers
  jwr-renovate-local when on PATH and renovate.json exists, checks open
  dependency PRs and aligns local bumps to resolve them, runs audits and tests,
  and reports issues for manual review. Use when the user asks to update
  dependencies, bump packages, run npm-check-updates, refresh go.mod, or
  perform routine dependency maintenance. Commits dependency changes with
  chore: dep update; never pushes or closes PRs.
disable-model-invocation: true
---

# jwr-dep-update

Update dependencies, validate the result, commit dependency-related changes, and produce a review report. **Do not push or close pull requests.**

## Hard rules

- **Commit** dependency-related changes only after build/tests pass (Step 3), using exactly:
  ```bash
  git commit -m "chore: dep update"
  ```
- Stage **only** dependency manifests and lockfiles (e.g. `package.json`, `package-lock.json`, `npm-shrinkwrap.json`, `yarn.lock`, `pnpm-lock.yaml`, `go.mod`, `go.sum`). Respect `.gitignore`. Do **not** stage source files, `.renovate/`, or unrelated edits.
- **Never** run `git push` or `jwr-gacp` unless the user explicitly asks to push in the same request.
- **Never** run `gh pr close`, merge PRs, or otherwise close dependency update PRs.
- **Never** use `npm audit fix --force` unless the user explicitly approves after seeing the report.
- Stop and ask before making source-code changes to fix breakage (only dependency/lockfile updates are in scope by default). Leave any required source fixes **uncommitted**.
- If tests fail and cannot be fixed with trivial dependency-only adjustments, **do not commit** — report failures and leave changes for the user.
- Summarize every warning, failure, and unresolved audit finding in the final report.

## Workflow overview

```
Task Progress:
- [ ] 1. Discover ecosystems, baseline state, renovate tooling, and open dependency PRs
- [ ] 2. Update dependencies (jwr-renovate-local if available, PR alignment, bulk npm/Go, audit/tidy)
- [ ] 3. Build and test
- [ ] 4. Commit dependency changes
- [ ] 5. Report for manual review
```

---

## Step 1: Discover ecosystems and open dependency PRs

From the repo root (or path the user gave):

1. Find `package.json` files (npm/JavaScript).
2. Find `go.mod` files (Go).
3. Note a root `Makefile`, `integration-tests/`, and other test entry points (see [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md) layout when present).
4. Check for Renovate local tooling (see below).

Record current branch and whether the working tree was clean before starting (`git status`). **Remember the clean/dirty state** — `jwr-renovate-local` requires a clean tree at the start of Step 2.

### Renovate local tooling

When `command -v jwr-renovate-local` succeeds and the repo root has `renovate.json`, Renovate local updates are available.

Also verify `docker` is on PATH (`jwr-renovate-local` runs Renovate in Docker). If Docker is missing, note it and fall back to manual npm/Go updates only.

`jwr-renovate-local` (repo root):

- Runs Mend Renovate in local dry-run mode and writes `.renovate/report.json`
- Applies manifest edits via `jwr-renovate-apply` (also on PATH when the wrapper is installed)
- Respects `renovate.json` — same rules as open Renovate PRs on GitHub
- **Requires a clean working tree**; refuses to run if there are uncommitted changes
- By default applies **non-major** bumps only; set `RENOVATE_APPLY_MAJORS=1` to include majors

Record whether Renovate local will be used in Step 2.

For monorepos, update each npm or Go module separately; run tests at the appropriate scope (per package or repo-wide `make` targets).

### Open dependency PRs

When `gh` is available and the repo has a GitHub remote, list open PRs and identify dependency-update PRs:

```bash
gh pr list --state open --json number,title,author,headRefName,labels,body,files --limit 100
```

Treat a PR as **dependency-related** when any of these match:

| Signal | Examples |
|--------|----------|
| Author login | `dependabot`, `renovate`, `renovate[bot]`, `app/dependabot` |
| Label | `dependencies`, `dependency`, `renovate`, `security` (when paired with dep bumps) |
| Title / branch | `bump`, `update dependency`, `deps`, `chore(deps)`, `fix(deps)`, `renovate/` prefix |

For each dependency PR, extract:

- **PR number** and title
- **Package/module name** and **target version** (from title, body tables, or changed manifest files)
- **Ecosystem** (npm vs Go) and **manifest path** (`package.json`, `go.mod`, etc.)

Common title patterns:

- Dependabot: `Bump <pkg> from <old> to <new>`
- Renovate: `Update dependency <pkg> to <new>` or grouped `Update all non-major dependencies`

Use `gh pr diff <number> --name-only` or the `files` field when the title/body does not spell out versions.

Build an **open PR target list** — one row per package/module the PR would update. If multiple open PRs target the same dependency, prefer the **newest/highest** semver target (or the most recent PR when versions are unclear).

If `gh` is missing or the repo is not on GitHub, note that in the report and proceed with normal bulk updates only.

---

## Step 2: Update dependencies

Apply updates in order: **Renovate local (when available)**, **PR alignment**, then **routine bulk updates** for anything still outstanding.

### 2.0 Renovate local (`jwr-renovate-local`)

When Step 1 found `jwr-renovate-local` on PATH, `renovate.json` at the repo root, and Docker available:

1. **Only if the working tree is clean.** If the user already had uncommitted changes at the start, skip this subsection, note why in the report, and use manual updates (2a–2c) instead.
2. From the repo root, run before any other manifest edits:

```bash
# Include major bumps when open Renovate PRs target majors
export RENOVATE_APPLY_MAJORS=1   # omit or unset when no open PR needs a major bump
jwr-renovate-local
```

Set `RENOVATE_APPLY_MAJORS=1` when the open PR target list (Step 1) includes any **major** semver bump; otherwise leave it unset so behavior matches typical Renovate PRs.

3. Capture stdout/stderr and read `.renovate/report.json` if present for the list of applied updates.
4. **Refresh lockfiles** — `jwr-renovate-apply` only edits manifests (e.g. `package.json`, `go.mod`). After a successful run:
   - In each directory with a changed `package.json`: `npm install`, then `npm audit fix` if the project uses npm audit
   - In each directory with a changed `go.mod`: `go mod tidy`

If `jwr-renovate-local` fails (missing config, Docker error, empty report), document the failure and continue with 2a–2c. Do not abort the whole skill unless nothing else can run.

When Renovate local succeeds, treat it as the primary bulk update — **skip 2b/2c** for ecosystems and manifests Renovate already changed, then use 2a only to close gaps vs open PRs and 2b/2c only for modules Renovate does not manage.

### 2a. Align with open dependency PRs

For each entry in the open PR target list, bump the working tree to **at least** the PR’s target version (same version is fine; newer is OK if a later bulk step goes higher).

**npm** (in the directory containing the manifest):

```bash
npm install <package>@<target-version>
```

For devDependencies, add `--save-dev`. For monorepos, run in the package directory that owns the manifest the PR changes.

**Go** (in the module directory):

```bash
go get <module>@<target-version>
```

When a PR updates several packages (grouped Renovate PR), apply each package from the PR diff or body, not just the title.

After explicit bumps, run `npm install` (npm) or `go mod tidy` (Go) in the affected directories.

**Do not** check out PR branches or merge PRs — only reproduce their dependency outcomes on the current branch.

### 2b. Routine npm updates

Skip packages/manifests already updated by `jwr-renovate-local` unless 2a still shows gaps.

When `package.json` is present, in that directory:

```bash
ncu -u
npm install
npm audit fix
```

If `ncu` is not on PATH, use `npx npm-check-updates -u` instead.

After bulk `ncu`, verify packages from the open PR target list were **not downgraded** below PR targets. If `ncu` pinned an older version, restore the PR target (or newer) with `npm install <package>@<version>`.

After install:

- Read command output for peer dependency warnings, engine mismatches, deprecated packages, and install errors.
- Run `npm audit` again if `npm audit fix` could not resolve everything; list remaining vulnerabilities by severity.
- Note major version bumps in `package.json` (breaking-change risk).

### 2c. Routine Go updates

Skip modules already updated by `jwr-renovate-local` unless 2a still shows gaps.

When `go.mod` is present, in that module directory:

```bash
go get -u ./...
go mod tidy
```

After bulk `go get`, verify modules from the open PR target list were **not downgraded** below PR targets. If needed, re-apply `go get <module>@<target-version>` and `go mod tidy`.

Then scan output for:

- Retracted module versions
- Incompatible or ambiguous module paths
- `go mod tidy` errors or unexpected `replace`/`exclude` changes

### 2d. Resolve open PRs (working tree only)

Compare the resulting manifest/lockfile state to each open dependency PR’s diff:

| Outcome | Meaning |
|---------|---------|
| **Likely resolved** | Local versions match or exceed every bump in the PR; lockfiles cover the same packages |
| **Partially aligned** | Some PR packages updated; others missing or still older |
| **Unrelated** | PR targets a manifest path or ecosystem not touched |

Record this per PR for the final report. **Do not close PRs** — after the Step 4 commit, the user can close them or let GitHub mark them superseded.

---

## Step 3: Build and test

Prefer project conventions when they exist:

| Signal | Action |
|--------|--------|
| Root or subdir `Makefile` | `make`, `make test`, and other relevant targets |
| Go module | `go test ./...` (add `-race` if the project normally uses it) |
| npm package with `"test"` script | `npm test` |
| `integration-tests/` or jwr-soa-2.0 layout | Run integration tests per project docs or Makefile |
| CI config (`.github/workflows`, etc.) | Mirror lint/test steps locally when feasible |

If tests fail:

1. Capture the failure output.
2. Attempt **minimal** fixes only when clearly caused by the dependency bump (e.g. renamed export, trivial API change).
3. If the fix needs non-trivial code changes, **stop**, document the failure, and leave fixes to the user.

Do not skip tests when they exist and are runnable in this environment.

---

## Step 4: Commit dependency changes

When Step 3 passed and dependency manifests or lockfiles changed:

1. Review `git status` and `git diff` — confirm only dependency files will be staged.
2. Stage dependency files explicitly (prefer path lists over `git add -A`):

```bash
git add package.json package-lock.json go.mod go.sum
# add other lockfiles/manifest paths as applicable
```

3. Commit with the fixed message:

```bash
git commit -m "chore: dep update"
```

If nothing dependency-related changed, skip the commit and note that in the report.

If pre-commit hooks reject the commit, fix dependency-only issues if possible, re-stage, and retry. If the hook still fails or modifies non-dependency files, stop and report — do not bypass hooks.

Do **not** push. Do **not** commit when tests failed or when the only remaining changes are non-dependency source fixes.

---

## Step 5: Report for manual review

Use this template:

```markdown
# Dependency update report

## Summary
[One paragraph: what was updated, overall pass/fail, whether jwr-renovate-local ran, commit created or skipped, how open dependency PRs were handled]

## Commit
- Created: [yes / no — reason]
- Message: `chore: dep update`
- Files committed: [list or n/a]

## Renovate local
- Used: [yes / no / skipped — reason]
- Majors applied: [RENOVATE_APPLY_MAJORS yes/no]
- Updates applied: [from jwr-renovate-local output or .renovate/report.json]

## Open dependency PRs (not closed)
| PR | Title | Target | Alignment | Notes |
|----|-------|--------|-----------|-------|
| #123 | Bump foo to 2.0.0 | foo@2.0.0 | Likely resolved | Local tree matches PR bump |

## Ecosystems touched
- [ ] npm: [paths]
- [ ] Go: [paths]

## Version changes
### npm
| Package | Before | After | Matched open PR |
|---------|--------|-------|-----------------|

### Go
[List notable module version changes from go.mod / go.sum diff; note matched open PRs]

## Audit / security
- npm audit: [clean / N remaining — list critical/high]
- Other: [go vuln check if run, etc.]

## Tests
| Target | Result | Notes |
|--------|--------|-------|

## Warnings and manual follow-ups
- [ ] Push the commit when ready (`git push` — not done by this skill)
- [ ] Review major semver bumps
- [ ] Close or refresh open dependency PRs after pushing (PRs were not closed by this skill)
- [ ] [Any unresolved audit items]
- [ ] [Any test failures or uncommitted source fixes]
- [ ] [Any open PRs still partially aligned]

## Uncommitted changes (if any)
[List files left unstaged — e.g. source fixes, .renovate/, unrelated edits]
```

Open dependency PRs remain open until the user pushes and chooses to close them.

---

## Prerequisites

- **Renovate local** (optional, preferred when available): `jwr-renovate-local` and `jwr-renovate-apply` on PATH, `renovate.json` at repo root, Docker installed and runnable, **clean working tree** at the start of Step 2.
- **GitHub CLI**: `gh` authenticated when checking open dependency PRs (optional — skip PR discovery if unavailable).
- **npm**: Node.js/npm installed; `npm-check-updates` (`ncu`) available globally or via `npx`.
- **Go**: Go toolchain installed; module proxy reachable.

If a core prerequisite is missing (npm/Go where those ecosystems exist), report it and stop rather than improvising a partial update. Optional tooling (`gh`, `jwr-renovate-local`) — skip that path and note it in the report when unavailable.
