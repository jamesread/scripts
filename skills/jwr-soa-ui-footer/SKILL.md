---
name: jwr-soa-ui-footer
description: >-
  Implements the standard SPA page footer for jwr SOA apps: femtocrank/PicoCrank
  layout, visibility and version/update/theme details from Init RPC, brand row
  plus link chips. Use when adding or aligning a footer, showFooter,
  currentVersion, availableVersion, showNewVersions, version display policy, or
  when matching OliveTin-style footer UI.
---

# jwr-soa-ui-footer

The page footer sits under `<main>` inside `#content`. **Most of what it shows comes from the `Init` API response** — do not hardcode version strings, visibility, or update-available state in the Vue tree.

Reference implementation: **OliveTin** (`frontend/resources/vue/App.vue` footer block, `Init` in `service/internal/api/api.go`, femtocrank `footer` / `footer span` styles).

Companions: [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md) (Vue + PicoCrank + Connect), [jwr-soa-settings](../jwr-soa-settings/SKILL.md) (optional `show_footer` / related cvars projected via Init).

Copy-paste proto + Vue skeleton: [reference.md](reference.md).

## Principles

1. **Init owns footer state** — visibility, current version, newer-version hint, and any policy that hides the version number are fields on `InitResponse` (or nested policy). The SPA only renders them.
2. **Layout shell, not a card** — footer is a plain `<footer>` in the PicoCrank/`#content` column; style comes from **femtocrank** (`footer`, `footer span`). Avoid inventing a custom footer design system.
3. **Three rows (optional)** — (1) brand + version, (2) link chips (`footer span`), (3) “new version available” when Init says so.
4. **Policy can redact version** — if Init policy says not to show the version number, omit version text **and** the update link; server should also clear version fields when redacting.
5. **Static product URLs may be hardcoded** — docs / GitHub / issue tracker links are app constants unless the app already exposes them via Init (e.g. `additional_links`). Prefer Init when admins can configure them.
6. **Extract a component** — prefer `AppFooter.vue` (or PicoCrank-equivalent) fed from `useInit` / `initResponse`, not a one-off inline block forever.

## When to use

- Adding a footer to a new or existing jwr SOA SPA
- Wiring `showFooter`, version display, or update-check UI to Init
- Aligning Faridoon / DataPipes / Japella / IceHive-style footers with the OliveTin pattern
- Hiding the footer for screenshots / minimal UI (`showFooter: false`)

Do **not** use this for action-button footers, modal dialog footers, or marketing-site page footers outside the SPA shell.

---

## Architecture

```
Config / buildinfo / update-check / ACL policy
                    │
                    ▼
              Init RPC ──► InitResponse footer fields
                    │
                    ▼
         useInit / window.initResponse
                    │
                    ▼
   #content → <main>…</main> → <footer v-if="showFooter">…</footer>
                    │
                    ▼
         femtocrank footer / footer span styles
```

Place the footer **inside** `#content`, after `<main>`, so the flex column keeps the footer at the bottom of the content pane (not the sidebar).

---

## Init contract (footer fields)

Expose these on `InitResponse` (names may be camelCase in generated TS):

| Field | Role |
|-------|------|
| `show_footer` | Master visibility; default `true` |
| `current_version` | Installed version string for the brand row |
| `show_new_versions` | Whether to offer an update hint |
| `available_version` | Newer version id/label when an update exists; empty / sentinel when none |
| `show_version_number` | Or nest under `effective_policy` — hide version + update UI when false |
| `available_themes` | Optional; theme chip only if length > 1 |
| `page_title` / site title | Optional brand label if not hardcoded |

Server rules:

- When version display is denied by policy, set `current_version` and `available_version` to empty (and `show_new_versions` false) so the client cannot leak them.
- Populate `available_version` from the app’s update-check path only when `show_new_versions` is enabled and a newer build exists.
- Default `show_footer` to `true` in config/cvars.

App-only Init extras (language list, OAuth, nav) are fine; keep **footer-specific** fields stable so other apps can copy the same shape.

---

## UI structure

OliveTin-shaped footer (adapt product name, logo, and links):

1. **Brand row** — small logo (optional) + product name + `current_version` when allowed.
2. **Links row** — each item in a `<span>` (femtocrank chips): docs, issues/GitHub, optional language, optional theme.
3. **Update row** — link/text for `available_version` when `show_new_versions` and a real newer version is present; hide otherwise (`hidden` attribute or `v-if`).

Language / theme pickers are optional: only include them when the app has i18n or theme discovery on Init. Wire click handlers to existing dialogs; do not invent heavy footer chrome.

Integration tests: assert `footer` absent when Init/`showFooter` is false; assert version text present/absent per policy.

---

## Styling

- Rely on **femtocrank** `footer` (centered, padded) and `footer span` (chip background, spacing).
- Dark theme: PicoCrank dark theme already targets `footer a` / `footer span`.
- Optional style mod: transparent chip backgrounds (OliveTin `sm-transparent-footer`) — only if the app supports style mods.
- Prefer **no** scoped redesign of the footer; match the shell.

---

## Checklist

- [ ] `InitResponse` includes footer fields above; server redacts version when policy denies
- [ ] SPA reads footer state only from Init (after load / reload Init)
- [ ] `<footer>` under `#content`, after `<main>`, gated by `show_footer`
- [ ] Brand row + version; link chips; optional update link
- [ ] No custom card/shadow footer layout — femtocrank chips
- [ ] Test: footer hidden when disabled; version hidden when policy says so

## Additional resources

- Templates and Vue skeleton: [reference.md](reference.md)
