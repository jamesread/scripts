---
name: jwr-soa-iam-profile
description: >-
  Implements the self-service user profile (User Control Panel) and per-user
  preferences for jwr SOA apps: PicoCrank Header username click, profile hub
  with identity/logout/quick actions, DB-backed language preference. Theme
  fields on User Preferences are defined in jwr-soa-theming. Use when adding
  a user profile page, account page, User Control Panel, user preferences,
  header username, ChangePassword, or per-user settings (not admin cvars).
---

# jwr-soa-iam-profile

The **logged-in username** appears in the PicoCrank `Header`. Clicking it opens the **profile hub** (User Control Panel): identity, quick actions (preferences, password, API keys, My Permissions), and sign-out.

**Per-user preferences** live in `user_preferences` (not admin cvars). **Theming** (color scheme, theme name) is defined in [jwr-soa-theming](../jwr-soa-theming/SKILL.md).

Companions: [jwr-soa-iam](../jwr-soa-iam/SKILL.md) (login, sessions, API keys, My Permissions), [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md), [jwr-soa-settings](../jwr-soa-settings/SKILL.md) (site-wide cvars — not this), [jwr-soa-theming](../jwr-soa-theming/SKILL.md), [jwr-soa-control-panel-system](../jwr-soa-control-panel-system/SKILL.md) (privileged System Control Panel — not this), [jwr-soa-dbmigrations](../jwr-soa-dbmigrations/SKILL.md).

Copy-paste schemas and Vue: [reference.md](reference.md).

## Principles

1. **Header username is the entry** — pass `username` from `GetStatus` only when logged in; click → profile hub. Guests see no username.
2. **Self-service only** — profile and preferences act on the **authenticated user**. This is not `/users/:id` admin details.
3. **Hub + child routes** — identity and logout on the hub; preferences, password, API keys, My Permissions are separate pages reached from a PicoCrank `NavigationGrid`.
4. **Language in the DB** — `language` upserts per user. Theme fields on the same page follow [jwr-soa-theming](../jwr-soa-theming/SKILL.md) (client composables + system cvars).
5. **Defaults when no row** — `GetUserPreferences` returns language `""` (browser default).
6. **`app.access`** — Get/Save preferences, change password, and the profile page need no extra RBAC perm. Apply language immediately after login via `loadAndApplyUserPreferences`.

Do **not** put per-user prefs in cvars. Do **not** use the admin Users page as the profile. Do **not** put this hub under the privileged System Control Panel.

## When to use

- Header username display and click-through to an account page
- User Control Panel / profile / My Account
- Language preference (Save to DB)
- Change password and sign-out from the account hub

For color scheme, theme name, or header theme switcher policy, use [jwr-soa-theming](../jwr-soa-theming/SKILL.md).

---

## Architecture

```
GetStatus.username ──► Header :username ──@userClick──► /user-control-panel
                                                              │
                         identity dl  ◄── GetStatus (username; optional email/dates)
                         NavigationGrid → preferences, password, API keys, My Permissions
                         Sign Out → Logout RPC, invalidate status, / + reload

user_preferences (DB) ◄── GetUserPreferences / SaveUserPreferences
        │
        └── language → vue-i18n locale (empty = fallback)

User Preferences theme fields ──► jwr-soa-theming (useTheme, useCustomTheme)
Header :themeToggleEnabled ─────► jwr-soa-theming (system cvar)
```

---

## Header contract

PicoCrank `Header`:

```vue
<Header
  :username="isLoggedIn ? username : ''"
  :themeToggleEnabled="isLoggedIn && themeColorSchemeSwitcherEnabled"
  @userClick="goToUserControlPanel"
/>
```

`themeColorSchemeSwitcherEnabled` comes from Init / system cvars ([jwr-soa-theming](../jwr-soa-theming/SKILL.md)), not from `user_preferences`.

`goToUserControlPanel` → `router.push({ name: 'userControlPanel' })`.

If the installed PicoCrank `Header` does not emit `userClick`, put a clickable username in `#user-info` that routes the same way. Do not leave the username as inert text.

