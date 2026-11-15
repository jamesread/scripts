# jwr-marketing-screenshots — reference templates

Replace `<app>`, the service names, ports and routes to fit the project. The examples assume a jwr-soa style app: a Go backend that takes `-configdir` and serves Connect RPC under `/api`, a Vite frontend whose dev server proxies `/api` to an env-var target, and MySQL (+ RabbitMQ when the app uses it).

## Makefile

```make
# Regenerates marketing screenshots against a throwaway stack seeded with
# fictional data. Run `make` here; everything is torn down afterwards.

ROOT := $(abspath ../../..)
HERE := $(abspath .)
TMP := $(HERE)/tmp

CONTAINER ?= podman
MYSQL_CTR := <app>-mkt-mysql
RABBIT_CTR := <app>-mkt-rabbitmq

BACKEND_URL := http://127.0.0.1:18480
FRONTEND_PORT := 18400

DOCS_ASSETS := $(ROOT)/docs/content/assets/marketing
DOCS_IMAGES := home.png list.png details.png settings.png

.PHONY: all build up seed shoot manifest publish down clean

all:
	@$(MAKE) build up seed shoot manifest publish; rc=$$?; $(MAKE) down; exit $$rc

build:
	$(MAKE) -C $(ROOT)/service build
	[ -d $(ROOT)/frontend/node_modules ] || (cd $(ROOT)/frontend && npm ci)

up:
	mkdir -p $(TMP)/service
	cp service.yaml $(TMP)/service/config.yaml
	# Only if the app finds migrations relative to its config dir:
	ln -sfn $(ROOT)/service/migrations $(TMP)/service/migrations
	$(CONTAINER) run -d --rm --name $(MYSQL_CTR) -p 127.0.0.1:13306:3306 \
		-e MYSQL_ROOT_PASSWORD=root-demo -e MYSQL_DATABASE=<app> \
		-e MYSQL_USER=<app> -e MYSQL_PASSWORD=<app>-demo \
		-v $(HERE)/mysql-init.sql:/docker-entrypoint-initdb.d/init.sql:ro,Z \
		docker.io/library/mysql:8.4
	$(CONTAINER) run -d --rm --name $(RABBIT_CTR) -p 127.0.0.1:15682:5672 \
		docker.io/library/rabbitmq:4-alpine
	@echo "Waiting for MySQL..."
	@for i in $$(seq 120); do \
		$(CONTAINER) exec $(MYSQL_CTR) mysql -u<app> -p<app>-demo -h127.0.0.1 -e 'SELECT 1' <app> >/dev/null 2>&1 && exit 0; \
		sleep 1; done; echo "MySQL did not start"; exit 1
	@echo "Waiting for RabbitMQ..."
	@for i in $$(seq 120); do \
		$(CONTAINER) exec $(RABBIT_CTR) rabbitmq-diagnostics -q check_port_connectivity >/dev/null 2>&1 && exit 0; \
		sleep 1; done; echo "RabbitMQ did not start"; exit 1
	cd $(TMP)/service && { $(ROOT)/service/<app> -configdir . > $(TMP)/service.log 2>&1 & echo $$! > $(TMP)/service.pid; }
	# Poll a readiness RPC that touches the DB, not just /healthz.
	@for i in $$(seq 60); do curl -fsS -X POST -H 'Content-Type: application/json' -d '{}' \
		$(BACKEND_URL)/api/<pkg>.v1.<Service>/Health >/dev/null 2>&1 && exit 0; sleep 1; done; \
		echo "Backend did not become healthy; see $(TMP)/service.log"; exit 1

seed:
	./seed.sh $(BACKEND_URL)
	# Start workers here if the app has any (same background + pid pattern).
	cd $(ROOT)/frontend && { <PROXY_ENV>=$(BACKEND_URL) npx vite --host 127.0.0.1 --port $(FRONTEND_PORT) --strictPort > $(TMP)/frontend.log 2>&1 & echo $$! > $(TMP)/frontend.pid; }
	# Optional: SQL for state the API can't create (fictional run history, etc.)
	$(CONTAINER) exec -i $(MYSQL_CTR) mysql -u<app> -p<app>-demo <app> < seed/run-history.sql
	@for i in $$(seq 60); do curl -fsS http://127.0.0.1:$(FRONTEND_PORT)/ >/dev/null 2>&1 && break; sleep 1; done
	sleep 5

shoot:
	repo-helper screenshot --config screenshots.ini

manifest:
	./generate-manifest.py

publish:
	mkdir -p $(DOCS_ASSETS)
	cp $(DOCS_IMAGES) $(DOCS_ASSETS)/

down:
	-@for p in frontend service; do \
		[ -f $(TMP)/$$p.pid ] && pkill -P $$(cat $(TMP)/$$p.pid) 2>/dev/null; \
		[ -f $(TMP)/$$p.pid ] && kill $$(cat $(TMP)/$$p.pid) 2>/dev/null; \
		rm -f $(TMP)/$$p.pid; done
	-@$(CONTAINER) rm -f $(MYSQL_CTR) $(RABBIT_CTR) >/dev/null 2>&1

clean: down
	rm -rf $(TMP)
```

