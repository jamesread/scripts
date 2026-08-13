---
name: jwr-repohelper-health
description: >-
  Run `repo-helper health` to check repository hygiene (README shields, common
  files, GitHub community profile, pre-commit, issue templates, etc.). Use when
  the user asks for repo health, maturity badge checks, common-files sync, or
  jwr-repohelper-health.
---

# jwr-repohelper-health

Run repository health checks via the locally installed `repo-helper` CLI.

## Prerequisites

1. Verify the tool exists:

```bash
command -v repo-helper
```

If this fails, tell the user `repo-helper` is not installed or not on `PATH`, and **stop**. Do not attempt workarounds or alternate checks.

2. Run from the **repository root** (where `README.md` and `.git` live). `cd` there first if needed.

3. Some checks need network and GitHub CLI (`gh` auth): maturity topic sync, community health. Offline skips apply when `OFFLINE` is set.

## Run checks

```bash
repo-helper health
```

To include skipped tests (e.g. common-files sub-checks that did not apply):

```bash
repo-helper health --show-skipped
```

## What is checked

| Check | Pass criteria |
|-------|---------------|
| `check_maturity_label` | README has a shields.io maturity badge; badge value matches a `maturity-*` GitHub topic |
| `check_logo_exists` | `logo.svg` present |
| `check_discord_link_exists` | README contains a `discord.gg` link |
| `check_security_exists` | `SECURITY.md` present |
| `check_contributing_guide_exists` | `CONTRIBUTING.md` present |
| `check_precommit_exists` | `.pre-commit-config.yaml` present (also runs conventional-commit hook check) |
| `check_issue_templates_exist` | `.github/ISSUE_TEMPLATE/` present |
| `check_community_health` | GitHub community profile is 100% |
| `check_common_files` | Files under `repo-common/common-files` (via `COMMON_DIR`) match repo copies when `match.yml` rules apply |

## Interpreting output

- `[  OK  ] check_name` — passed
- `[FAILED] check_name message` — failed; message explains why
- `[ SKIP ] check_name message` — only with `--show-skipped`

Common failures and fixes:

- **Missing README / maturity shield** — add shields.io maturity badge; set matching `maturity-*` topic on GitHub
- **Common files mismatch** — follow `SUGGEST:` lines (`cp`, `vimdiff`) in output
- **Community health < 100%** — open the linked GitHub community page and add missing files/settings
- **gh / remote errors** — ensure `git remote get-url origin` points at GitHub and `gh auth status` succeeds

## After running

Summarize pass/fail counts. For each failure, quote the check name and suggest the concrete fix from the tool output. Offer to apply fixes only when the user asks.