After login, `applyAuthFromStatus` sets `username` from `GetStatus` and calls `loadAndApplyUserPreferences`. Register language appliers in `App` `onMounted` so preference saves update the shell without a full reload.

---

## Profile hub

**Route:** `/user-control-panel` (`requiresAuth: true`). Title “User Control Panel” (or “Account”).

Three PicoCrank `Section`s:

1. **Identity** — toolbar Refresh. Avatar + username heading. `<dl>`: Username, Email (or “Not provided”), Account created, Last login. Source: `GetStatus` (add `email`, `created_at`, `last_login_at` if the app stores them; otherwise omit those rows rather than showing fake “Unknown”).
2. **Quick actions** — `Navigation` + `NavigationGrid`. Tiles (all `app.access` self-service):
   - User Preferences → `/user-control-panel/preferences`
   - Change Password → `/change-password`
   - API Keys → `/api-keys` ([jwr-soa-iam](../jwr-soa-iam/SKILL.md))
   - My Permissions → `/user-control-panel/permissions` ([jwr-soa-iam](../jwr-soa-iam/SKILL.md))
   - Optional: browser diagnostics
3. **Session** — Sign Out (`class="bad"`). `Logout` RPC → `invalidateAppStatus()` → `router.push('/')` → `window.location.reload()`.

Child pages use a Back toolbar link to `{ name: 'userControlPanel' }`.

This is **not** the admin user editor. Admins change other users under `/users`.

---

## Preferences

**Route:** `/user-control-panel/preferences`. `Section` + `FormLayout` + dirty Save.

| Pref | Storage | UI | Default |
|------|---------|-----|---------|
| Language | DB `language` | `<select>`: empty = “Browser default”, plus `available_languages` from Get | `""` |

Add theme fields from [jwr-soa-theming](../jwr-soa-theming/SKILL.md) on the same page (Color scheme preference, Theme name when user policy). Those apply immediately via PicoCrank composables — not part of dirty Save.

Save **disabled until dirty** (language only). After a successful save, call `applyUserLanguage`.

`GetUserPreferences` always returns `available_languages` from the server i18n catalog. `SaveUserPreferences` rejects unknown codes; **empty language is allowed** (browser default).

Missing row: return the defaults above, do not 404.

---

## Protocol

Gate with `app.access` (authenticated self):

| RPC | Role |
|-----|------|
| `GetUserPreferences` | Current user’s language pref + language catalog |
| `SaveUserPreferences` | Upsert language for **caller only** |
| `ChangePassword` | Current + new (min 8); verify current hash |
| `Logout` | Delete session, clear `{app}-sid` |

Never accept a `user_id` on Save preferences. ChangePassword is not `users.reset-password` (that is admin reset of someone else).

---

## Implementation checklist

- [ ] Migration: `user_preferences` unique on `user_account_id`; FK CASCADE to `user_accounts`
- [ ] Store: Get (defaults if missing), Save upsert
- [ ] Proto: Get/Save preferences; optional GetStatus identity fields for the hub
- [ ] Header: username when logged in; click → profile hub
- [ ] `userPreferences.js`: language applier + `loadAndApplyUserPreferences` after login
- [ ] Profile hub: identity, NavigationGrid, logout
- [ ] Preferences page: language FormField + dirty Save; theme fields from [jwr-soa-theming](../jwr-soa-theming/SKILL.md)
- [ ] Change password page; Back links to the hub
- [ ] Routes `requiresAuth`; i18n empty string = fallback

When adding a **new per-user pref** later: column + proto fields + Get/Save + FormField. Do not add it to admin cvars.

---

## Anti-patterns

- Storing per-user language in cvars ([jwr-soa-settings](../jwr-soa-settings/SKILL.md) is site-wide)
- Storing theme switcher visibility or theme policy in `user_preferences` ([jwr-soa-theming](../jwr-soa-theming/SKILL.md))
- Opening `/users/:id` when the header username is clicked
- `user_id` on SaveUserPreferences (always the authenticated user)
- 404 when no preferences row exists
- Rejecting empty language (browser default)
- Hardcoded language `<option>`s that ignore `available_languages`
