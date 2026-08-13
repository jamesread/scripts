# jwr-semrel — reference templates

Default config follows [OliveTin-bindings-php](https://github.com/Olivetin/OliveTin-bindings-php). SOA / GoReleaser extensions follow [OliveTin](https://github.com/Olivetin/OliveTin) with **`@semantic-release/github` added** (OliveTin omits it).

## .releaserc.yaml (default)

Always include `@semantic-release/github` for GitHub Releases and issue/PR success comments.

```yaml
---
branches:
  - main
plugins:
  - '@semantic-release/commit-analyzer'
  - '@semantic-release/release-notes-generator'
  - '@semantic-release/github'

tagFormat: '${version}'
```

## .releaserc.yaml (jwr-soa-2.0 + GoReleaser)

Based on OliveTin / Faridoon, with github plugin added. Plugin order: analyze → notes → github release → publish binaries.

```yaml
---
branches:
  - main
plugins:
  - '@semantic-release/commit-analyzer'
  - '@semantic-release/release-notes-generator'
  - '@semantic-release/github'
  - - '@semantic-release/exec'
    - publishCmd: |
        goreleaser release --clean

tagFormat: '${version}'
```

When GoReleaser also creates GitHub Releases, set in `.goreleaser.yml`:

```yaml
release:
  disable: false
  # Upload assets to the tag semantic-release already created
```

Or use `release.disable: true` in GoReleaser and rely on `@semantic-release/github` for the release page; attach binaries via GoReleaser `extra_files` / workflow upload steps (OliveTin uses separate artifact upload jobs).

OliveTin additionally uses `@semantic-release/git` and a custom `publishCmd` script — keep those only when the repo already depends on git commits of release assets; do not add `@semantic-release/git` by default.

## .releaserc.yaml (keep CHANGELOG.md — PSR migration)

When migrating from PSR and the repo should keep updating `CHANGELOG.md`:

```yaml
---
branches:
  - main
plugins:
  - '@semantic-release/commit-analyzer'
  - '@semantic-release/release-notes-generator'
  - '@semantic-release/changelog'
  - '@semantic-release/github'

tagFormat: '${version}'
```

Remove the PSR `<!-- version list -->` marker when using `@semantic-release/changelog` (it manages the file directly).

## .github/workflows/release.yml (standalone)

From OliveTin-bindings-php. Release runs on push to `main` after a test/build job (add `needs:` as appropriate).

```yaml
name: Release Pipeline

permissions:
  contents: read

on:
  push:
    branches:
      - main
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      # … project-specific test/build steps …

  release:
    runs-on: ubuntu-latest
    needs: [build]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    permissions:
      contents: write
      issues: write
      pull-requests: write
    steps:
      - name: Checkout code
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: release
        uses: cycjimmy/semantic-release-action@v6.0.0
        with:
          semantic_version: 24.2.3
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Pin `semantic_version` deliberately; bump only when intentionally upgrading semantic-release.

### Token note

Use `secrets.GITHUB_TOKEN` when default permissions suffice. Use a PAT (e.g. `secrets.CONTAINER_TOKEN` as in OliveTin) when branch protection blocks `GITHUB_TOKEN` pushes/tags — document the reason in the workflow comment.

## .github/workflows/release.yml (npm package root)

For repos with a root `package.json` (e.g. picocrank):

```yaml
name: Release

on:
  push:
    branches:
      - main

permissions:
  contents: read

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-node@v4
        with:
          node-version: '22'

      - run: npm clean-install

      - name: Release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: npx semantic-release
```

Add `semantic-release` to root `package.json` `devDependencies` when using this layout.

## jwr-soa-2.0 integrated release step

Drop into an existing build pipeline (OliveTin `build-and-release.yml` pattern) **after tests**, when `github.ref_type != 'tag'`:

```yaml
      - name: release
        id: release
        if: github.ref_type != 'tag' && github.event_name != 'pull_request'
        uses: cycjimmy/semantic-release-action@v6.0.0
        with:
          semantic_version: 24.2.3
          extra_plugins: |
            @semantic-release/commit-analyzer
            @semantic-release/release-notes-generator
            @semantic-release/github
            @semantic-release/exec
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Use `steps.release.outputs.new_release_published == 'true'` for post-release steps (artifact upload, SignPath, etc.) — see OliveTin workflow.

## Conventional commits (contributor summary)

| Prefix | Release bump |
|--------|----------------|
| `feat:` | Minor |
| `fix:`, `perf:` | Patch |
| `docs:`, `style:`, `refactor:`, `test:`, `build:`, `chore:`, `ci:` | No bump |
| `feat!:` or `BREAKING CHANGE:` footer | Major |

Issue/PR linking (for `@semantic-release/github` comments): use [closing keywords](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue) in commit messages or PR descriptions (`fixes #123`, `closes #456`).

Examples:

```
feat(auth): add bearer token provider

fix(session): expire cookies on logout (#42)
```

## Migrate from python-semantic-release

### Detection (any match → migrate)

```
pyproject.toml         # [tool.semantic_release]
.github/workflows/     # python-semantic-release/python-semantic-release
CHANGELOG.md           # <!-- version list --> (PSR marker)
```

### PSR → npm mapping

| PSR setting | npm semantic-release equivalent |
|-------------|----------------------------------|
| `tag_format = "v{version}"` | `tagFormat: 'v${version}'` |
| `tag_format = "{version}"` | `tagFormat: '${version}'` (jwr default) |
| `upload_to_vcs_release = true` | `@semantic-release/github` |
| Changelog / `CHANGELOG.md` | `@semantic-release/changelog` (optional) + `@semantic-release/release-notes-generator` |
| `version_variables` | `@semantic-release/git` assets and/or `@semantic-release/exec` |
| Custom publish / GoReleaser | `@semantic-release/exec` `publishCmd` |
| Issue comments | `@semantic-release/github` (PSR has no equivalent) |

### Removal checklist

```
- [ ] Remove [tool.semantic_release] from pyproject.toml (or delete pyproject.toml if PSR-only)
- [ ] Remove python-semantic-release/python-semantic-release workflow steps
- [ ] Add .releaserc.yaml with @semantic-release/github
- [ ] Add or update release workflow (cycjimmy/semantic-release-action or npx semantic-release)
- [ ] Set release job permissions: contents, issues, pull-requests (write)
- [ ] Match tagFormat to existing tags
- [ ] Remove <!-- version list --> unless adopting @semantic-release/changelog
```

### Before / after

**Remove** (PSR — httpauthshim style):

```toml
[tool.semantic_release]
# … entire section …
```

**Replace with** `.releaserc.yaml` default template above and bindings-php-style workflow.

Do **not** keep both PSR and npm semantic-release in the same repo.

## Seeding an existing version

If the project already released `0.1.0`:

```bash
git tag 0.1.0 <commit-sha>    # or v0.1.0 if using v-prefix tagFormat
git push origin 0.1.0
```

The next qualifying `feat:` / `fix:` on `main` bumps the version. Release notes appear on the GitHub Release created by `@semantic-release/github`.