If a seed call needs a dependency that only connects after the settings exist (e.g. "enqueue a job" needs AMQP), retry it after the workers are up:

```make
	@for i in $$(seq 30); do curl -fsS -X POST -H 'Content-Type: application/json' -d '{"id":"demo-1"}' \
		$(BACKEND_URL)/api/<pkg>.v1.<Service>/RunNow >/dev/null 2>&1 && break; sleep 1; done
```

## seed.sh

```bash
#!/usr/bin/env bash
# Seeds the throwaway backend with fictional settings and records via its
# public API (Connect JSON). Usage: seed.sh <backend-base-url>
set -euo pipefail

base="${1:?backend base url}"
here="$(cd "$(dirname "$0")" && pwd)"
api="$base/api/<pkg>.v1.<Service>"

rpc() {
	curl -fsS -X POST -H 'Content-Type: application/json' -d "$2" "$api/$1" >/dev/null
}

jq -c 'to_entries[] | {key, value}' "$here/seed/config.json" | while read -r kv; do
	rpc SetConfig "$kv"
done

jq -c '.[]' "$here/seed/items.json" | while read -r item; do
	rpc UpsertItem "{\"item\": $item}"
done
```

`seed/items.json`: fixed IDs give stable URLs (e.g. `items/demo-widgets`), and every value is obviously fictional:

```json
[
  {"id": "demo-widgets", "name": "Widgets", "source": "https://example.com/feed.xml", "enabled": true},
  {"id": "demo-gadgets", "name": "Gadgets", "source": "repo:example-org/gadgets", "enabled": false}
]
```

`seed/run-history.sql`:

```sql
-- Fictional run history so list pages show a healthy state.
SET @now = UNIX_TIMESTAMP() * 1000;
UPDATE items SET last_success_unix_ms = @now - 60000 WHERE id = 'demo-widgets';
```

## screenshots.ini

```ini
# Marketing screenshots, captured by `make` in this directory against the
# throwaway stack it starts (see Makefile / seed/).
#
# title/description/theme are not used by repo-helper; `make manifest` turns
# them into screenshot-manifest.yaml for indexers. Every section needs them.

[DEFAULT]
base_url = http://127.0.0.1:18400/
dir = .
width = 1280
height = 800
script = scripts/light.py, scripts/prepare.py
post_script_sleep = 1.5
theme = light
manifest_project = <App>
manifest_base_url = https://raw.githubusercontent.com/<owner>/<repo>/main/var/marketing/screenshots/

[home]
url = .
title = Home
description = What the page shows, and why it is useful to an end user, in one or two sentences.

[list]
url = items
title = Items
description = ...

[details]
url = items/demo-widgets
title = Item details
description = ...

# Dark variants last; the browser session (and localStorage) is shared.
[home-dark]
url = .
script = scripts/dark.py, scripts/prepare.py
theme = dark
title = Dark mode
description = ...
```

## screenshot-manifest.yaml (generated, well-known path)

Commit this file and never edit it by hand. Its format:

```yaml
# Generated by `make manifest` from screenshots.ini. Do not edit by hand.
version: 1
project: "<App>"
screenshots:
  - name: "home"
    title: "Home"
    description: "What the page shows, and why it is useful to an end user."
    url: "https://raw.githubusercontent.com/<owner>/<repo>/main/var/marketing/screenshots/home.png"
    file: "home.png"
    width: 1280
    height: 800
    theme: "light"
```

`width`/`height` are read from the PNG itself, so crop settings are reflected.

## generate-manifest.py

Standard library only; `chmod +x` it.

