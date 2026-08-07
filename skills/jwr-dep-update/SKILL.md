---
name: jwr-dep-update
description: >-
  Updates project dependencies for npm and Go ecosystems, runs audits and tests,
  and reports issues for manual review. Use when the user asks to update
  dependencies, bump packages, run npm-check-updates, refresh go.mod, or
  perform routine dependency maintenance. Never commits or pushes.
disable-model-invocation: true
---

# jwr-dep-update

Update dependencies, validate the result, and produce a review report. **Do not commit, push, or stage changes.** Leave all modified lockfiles and manifests for the user to review.

## Hard rules

- **Never** run `git add`, `git commit`, `git push`, or any skill that commits (e.g. `jwr-gacp`).
- **Never** use `npm audit fix --force` unless the user explicitly approves after seeing the report.
- Stop and ask before making source-code changes to fix breakage (only dependency/lockfile updates are in scope by default).
- Summarize every warning, failure, and unresolved audit finding in the final report.

## Workflow overview

```
Task Progress:
- [ ] 1. Discover ecosystems and baseline state
- [ ] 2. Update dependencies (npm and/or Go)
- [ ] 3. Audit and tidy
- [ ] 4. Build and test
- [ ] 5. Report for manual review
```

---

## Step 1: Discover ecosystems

From the repo root (or path the user gave):

1. Find `package.json` files (npm/JavaScript).
2. Find `go.mod` files (Go).
3. Note a root `Makefile`, `integration-tests/`, and other test entry points (see [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md) layout when present).

Record current branch and whether the working tree was clean before starting (`git status` for context only — do not stage).

For monorepos, update each npm or Go module separately; run tests at the appropriate scope (per package or repo-wide `make` targets).

---

## Step 2: npm updates

When `package.json` is present, in that directory:

```bash
ncu -u
npm install
npm audit fix
```

If `ncu` is not on PATH, use `npx npm-check-updates -u` instead.

After install:

- Read command output for peer dependency warnings, engine mismatches, deprecated packages, and install errors.
- Run `npm audit` again if `npm audit fix` could not resolve everything; list remaining vulnerabilities by severity.
- Note major version bumps in `package.json` (breaking-change risk).

---

## Step 3: Go updates

When `go.mod` is present, in that module directory:

```bash
go get -u ./...
go mod tidy
```

Then scan output for:

- Retracted module versions
- Incompatible or ambiguous module paths
- `go mod tidy` errors or unexpected `replace`/`exclude` changes

---

## Step 4: Build and test

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

## Step 5: Report for manual review

Use this template:

```markdown
# Dependency update report

## Summary
[One paragraph: what was updated, overall pass/fail]

## Ecosystems touched
- [ ] npm: [paths]
- [ ] Go: [paths]

## Version changes
### npm
| Package | Before | After |
|---------|--------|-------|

### Go
[List notable module version changes from go.mod / go.sum diff]

## Audit / security
- npm audit: [clean / N remaining — list critical/high]
- Other: [go vuln check if run, etc.]

## Tests
| Target | Result | Notes |
|--------|--------|-------|

## Warnings and manual follow-ups
- [ ] Review lockfile changes (`package-lock.json`, `go.sum`)
- [ ] Review major semver bumps
- [ ] [Any unresolved audit items]
- [ ] [Any test failures or suggested code changes]

## Files changed (not committed)
[List key modified files]
```

Remind the user that changes are **uncommitted** and require their review before commit.

---

## Prerequisites

- **npm**: Node.js/npm installed; `npm-check-updates` (`ncu`) available globally or via `npx`.
- **Go**: Go toolchain installed; module proxy reachable.

If a prerequisite is missing, report it and stop rather than improvising a partial update.
