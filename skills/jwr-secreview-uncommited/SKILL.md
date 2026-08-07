---
name: jwr-secreview-uncommited
description: >-
  Security review of uncommitted (staged and unstaged) local changes. Use when
  the user runs /jwr-secreview-uncommited, asks whether local edits introduce
  new security issues, or wants a security check before committing dirty
  working-tree changes.
disable-model-invocation: true
---

# jwr-secreview-uncommited

Security review of **uncommitted changes only** — staged and unstaged edits in the working tree. Answer whether these changes introduce **new** security issues.

Use when the user runs `/jwr-secreview-uncommited`.

## Scope

Review only what is not yet committed:

- Staged changes (`git diff --cached`)
- Unstaged changes (`git diff`)

Do **not** include commits already on the branch. For branch-wide or PR review, use `/review-security` instead.

## Workflow

```
Task Progress:
- [ ] 1. Confirm uncommitted changes exist
- [ ] 2. Launch security-review subagent (uncommitted changes)
- [ ] 3. Summarize findings
```

### Step 1: Confirm uncommitted changes

From the repository root (active workspace or path the user gave), run in parallel:

```bash
git status --short
git diff --stat
git diff --cached --stat
```

- If there are no staged or unstaged changes, stop. Tell the user in one sentence that there is nothing uncommitted to review.
- If changes exist, note which files are staged, unstaged, or both. Proceed to step 2.

### Step 2: Launch security-review subagent

Launch exactly one `security-review` subagent with:

- `readonly: true`
- `run_in_background: false` unless the user explicitly asks to run in background
- `description: "Security Review"`
- `subagent_type: "security-review"`

The subagent computes the local diff from the repository path. Do not compute the full diff yourself before launching it.

Use this exact prompt shape:

```text
Full Repository Path: <absolute repository path>
Diff: uncommitted changes
Custom Instructions: Focus on whether these uncommitted changes introduce new security issues. Report only findings attributable to the changed lines — not pre-existing problems elsewhere in the repo. Prioritize: credential/secret exposure, injection (SQL, command, XSS), authn/authz bypasses, insecure crypto, SSRF/path traversal, unsafe deserialization, missing input validation, overly broad permissions, and sensitive data in logs or errors.
```

Do not include `Base Branch` — it does not apply to uncommitted changes.

If the user gave additional review focus (e.g. "check the new API endpoint"), append it to `Custom Instructions`.

#### Subagent failures

If the subagent fails before producing findings, inspect the failure text.

- If caused by incorrect invocation (missing path, wrong prompt shape, wrong subagent type), correct and retry once immediately.
- For any other failure, retry once with the same prompt shape.
- If the same failure persists after retry, stop. Tell the user the review could not complete and include the short error or blocker. Do not keep retrying.

### Step 3: Summarize findings

After the subagent finishes:

- **Empty diff**: one sentence — no uncommitted diff to review.
- **No issues**: one-line verdict, e.g. "Security review found no new issues in uncommitted changes."
- **Issues found**: lead with a one-line verdict, then a compact markdown table sorted by severity (highest first):

| Severity | Location (file:line) | Finding |
|----------|----------------------|---------|
| ...      | `path/to/file:42`    | ...     |

For each finding, state whether it is **new** (introduced by the uncommitted diff) or **pre-existing** (touched but not introduced). If unclear, say so.

End with a direct answer to: **Do these uncommitted changes create any new security issues?** Yes / No / Unclear — with a brief justification.

## Hard rules

- Do **not** fix findings or modify code unless the user explicitly asks.
- Do **not** commit, stage, or push changes.
- Do **not** rerun the review unless the user asks.
