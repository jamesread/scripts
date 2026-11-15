---
name: jwr-marketing-screenshots
description: >-
  Set up reproducible marketing screenshots for a web app in
  var/marketing/screenshots: a one-command `make` that starts a throwaway stack
  (temporary database/broker containers), seeds repeatable fictional marketing
  data, captures pages with `repo-helper screenshot`, generates the well-known
  var/marketing/screenshots/screenshot-manifest.yaml index for indexers,
  publishes images to the README/docs (adding them when the README has none, or
  replacing older/framed screenshots), and tears everything down. Often used
  with jwr-soa style apps. Use when adding or refreshing README/docs
  screenshots, marketing images, product tour images, screenshot manifests, or
  jwr-marketing-screenshots.
---

# jwr-marketing-screenshots

Build a self-contained, repeatable screenshot pipeline in **`var/marketing/screenshots/`**, so that anyone can regenerate every marketing image with:

```bash
make -C var/marketing/screenshots     # or `make screenshots` from the repo root
```

This is often used with **jwr-soa** style apps (Go Connect RPC backend, Vue/Vite + PicoCrank frontend, MySQL, optional RabbitMQ), but the pattern works for any web app that can run locally.

For `repo-helper screenshot` itself (INI keys, setup scripts, capture pipeline, crop options), see the **jwr-repohelper-screenshots** skill. This skill covers everything around it: the stack, the data, and the publishing. Templates are in [reference.md](reference.md).

## Non-negotiable rules

### 1. Repeatable marketing data, never dev stack data
- **Never** point screenshots at a developer's running stack, a shared dev, staging or production environment, or a copy of a real database. That data is unrepeatable and may be private.
- Every run starts from an **empty** database and is seeded only from files committed under `var/marketing/screenshots/seed/`.
- The output must be the same on every machine and every run. The only acceptable differences are wall-clock timestamps.

### 2. Safe, obviously fictional data
- Use `example.com`, `example.org`, `example-org`, `demo-*` IDs, and made-up names. Never use real customers, real people, real email addresses, internal hostnames, or the maintainer's own accounts or repos.
- Never use real tokens or API keys. Credentials are throwaway values that exist only inside the temporary containers (`<app>-demo`, `guest/guest`, …).
- Prefer config keys the UI already redacts (`*.password`, `*token*`, `*secret*`) over URLs with embedded credentials, so secrets never appear in an image.
- Before committing, look at every PNG and check that nothing sensitive is visible, including localhost URL history, usernames, and hostnames.

### 3. Temporary infrastructure only
- Databases, brokers and caches run as **temporary containers**: `podman`/`docker run -d --rm`, with **no volumes**. Make the runtime switchable with `CONTAINER ?= podman`.
- Use fixed, prefixed container names (`<app>-mkt-mysql`, `<app>-mkt-rabbitmq`) and **non-default host ports** bound to `127.0.0.1` (e.g. 13306, 15682, 184xx), so the pipeline never collides with or touches a dev stack.
- App processes run from the repo's own build outputs. Their generated config, logs and PID files go in `var/marketing/screenshots/tmp/`, which is gitignored.
- `make` **always** tears down, even when a step fails: `$(MAKE) build up seed shoot publish; rc=$$?; $(MAKE) down; exit $$rc`.

### 4. The screenshot manifest is always current
- `var/marketing/screenshots/screenshot-manifest.yaml` is a **well-known path**. Indexers read it to display a project's screenshots, so keep the path and format stable.
- It is **generated, never hand-edited**. Each screenshot's `title`, `description` and `theme` live in its `screenshots.ini` section (repo-helper ignores unknown keys), and `generate-manifest.py` writes the manifest. `make` runs `manifest` straight after `shoot`.
- Adding, renaming or removing a screenshot means editing `screenshots.ini` and re-running `make`, or `make manifest` if only the text changed. The generator fails if a section lacks `title`/`description` or its PNG is missing, so the manifest can't drift.
- `url` is the **absolute raw GitHub URL** of the PNG on the default branch (`https://raw.githubusercontent.com/<owner>/<repo>/<branch>/var/marketing/screenshots/<name>.png`), built from `manifest_base_url` in `[DEFAULT]`. Confirm the owner/repo casing from `git remote get-url origin`. After pushing, check that one URL returns 200.
- Descriptions say **what is shown and why it matters to an end user**, in one or two plain sentences. Reuse them for the README captions.

### 5. The README always shows the current marketing screenshots
Check the README every time the skill runs, not only on first setup:
- **No screenshots.** If no README image points into `var/marketing/screenshots/`, add a `## Screenshots` section straight after the opening "what it does" or intro section.
- **Older or framed screenshots.** Look for images from an earlier approach. These include:
  - images under other screenshot paths (`screenshots/`, `docs/screenshots/`, `.github/`, `var/screenshots/`, `assets/`);
  - framed or mocked-up images (browser or device frames, drop shadows, names like `*-framed.png`, `*frame*`, `*mockup*`);
  - externally hosted images (imgur, user-attachments) that show the UI.
  Replace those README references with the new marketing screenshots. Keep badges, logos and diagrams, which aren't UI screenshots.
- Use one `###` heading per screenshot, the image, and its manifest `description` as the caption, so the README and the manifest say the same thing. Finish with the "regenerated with `make screenshots`" note.
- Don't delete old image files as part of this. List them for the user, and only remove them if the user agrees and nothing else (docs, other READMEs) still references them.
- If the README already uses the marketing screenshots, just make sure every PNG in the manifest appears and the captions match the descriptions.

## Directory layout

