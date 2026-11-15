---
name: jwr-soa-theming
description: >-
  Implements PicoCrank theming for jwr SOA apps: color scheme (auto/light/dark)
  via useTheme, named CSS themes via useCustomTheme, system Theme cvars
  (color scheme switcher, theme name, theme control), and user preference
  fields on the User Preferences page. Use when adding themes, color scheme,
  theme switcher, theme name selector, or system vs user theme policy.
---

# jwr-soa-theming

PicoCrank provides two composables:

- **`useTheme`** — color scheme preference (`auto` | `light` | `dark`); persists in browser localStorage (`picocrank-theme`); sets `data-theme` on `<html>`.
- **`useCustomTheme`** — named drop-in CSS themes under `public/themes/<name>/theme.css`; persists theme name in browser localStorage.

**System (app) theme policy** lives in **cvars** ([jwr-soa-settings](../jwr-soa-settings/SKILL.md), category `Theme`). **User overrides** for color scheme and theme name go on the **User Preferences** page ([jwr-soa-iam-profile](../jwr-soa-iam-profile/SKILL.md)).

Companions: [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md), [jwr-soa-settings](../jwr-soa-settings/SKILL.md), [jwr-soa-iam-profile](../jwr-soa-iam-profile/SKILL.md), [jwr-soa-dbmigrations](../jwr-soa-dbmigrations/SKILL.md).

Copy-paste cvars, Vue, and boot wiring: [reference.md](reference.md).

## Principles

1. **Color scheme is client-local** — `useTheme` only; do not store `auto`/`light`/`dark` in the DB or cvars.
2. **Theme name default is a cvar** — admins pick the app default / enforced theme in Settings.
3. **Theme control policy is a cvar** — `system` (force system theme) or `user` (system default, user may override).
4. **Color scheme switcher visibility is a cvar** — not a per-user preference; gates the header color-scheme control.
5. **Apply on boot and after Init/Settings save** — call `applyAppTheming` after `loadInit()` and login so system policy wins when required.
6. **User Preferences fields apply immediately** — color scheme and theme name use `v-model` on the composables; no Save RPC for those (same pattern as legacy `useTheme` on the prefs page).

Do **not** put color scheme in cvars. Do **not** put theme switcher visibility in `user_preferences`. Do **not** bypass `useTheme` / `useCustomTheme` with ad-hoc localStorage keys.

## When to use

- Color scheme preference (Auto / Light / Dark) on User Preferences
- Theme name dropdown on User Preferences or Settings
- Header color scheme switcher enable/disable
- System vs user theme control policy
- Bootstrapping PicoCrank `initCustomTheme` / `discoverThemes`

---

## Architecture

```
cvars (Theme category)
  theme_color_scheme_switcher_enabled ──► Header :themeToggleEnabled
  theme_name ───────────────────────────► default / forced theme name
  theme_control (system | user) ────────► policy

Init.features ──► SPA (theme policy + available theme catalog)

useTheme.theme ─────────────► color scheme (localStorage; User Preferences RadioGroup)
useCustomTheme.themePreference ► theme name (localStorage; User Preferences select)

applyAppTheming(init) on boot / after Settings save:
  system → setTheme(init.themeName); ignore user theme override
  user   → setTheme(userStored || init.themeName)
```

---

## System settings (cvars)

Add to `Defaults()` in category **`Theme`**. Gate Settings edits with `system.settings` ([jwr-soa-settings](../jwr-soa-settings/SKILL.md)).

| Cvar key | Type | UI label | Default | Role |
|----------|------|----------|---------|------|
| `theme_color_scheme_switcher_enabled` | bool | Color scheme switcher | `false` | Show PicoCrank header control for auto/light/dark |
| `theme_name` | string | Theme name | `""` | Active theme when `theme_control=system`; default when `user` |
| `theme_control` | string | Theme control | `user` | `system` or `user` (see below) |

### Theme control

| Value | Label in Settings | Behavior |
|-------|-------------------|----------|
| `system` | System preference | All users get `theme_name` from cvars; user theme name override ignored |
| `user` | User preference | `theme_name` cvar is the default; users may override on User Preferences |

Render **Theme control** as PicoCrank `RadioGroup` `variant="list"` with exactly those two options (not a free-text string field).

Render **Theme name** as a `<select>` populated from `available_themes` (from Init or `discoverThemes()`), plus empty = default Femtocrank-only styling.

Project cvars needed by the shell into `Init.features` (or equivalent): `themeColorSchemeSwitcherEnabled`, `themeName`, `themeControl`, `availableThemes`.

After admin saves Theme settings: `loadInit()` then `applyAppTheming()`.

---

## User Preferences page

On `/user-control-panel/preferences` ([jwr-soa-iam-profile](../jwr-soa-iam-profile/SKILL.md)), add a **Theme** subsection (after Language):

| Field | Label | Control | When shown |
|-------|-------|---------|------------|
| Color scheme preference | Color scheme preference | `RadioGroup` `variant="list"`: Auto / Light / Dark | Always (logged in) |
| Theme name | Theme name | `<select>` of `availableThemes` + default option | Only when `themeControl === 'user'` |

Wire color scheme to `useTheme().theme` (or `setTheme`). Wire theme name to `useCustomTheme().themePreference` (or `setTheme`). Changes apply immediately via composable watchers.

When `themeControl === 'system'`, hide the Theme name field (or show read-only “Set by administrator”). Do not write user theme name to localStorage in system mode.

Color scheme preference is **not** part of the dirty Save button for DB-backed prefs (language only in iam-profile).

---

## Header

```vue
<Header
  :themeToggleEnabled="isLoggedIn && themeColorSchemeSwitcherEnabled"
  …
/>
```

`themeColorSchemeSwitcherEnabled` comes from Init (cvar `theme_color_scheme_switcher_enabled`), not from `user_preferences`.

---

## Boot sequence

In app entry (e.g. `main.js` / `App.vue` `onMounted`):

1. `initCustomTheme({ storageKey: '{app}-custom-theme', … })`
2. `await discoverThemes()` (or use `Init.features.availableThemes`)
3. `await loadInit()` (or reuse cached Init)
4. `applyAppTheming(initFeatures)`

Call again after login and after Settings save.

---

## Implementation checklist

- [ ] Cvars: three Theme keys in `Defaults()`; validate `theme_control` ∈ `{system,user}`; validate `theme_name` against catalog (empty allowed)
- [ ] Init projection for theme flags + `available_themes`
- [ ] Go helper: `AvailableThemeNames()` (scan `frontend/public/themes/` or static list)
- [ ] `applyAppTheming.js`: policy-aware `setTheme` for custom theme + document color scheme stays on `useTheme`
- [ ] Settings: Theme category with bool switcher, theme name `<select>`, theme control RadioGroup list
- [ ] User Preferences: Color scheme preference RadioGroup; Theme name select when user policy
- [ ] Header `:themeToggleEnabled` from Init, not user DB
- [ ] Remove legacy `theme_toggle_enabled` from `user_preferences` if present ([jwr-soa-iam-profile](../jwr-soa-iam-profile/SKILL.md))

---

## Anti-patterns

- Storing color scheme in cvars or `user_preferences`
- Per-user “show theme switcher” in DB (use system cvar)
- Ignoring `theme_control=system` and still applying user localStorage theme name
- Hardcoded theme lists that ignore `themes/index.json` / Init catalog
- Custom CSS theme wiring outside `useCustomTheme`
- Requiring Save on User Preferences to apply color scheme or theme name (use composable `v-model`)