```python
#!/usr/bin/env python3
"""Writes screenshot-manifest.yaml from screenshots.ini for indexers.

Each INI section with url= is one screenshot; it must have title= and
description=, and its PNG must exist. Run via `make manifest`.
"""
import configparser
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INI = HERE / "screenshots.ini"
OUT = HERE / "screenshot-manifest.yaml"


def png_size(path):
    with open(path, "rb") as f:
        header = f.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("%s is not a PNG" % path)
    return struct.unpack(">II", header[16:24])


def q(value):
    # JSON strings are valid YAML scalars and handle all quoting/escaping.
    return json.dumps(value, ensure_ascii=False)


def main():
    cp = configparser.ConfigParser(interpolation=None)
    cp.read(INI)
    defaults = cp.defaults()
    base_url = defaults["manifest_base_url"].rstrip("/") + "/"
    errors = []
    lines = [
        "# Generated by `make manifest` from screenshots.ini. Do not edit by hand.",
        "version: 1",
        "project: %s" % q(defaults["manifest_project"]),
        "screenshots:",
    ]
    for section in cp.sections():
        if not cp.get(section, "url", fallback="").strip():
            continue
        name = cp.get(section, "name", fallback=section).strip() or section
        file = "%s.png" % name
        title = cp.get(section, "title", fallback="").strip()
        description = cp.get(section, "description", fallback="").strip()
        if not title or not description:
            errors.append("[%s] needs title= and description=" % section)
            continue
        if not (HERE / file).is_file():
            errors.append("[%s] %s is missing; run `make` first" % (section, file))
            continue
        width, height = png_size(HERE / file)
        lines += [
            "  - name: %s" % q(name),
            "    title: %s" % q(title),
            "    description: %s" % q(description),
            "    url: %s" % q(base_url + file),
            "    file: %s" % q(file),
            "    width: %d" % width,
            "    height: %d" % height,
            "    theme: %s" % q(cp.get(section, "theme", fallback="light").strip()),
        ]
    if errors:
        sys.exit("\n".join(errors))
    OUT.write_text("\n".join(lines) + "\n")
    print("Wrote %s" % OUT.name)


if __name__ == "__main__":
    main()
```

## scripts/prepare.py

```python
"""Waits for the SPA to connect and render data before capture."""
import time

from selenium.webdriver.common.by import By


def run(driver):
    deadline = time.time() + 15
    while time.time() < deadline:
        if driver.find_elements(By.CSS_SELECTOR, "main tbody tr, main li, main dl, main form"):
            break
        time.sleep(0.25)
    driver.execute_script("window.scrollTo(0, 0);")
```

## scripts/theme.py, light.py, dark.py (PicoCrank)

```python
# theme.py
"""Pins the picocrank theme; the browser session is shared across captures."""
import time


def set_theme(driver, theme):
    current = driver.execute_script("return localStorage.getItem('picocrank-theme');")
    if current == theme:
        return
    driver.execute_script("localStorage.setItem('picocrank-theme', arguments[0]); location.reload();", theme)
    time.sleep(3)
```

```python
# light.py (dark.py is identical with "dark")
"""Forces the light theme before capture."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from theme import set_theme  # noqa: E402


def run(driver):
    set_theme(driver, "light")
```

## .gitignore

If the repo ignores `**/screenshots/` (common for Selenium artifacts), add an exception straight after it:

```gitignore
**/screenshots/
!var/marketing/screenshots/
```

`var/marketing/screenshots/tmp/` must stay ignored (`**/tmp/` or an explicit rule).

## Root Makefile

```make
screenshots:
	$(MAKE) -wC var/marketing/screenshots
```

Add it to `.PHONY`. Do **not** make it part of `all`, because it needs containers and a browser.

## README snippet

Captions are the manifest `description` for each screenshot.

```markdown
## Screenshots

### <Title from screenshots.ini>

![<Title>](var/marketing/screenshots/home.png)

<Description from screenshots.ini: what is shown, and why it matters to an end user.>

### <Next title>

![<Next title>](var/marketing/screenshots/list.png)

<Description.>

Screenshots use fictional test data and are regenerated with `make screenshots`
(see [`var/marketing/screenshots`](var/marketing/screenshots/README.md)).
```

To find README images that need replacing (none, older, or framed):

```bash
grep -nE '!\[|<img' README.md | grep -v 'var/marketing/screenshots/'
```

Review each match by hand. Badges, logos and diagrams stay; UI screenshots from other paths, framed/mockup images, and externally hosted UI images get replaced.

Docs pages reference `assets/marketing/<name>.png`, relative to `docs/content/`.
