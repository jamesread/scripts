---
name: jwr-semrel
description: >-
  Sets up npm semantic-release with @semantic-release/github for jwr repos:
  conventional commits, GitHub releases, and issue/PR success comments. Migrates
  repos away from python-semantic-release ([tool.semantic_release], PSR action)
  when found. Use for jwr-soa-2.0 release automation, semantic versioning,
  or when the user mentions jwr-semrel or semantic-release.
---

# jwr-semrel

Automated versioning via [semantic-release](https://semantic-release.gitbook.io/) (npm), with **`@semantic-release/github`** for GitHub Releases and success comments on linked issues/PRs.

Reference implementations:

- **Default (GitHub plugin):** [OliveTin-bindings-php](https://github.com/Olivetin/OliveTin-bindings-php) — `.releaserc.yaml` + release job permissions
- **jwr-soa-2.0 (GoReleaser):** [OliveTin](https://github.com/Olivetin/OliveTin) — build pipeline + `@semantic-release/exec`; add `@semantic-release/github` (OliveTin omits it because GoReleaser owns release assets — jwr standard includes github for issue comments)

Templates: [reference.md](reference.md). Companion: [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md).

## When to use

- New jwr repo needs conventional-commit-driven releases on `main`.
- Existing repo migrates from manual tags, ad-hoc versioning, or **python-semantic-release**.
- User asks to align release automation with jwr / OliveTin patterns.

## Detect python-semantic-release (PSR)

**If any of these are present, migrate to npm semantic-release** (do not leave both in place):

| Signal | Examples |
|--------|----------|
| `pyproject.toml` | `[tool.semantic_release]` tables |
| CI workflow | `python-semantic-release/python-semantic-release` action |
| Changelog marker | `<!-- version list -->` in `CHANGELOG.md` (PSR insertion flag) |

Read the old config first. Note `tag_format`, `upload_to_vcs_release`, `version_variables`, and any post-release workflow steps — map during migration (reference.md).

## Setup checklist

```
- [ ] Detect and remove python-semantic-release (if present — see migration below)
- [ ] Add .releaserc.yaml (include @semantic-release/github — reference.md)
- [ ] Add or update .github/workflows/release.yml (or integrate into build pipeline)
- [ ] Ensure release job permissions: contents, issues, pull-requests (write)
- [ ] Ensure default branch is main (matches branches config)
- [ ] Document conventional commits for contributors
- [ ] Seed or preserve existing git tags (match tagFormat to history)
- [ ] For jwr-soa-2.0 + GoReleaser: add @semantic-release/exec publishCmd (reference.md)
```

## Migrate from python-semantic-release

When PSR is detected, **replace it** with the npm stack:

1. **Preserve history** — existing git tags and any `CHANGELOG.md` content stay; do not retag or rewrite history.
2. **Match tag format** — jwr default is `tagFormat: '${version}'` (no `v` prefix, OliveTin style). If PSR used `tag_format = "v{version}"`, keep `tagFormat: 'v${version}'` when existing tags have the `v` prefix.
3. **Map PSR settings to plugins**:
   - `upload_to_vcs_release = true` or desired GitHub Releases → `@semantic-release/github` (jwr default).
   - PSR changelog / `CHANGELOG.md` updates → optional `@semantic-release/changelog` plugin if the repo should keep updating that file; otherwise release notes live on GitHub Releases only.
   - `version_variables` → `@semantic-release/git` assets and/or `@semantic-release/exec` prepareCmd; or bump versions in the workflow step.
   - GoReleaser / custom publish → `@semantic-release/exec` `publishCmd` (OliveTin / Faridoon pattern).
4. **Add** `.releaserc.yaml` and **replace** PSR workflow steps with `cycjimmy/semantic-release-action` or `npx semantic-release`.
5. **Remove PSR tooling**:
   - Delete all `[tool.semantic_release]` tables from `pyproject.toml` (keep unrelated Python package metadata).
   - Delete `pyproject.toml` entirely when it existed **only** for PSR (e.g. Go library with no Python package).
   - Remove `python-semantic-release/python-semantic-release` workflow steps.
   - Remove `<!-- version list -->` marker when not using `@semantic-release/changelog`.
6. **Keep unrelated tooling** — do not remove frontend `package.json`, Go modules, or Python package metadata unrelated to releases.

Full PSR removal checklist: [reference.md](reference.md#migrate-from-python-semantic-release).

## Workflow

1. **Read the repo** — default branch, existing tags, CI layout, PSR signals, GoReleaser (`.goreleaser.yml`), root vs frontend `package.json`.
2. **Choose layout** (reference.md):
   - **Standalone release** — separate `.github/workflows/release.yml` after tests (bindings-php style).
   - **jwr-soa-2.0 integrated** — semantic-release step in build pipeline after tests, before/with GoReleaser (OliveTin style).
   - **npm package** — root `package.json` with `semantic-release` devDependency + `npx semantic-release` (picocrank style).
3. **Add `.releaserc.yaml`** — always include `@semantic-release/github`. Extend with `@semantic-release/exec` when GoReleaser or custom publish is needed.
4. **Add or update release workflow** — `fetch-depth: 0`, release job permissions, pin action version (reference.md).
5. **Token** — default `GITHUB_TOKEN` with explicit job permissions. Use a PAT (e.g. `CONTAINER_TOKEN`) only when branch protection or downstream triggers require it (document why).
6. **Conventional commits** — contributors use `feat:`, `fix:`, etc. Closing keywords in commits/PRs (`fixes #123`) drive `@semantic-release/github` success comments.

## Behaviour (defaults)

| Setting | Value | Notes |
|---------|-------|-------|
| Tags | `${version}` | e.g. `1.2.3` (no `v` prefix) |
| Branch | `main` | Stable releases |
| GitHub Releases | On | `@semantic-release/github` |
| Issue/PR comments | On | Default success comment on resolved issues/PRs |
| Release notes | GitHub Release | Optional `@semantic-release/changelog` for `CHANGELOG.md` |
| GoReleaser (SOA) | `@semantic-release/exec` | After github plugin in plugin order |

## jwr-soa-2.0 notes

For [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md) monorepos (`service/`, `frontend/`, `integration-tests/`):

- Run semantic-release **after** unit/integration tests pass on `main`.
- Use `@semantic-release/exec` with `goreleaser release --clean` when `.goreleaser.yml` exists (OliveTin reference).
- **Add `@semantic-release/github`** even when GoReleaser publishes binaries — github handles release notes and issue comments; configure GoReleaser to attach assets to the semantic-release tag (see reference.md).
- OliveTin uses `@semantic-release/git` + exec without github; **jwr standard replaces that omission** with github + exec.

## Verification

After setup:

1. Confirm `.releaserc.yaml` lists `@semantic-release/github`.
2. Confirm release job has `contents: write`, `issues: write`, `pull-requests: write`.
3. Confirm workflow uses `fetch-depth: 0`.
4. Confirm no `[tool.semantic_release]` remains in `pyproject.toml`.
5. Confirm `tagFormat` matches existing tags in the repo.

## Related skills

- [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md) — project layout, build pipeline, GoReleaser
- [jwr-gacp](../jwr-gacp/SKILL.md) — conventional commit messages