```
var/marketing/screenshots/
  Makefile             # all, build, up, seed, shoot, manifest, publish, down, clean
  README.md            # what this is, requirements, `make`, `make up seed` to browse
  screenshots.ini      # repo-helper batch config + title/description/theme per section
  screenshot-manifest.yaml  # GENERATED well-known index for indexers (committed)
  generate-manifest.py # writes the manifest from screenshots.ini (stdlib only)
  <service>.yaml       # configs for the throwaway services (non-default ports)
  mysql-init.sql       # extra DBs/users created at container init (if needed)
  seed.sh              # seeds via the app's public API (curl + jq)
  seed/
    config.json        # settings/cvars to set via the API
    <entities>.json    # fictional records with FIXED ids (stable URLs)
    run-history.sql    # optional: SQL for state the API can't create
  scripts/
    prepare.py         # waits for the SPA to render data
    theme.py, light.py, dark.py   # pin the UI theme for each capture
  *.png                # committed outputs
  tmp/                 # gitignored: configdir, logs, pids
```

Images used by the docs are copied by `make publish` to `docs/content/assets/marketing/`. MkDocs can only serve files inside `docs_dir`; don't use a directory named `screenshots/` there (see the gitignore notes below). The README references `var/marketing/screenshots/*.png` directly.

## Workflow

1. **Explore the app.** Find:
   - how each service starts locally (flags, config dir, env vars);
   - which external dependencies it needs and where it reads their settings (YAML file vs. settings stored in the DB);
   - which readiness signal really means "the DB is ready";
   - the frontend dev server, its API proxy env var, its routes, and its theme mechanism;
   - any existing `.gitignore` rules that match `screenshots/`.
2. **Confirm the tooling.** Check that `command -v repo-helper` works, along with podman or docker, `jq` and `curl`. If `repo-helper` is missing, stop and tell the user.
3. **Write the stack.** Use the Makefile from [reference.md](reference.md), adjusting the services, ports and readiness checks.
4. **Write the seed data.** Seed through the app's **public API** (Connect JSON, REST, MCP) wherever possible, so the seed follows the same code paths as real use. Fall back to SQL inside the DB container (`$(CONTAINER) exec -i … mysql … < seed/x.sql`) only for state the API can't create, such as run history or "last success" timestamps. Comment the SQL as fictional.
5. **Use realistic, healthy-looking state.** Avoid empty tables, red "stale" or "error" badges, and "not connected" banners. Include a small amount of variety, such as one disabled item, but never show something broken unless that is the point of the image.
6. **Write `screenshots.ini`.** Use one section per image, 1280×800 by default, with `script = scripts/light.py, scripts/prepare.py` in `[DEFAULT]`. Put dark variants **last**. Give every section a `title` and `description`, set `theme = dark` on dark variants, and set `manifest_project` and `manifest_base_url` in `[DEFAULT]`.
7. **Run `make`, review every PNG and read `screenshot-manifest.yaml`** with the image viewer or Read tool. Iterate until the images are right.
8. **Publish.** Bring the README up to date following rule 5: add the screenshots if there are none, and replace any older or framed ones. Update the docs pages. Add a root `screenshots:` Makefile target. **Do not** add it to `all`.
9. **Verify:**
   - `make` passes from a clean state;
   - `podman ps` and `pgrep` show nothing left running;
   - `git status -uall` lists the PNGs (the gitignore exception works);
   - the docs build has no missing-image warnings;
   - a second run produces the same images apart from timestamps;
   - `screenshot-manifest.yaml` parses as YAML, lists every PNG, and (once pushed) its URLs return 200.

## Pitfalls (learned the hard way)

| Symptom | Cause / fix |
|---------|-------------|
| Seed fails with 503 right after start | A `/healthz` liveness check passes before the DB is ready. Poll a readiness RPC that touches the DB (e.g. `Health`). |
| Some seed calls fail with "not connected" | That RPC needs a dependency (e.g. AMQP) which the app only connects to *after* settings are seeded. Run those calls later, in a retry loop, after the workers are healthy. |
| A background process dies when its recipe line ends | Start it as `cd dir && { cmd > log 2>&1 & echo $$! > pid; }` and kill it in `down` using the PID file (and `pkill -P` for npm/npx wrappers). |
| Every capture after the dark one is dark | repo-helper reuses **one browser session** for the whole INI, so localStorage carries over between sections. Pin the theme in every section (`light.py` in `[DEFAULT]`, `dark.py` on dark sections). |
| `dark = true` has no effect | PicoCrank's `useTheme` stores the theme in `localStorage['picocrank-theme']`, which wins over `prefers-color-scheme`. Set that key and reload the page. |
| Items show "stale", empty "last success", or red counters | Nothing in the throwaway stack runs that collector or job. Seed fictional run history with SQL, or enable only the items that actually run. |
| PNGs don't appear in `git status` | A rule such as `**/screenshots/` ignores them. Add `!var/marketing/screenshots/` straight after it, and keep `tmp/` ignored. |
| `session not created: ChromeDriver only supports Chrome N` | webdriver_manager resolved an old driver. repo-helper should prefer the system `chromedriver` on PATH; install the distro package that matches the browser. |
| UI shows a connection picker or old controller URLs | The browser profile is fresh, but the API must be same-origin through the dev server proxy. Clear app localStorage keys in `prepare.py` if the app stores any. |

## Reporting back

Tell the user:
- the command to regenerate the images;
- which images exist and where they're used, including that the manifest has been regenerated;
- what changed in the README (screenshots added, or older/framed images replaced), and any old image files that are now unreferenced;
- any data that is synthetic beyond the API seed (e.g. SQL run history);
- any UI bugs the screenshots revealed. Don't silently "fix" the UI to make images look better unless asked.
