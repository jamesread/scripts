---
name: jwr-repohelper-screenshots
description: >-
  Capture headless Chrome UI screenshots with `repo-helper screenshot` — single
  URL, batch `screenshots.ini`, or Python/JS setup scripts to reach a precise
  UI state before capture. Use when updating README screenshots, visual docs,
  marketing assets, or jwr-repohelper-screenshots.
---

# jwr-repohelper-screenshots

Capture PNG screenshots via the locally installed `repo-helper screenshot` command (headless Chrome + Selenium).

## Prerequisites

1. Verify the tool exists:

```bash
command -v repo-helper
```

If this fails, tell the user `repo-helper` is not installed or not on `PATH`, and **stop**. Do not substitute other screenshot tools.

2. Ensure the target app is **running and reachable** at the URL before capturing (local dev server, staging, etc.).

3. Chrome/Chromium and a matching driver must be available (the tool uses Selenium; `webdriver_manager` may auto-install the driver).

## Invocation modes

### Single capture (NAME + URL)

```bash
repo-helper screenshot <name> <url> [options]
```

- `name` — output filename stem (`<name>.png`)
- `url` — `http(s)://…`, hostname, absolute `/path`, or relative path to an existing file (mapped to `http://127.0.0.1/…`)

Common options:

| Flag | Purpose |
|------|---------|
| `--width`, `--height` | Viewport (default 1024×768) |
| `--croptop`, `--cropbottom`, `--cropleft`, `--cropright` | Crop pixels after capture (e.g. hide sidebar) |
| `--dark` | Prefer dark color scheme |
| `--script PATH` | Python setup script (repeatable) |
| `--exec-js CODE` | Inline JS in page context (repeatable) |
| `--script-js PATH` | `.js` file executed in page (repeatable) |
| `--post-script-sleep SECS` | Wait after scripts before capture (default 0.5) |

Example:

```bash
repo-helper screenshot home http://localhost:8080/ --width 1280 --height 800 --dark
```

### Batch capture (`screenshots.ini`)

When `./screenshots.ini` exists in the repo root, running with no arguments processes all sections:

```bash
repo-helper screenshot
```

Or specify a config path:

```bash
repo-helper screenshot --config path/to/screenshots.ini
```

**Do not** pass NAME/URL with `--config`.

Example `screenshots.ini`:

```ini
[DEFAULT]
base_url = http://localhost:8080/
dir = screenshots
width = 1280
height = 800
post_script_sleep = 0.5

[home]
url = .
name = home

[settings]
url = /settings
script = scripts/screenshot-open-settings.py
cropleft = 240
dark = true
```

- `[DEFAULT]` keys inherit into every section.
- Each section **with** `url=` is one capture; sections without `url=` are skipped.
- Relative `url` values join to `base_url` (trailing slash on `base_url` matters).
- `dir` — output folder (relative to INI directory unless absolute); default is cwd or `SCREENSHOT_DIR`.
- `script`, `script_js` — comma-separated paths relative to the INI directory.

## Capture pipeline (order matters)

Understanding this sequence is essential when writing setup scripts:

1. Browser opens; viewport set to `--width` / `--height`
2. Page navigates to URL
3. **Fixed 3 s wait** (initial load / hydration)
4. **Setup scripts run** (see below)
5. **`post_script_sleep`** (default 0.5 s)
6. PNG saved as `<name>.png`
7. Optional crop applied

Plan scripts for step 4; use `post_script_sleep` or `time.sleep()` inside Python when the UI needs extra time after interactions.

## Setup scripts — reaching a precise UI state

Use scripts when a bare page load does not show the desired state (modals dismissed, tab selected, form filled, lazy content loaded, scroll position, etc.).

### Python (`--script` / INI `script=`)

Each file **must** define:

```python
def run(driver):
    """Called with the live Selenium WebDriver after page load."""
    ...
```

- Runs in the **runner process** (full Python + Selenium API).
- Repeat `--script` to chain multiple files in order.
- Use for: clicks, waits, `time.sleep`, `WebDriverWait`, form input, multi-step flows.

Example — load lazy content, dismiss cookie banner, open a panel:

```python
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def run(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.5)
    driver.execute_script("window.scrollTo(0, 0);")

    try:
        btn = driver.find_element(By.CSS_SELECTOR, "button.accept-cookies")
        btn.click()
        time.sleep(0.3)
    except Exception:
        pass

    tab = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='settings-tab']"))
    )
    tab.click()
    time.sleep(0.2)
```

CLI:

```bash
repo-helper screenshot settings http://localhost:8080/app \
  --script scripts/screenshot-open-settings.py \
  --post-script-sleep 1
```

### JavaScript in page context

**`--exec-js`** — one-liners, repeatable:

```bash
repo-helper screenshot scrolled http://localhost:8080/ \
  --exec-js "document.querySelector('#main').scrollTop = 400"
```

**`--script-js`** — load a `.js` file into the page (repeatable). Good for scroll/visibility tweaks without Python.

```javascript
// scripts/focus-panel.js
document.querySelector('[data-panel="billing"]').classList.add('open');
document.querySelector('#billing-section').scrollIntoView({ block: 'start' });
```

INI equivalent:

```ini
[checkout]
url = /checkout
script_js = scripts/focus-panel.js
exec_js = localStorage.setItem('onboarding', 'done'); location.reload();
post_script_sleep = 1.5
```

**Limitation:** JS snippets cannot call `time.sleep`; use `--post-script-sleep` or a Python `--script` for delays between steps.

### Script execution order

For each capture, scripts run in this order:

1. All `--script` Python files (in order given)
2. All `--exec-js` snippets (in order)
3. All `--script-js` files (in order)

Then `post_script_sleep`, then screenshot.

## Workflow for the agent

1. Confirm `repo-helper` is on `PATH`; confirm app URL is up.
2. Choose mode: one-off NAME/URL vs maintain `screenshots.ini` for recurring README assets.
3. If the default view is wrong, **author or update a setup script** rather than asking the user to manually stage the UI.
4. Run the command from the directory where relative script paths and `screenshots.ini` resolve correctly.
5. Report output paths (`Saved screenshot as: …`) and verify PNGs exist.
6. For README updates, prefer a committed `screenshots.ini` + `scripts/` so captures are reproducible.

## Troubleshooting

| Issue | Action |
|-------|--------|
| Connection refused | Start dev server; check `base_url` / port |
| Blank or loading UI | Increase `--post-script-sleep`; add waits in Python script |
| Wrong theme | Add `--dark` or set `dark = true` in INI |
| Sidebar/chrome in frame | Use `--cropleft` / crop keys in INI |
| Script not found | Paths in INI are relative to the INI file; CLI paths relative to cwd |
| `must define run(driver)` | Python script missing `run(driver)` function |
