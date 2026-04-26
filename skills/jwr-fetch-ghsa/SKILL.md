---
name: jwr-fetch-ghsa
description: Fetch private GitHub Security Advisories (GHSA) for this repo using GitHub
---

# Fetching private GitHub Security Advisories (GHSA)

Private or draft security advisories for this repo are **repository-level**, not global. The global advisory APIs do not return them.

This skill refers to the example repo `OliveTin/OliveTin` which has a mix of public and private advisories. Replace with your own repo as needed, by checking the git origin.

## Prerequisites

- [GitHub CLI](https://cli.github.com/) (`gh`) installed and authenticated (`gh auth status`).
- Repo access that includes permission to view security advisories (e.g. maintainer or collaborator).

## Get one advisory by GHSA ID

```bash
gh api "/repos/OliveTin/OliveTin/security-advisories/GHSA-XXXX-XXXX-XXXX"
```

Replace `GHSA-XXXX-XXXX-XXXX` with the full advisory ID (e.g. `GHSA-fwhj-785h-43hh`).

Example with pretty-printed JSON:

```bash
gh api "/repos/OliveTin/OliveTin/security-advisories/GHSA-fwhj-785h-43hh" | jq .
```

## List all repository advisories

```bash
gh api "/repos/OliveTin/OliveTin/security-advisories"
```

Returns all advisories for this repo (including draft/triage/private). Pipe to `jq` to filter or format.

## What does *not* work for private advisories

- **Global REST API**  
  `gh api /advisories/GHSA-xxxx-xxxx-xxxx` → 404 for repo-only advisories.

- **GraphQL `securityAdvisory(ghsaId: "...")`**  
  Resolves only **global** (published) advisories; returns null for repo-only/draft.

- **`gh advisory view`**  
  Not available in all `gh` installs; when present, it typically queries global advisories only.

So for any GHSA that might be private or in triage/draft, use the **repo path** above.

## Repo-specific API reference

- [GitHub REST API: Get a repository security advisory](https://docs.github.com/en/rest/security-advisories/repository-advisories#get-a-repository-security-advisory)
- [List repository security advisories](https://docs.github.com/en/rest/security-advisories/repository-advisories#list-repository-security-advisories)
