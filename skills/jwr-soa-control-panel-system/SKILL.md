---
name: jwr-soa-control-panel-system
description: >-
  Implements the privileged System Control Panel for jwr SOA apps: a root
  navigation hub for users with privileges to manage system (app) settings and
  administration, with IAM and Settings as default children when those features
  exist. Use when adding a System Control Panel, admin hub, privileged system
  navigation, nesting IAM or Settings under the system hub, or
  privilege-gated system pages (not the User Control Panel).
---

# jwr-soa-control-panel-system

The **System Control Panel** is the privileged hub for controlling **system (app) settings** and other administration. Access generally depends on **privileges** (RBAC permissions or superuser) — it is not shown to every logged-in user.

It is a **root navigation item**. IAM, Settings, and other privileged pages fall under it.

The only specific items to include as defaults are **IAM** and **Settings**, if they exist and have been implemented.

Companions: [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md), [jwr-soa-iam](../jwr-soa-iam/SKILL.md) (IAM hub and pages), [jwr-soa-settings](../jwr-soa-settings/SKILL.md) (cvars Settings page), [jwr-soa-iam-profile](../jwr-soa-iam-profile/SKILL.md) (self-service User Control Panel — not this).

Copy-paste Vue/router skeletons: [reference.md](reference.md).

## Principles

1. **Privileged system control** — the System Control Panel is for users who have privileges to manage system (app) settings and administration. Hide it from users without the required permissions.
2. **Root navigation item** — System Control Panel is a root sidebar item (its own section). IAM, Settings, etc fall under it. Do not put IAM or Settings as sibling root items. Do not bury the System Control Panel inside another section.
3. **Default children: IAM and Settings only** — include those tiles when the corresponding features exist and have been implemented. Do not treat any other page as a required default of this skill. Apps may add further privileged system pages as extra children.
4. **Hub, then children** — `/control-panel` is a PicoCrank `NavigationGrid` of tiles. Child pages live under that hub (nested routes, breadcrumbs, Back to System Control Panel).
5. **Not the User Control Panel** — header-username self-service (profile, preferences, password, API keys, My Permissions) is [jwr-soa-iam-profile](../jwr-soa-iam-profile/SKILL.md).

Do **not** show an empty System Control Panel. Do **not** mix self-service account pages into this hub.

## When to use

- Adding a System Control Panel / privileged admin / system hub
- Placing IAM or Settings in navigation for privileged users
- Gating system (app) settings and administration in the sidebar
- Distinguishing privileged system nav from the User Control Panel

---

## Architecture

```
GetStatus (rbac_is_superuser, rbac_permissions)
        │
        ├── canAccessControlPanel? ──► sidebar root item "System Control Panel"
        │
        └── /control-panel  (hub)
                 │
                 ├── IAM tile      → /control-panel/iam       (if IAM implemented)
                 ├── Settings tile → /control-panel/settings  (if Settings implemented)
                 └── extra tiles   → other privileged system pages the app adds
```

---

## Navigation

**Sidebar:** a dedicated root section titled “System Control Panel”, containing one link to the hub (`name: 'controlPanel'`). Show that section only when `canAccessControlPanel` is true.

- IAM, Settings, and other system pages are **not** root sidebar items.
- Optional: nested links under the System Control Panel section. Prefer hub tiles if the sidebar is flat.
- Rebuild nav after login/logout/`GetStatus` so the item appears or disappears with privileges.

**Hub:** PicoCrank `Section` titled “System Control Panel”, subtitle along the lines of “System and app settings”, toolbar Refresh, then `Navigation` + `NavigationGrid`. Add a tile only when that child is implemented **and** the user may open it.

**Child pages:** toolbar Back link to `{ name: 'controlPanel' }`. Breadcrumbs: `System Control Panel › {child}`.

---

## Default children

Include a tile only if that feature exists and has been implemented in this app.

| Child | When | Route | Tile if |
|-------|------|-------|---------|
| **IAM** | [jwr-soa-iam](../jwr-soa-iam/SKILL.md) is implemented | `/control-panel/iam` | `canAccessIam` (superuser or any IAM view perm) |
| **Settings** | [jwr-soa-settings](../jwr-soa-settings/SKILL.md) is implemented | `/control-panel/settings` | superuser or `system.settings` |

IAM’s own Users / Groups / Roles pages stay under the IAM hub, not as System Control Panel tiles. Settings is the cvars page for system (app) configuration, not RBAC.

**Extra children:** other privileged system pages may be added as further tiles, nested routes, and breadcrumbs under the System Control Panel. They are not defaults of this skill. Still not root nav items.

---

## Access

Logged in, plus superuser **or** at least one permission that unlocks a System Control Panel child. Mirror Go and `rbacAccess.js`.

```
canAccessControlPanel =
  isLoggedIn && (rbacIsSuperuser || any(childUnlockingPermissions))
```

`childUnlockingPermissions` is the union of permissions for **implemented** children:

- IAM implemented → IAM perms from [jwr-soa-iam](../jwr-soa-iam/SKILL.md) (`users.view`, `usergroups.view`, `rbac.view`, …)
- Settings implemented → `system.settings`
- Extra children → that page’s permission(s)

Unauthorized hub or child routes redirect to `/`. Gate each tile independently so a user who can open Settings but not IAM sees only Settings.

---

## Implementation checklist

- [ ] Route `/control-panel` (`requiresControlPanel`); redirect if `!canAccessControlPanel`
- [ ] Hub: Section + NavigationGrid; tiles only for implemented, permitted children
- [ ] Sidebar: root “System Control Panel” section; hide when unauthorized; not nested in another section
- [ ] If IAM exists: `/control-panel/iam`, IAM tile, breadcrumbs `System Control Panel › IAM`
- [ ] If Settings exists: `/control-panel/settings`, Settings tile, breadcrumbs `System Control Panel › Settings`
- [ ] Child pages: Back to System Control Panel
- [ ] `canAccessControlPanel` / `canAccessIam` in Go and `rbacAccess.js`; union of implemented children
- [ ] Rebuild sidebar after login/status

When adding a **new** privileged system page later: nest it under the System Control Panel (tile + route + breadcrumb + Back). Do not add a new root nav item. Do not add it as a default of this skill.

---

## Anti-patterns

- Showing the System Control Panel to every logged-in user (access requires privileges)
- IAM or Settings as root sidebar items
- Burying the System Control Panel inside another sidebar section
- Requiring extra system pages as System Control Panel defaults (only IAM and Settings are defaults, if implemented)
- Putting User Control Panel / profile / preferences / My Permissions on this hub
- Empty hub (no tiles the user can open)
- Vue-only gates without route meta + server permission checks
