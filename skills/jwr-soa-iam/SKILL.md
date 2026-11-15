---
name: jwr-soa-iam
description: >-
  Implements HTTP authentication (httpauthshim) and IAM for jwr SOA apps:
  DB users, sessions, API keys, user groups, RBAC roles/permissions,
  SUPERUSER, Connect procedure gates, PicoCrank Login form, and IAM UI
  (users, groups, roles, My Permissions). Use when adding login, Login.vue,
  auth, RBAC, IAM, usergroups, roles, permissions, SUPERUSER, API keys,
  impersonation, or httpauthshim.
---

# jwr-soa-iam

Identity lives in **`user_accounts`**. Access is **group-based RBAC**: users belong to groups, groups have roles, roles have permissions. The `superuser` role grants every permission. HTTP auth is **`github.com/jamesread/httpauthshim`** plus app-owned session cookies and Bearer API keys.

Companions: [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md), [jwr-soa-dbmigrations](../jwr-soa-dbmigrations/SKILL.md), [jwr-datatable](../jwr-datatable/SKILL.md), [jwr-soa-settings](../jwr-soa-settings/SKILL.md), [jwr-soa-control-panel-system](../jwr-soa-control-panel-system/SKILL.md) (privileged System Control Panel hub; IAM is a child), [jwr-soa-iam-profile](../jwr-soa-iam-profile/SKILL.md) (header username, profile hub, per-user preferences), [jwr-soa-ai](../jwr-soa-ai/SKILL.md) (optional Bearer MCP).

Copy-paste schemas and skeletons: [reference.md](reference.md).

## Principles

1. **Roles never attach to users** — only to groups. Users inherit the union of roles from every group they belong to.
2. **`superuser` short-circuits** — `Has(p)` is true for every permission; do not edit its permission set.
3. **Catalog in two places** — permission *names* are Go constants that **must match** `rbac_permissions.name`. Seed and extend via SQL migrations.
4. **Procedure map + handler checks** — Connect middleware maps procedure → required permission (default `app.access`). UI gates are not sufficient.
5. **App owns sessions** — httpauthshim disk session storage is a no-op; `{app}-sid` cookies and `api_keys` live in the DB.
6. **Never leave zero superusers** — membership and group-role writes must refuse if no user would retain `superuser` via groups.
7. **SPA status is the IAM source** — `GetStatus` returns `rbac_permissions` and `rbac_is_superuser`; frontend helpers must match Go.

Do **not** tick permissions on a user. Apps may attach extra resource-sharing tables to `user_groups`; that is outside this skill.

## When to use

- Adding login, sessions, API keys, or httpauthshim providers
- Introducing IAM: users, groups, roles, permissions, SUPERUSER
- Gating Connect RPCs and Vue routes/nav by permission
- Porting this IAM model into another jwr SOA app

---

## Architecture

```
config.yaml auth: ──► httpauthshim (JWT / headers / mTLS)
api_keys Bearer  ──► custom provider ─┐
{app}-sid cookie ──► custom provider ─┴─► username → user_accounts
                                              │
                              LoadEffectiveRBAC (groups → roles → perms)
                                              │
RequiredPermission(procedure) ── default app.access; else Forbidden
                                              │
GetStatus → rbac_permissions[], rbac_is_superuser ──► SPA (rbacAccess.js)
                                              │
IAM UI: Users / Groups / Roles / Permissions / My Permissions
```

---

## Data model

| Table | Role |
|-------|------|
| `user_accounts` | Username, password hash, `created_by` |
| `sessions` | `sid` unique, FK user; optional `impersonator_user_id` |
| `api_keys` | Bearer secret, FK user, unique key, last-used |
| `user_groups` | Named groups; system: `Everyone`, `Administrators` |
| `user_group_memberships` | Unique `(user_account_id, user_group_id)` |
| `rbac_permissions` | Catalog (`name` unique, description) |
| `rbac_roles` | Named roles; system: `superuser`, `member` |
| `rbac_role_permissions` | Role ↔ permission |
| `rbac_group_roles` | Group ↔ role (**the only role assignment**) |

There is **no** `rbac_user_roles` table. `GetUserRbacRoles` is effective (via groups), read-only.

### System seeds

| Entity | Name | Rules |
|--------|------|--------|
| Group | `Everyone` | Undeletable. Has role `member`. Every user is a member. |
| Group | `Administrators` | Undeletable. Has role `superuser`. |
| Role | `superuser` | All access. Cannot rename, delete, or change permissions. |
| Role | `member` | `app.access` only. Cannot rename or delete. |

Bootstrap after migrations / first user:

1. Ensure both system groups and their role links.
2. If no user has `superuser` via groups, add the first `user_accounts` row to `Administrators`.
3. Insert any user with no memberships into `Everyone`.
4. On every **CreateUser** (and JWT auto-provision), `EnsureUserInEveryoneGroup`.

### Permission catalog

Core names (apps add domain names the same way):

| Name | Meaning |
|------|---------|
| `app.access` | Default for authenticated app RPCs |
| `users.view` / `users.create` / `users.delete` / `users.reset-password` | User admin |
| `usergroups.view` / `usergroups.manage` | Groups and membership |
| `rbac.view` / `rbac.manage` | Roles and assigning roles to groups |
| `system.settings` | Cvars, webhooks, and similar admin knobs |
| `system.logs` | Logs / jobs / diagnostics-style RPCs |
| `system.impersonate` | Impersonate another user |

New permission:

1. Migration `INSERT` into `rbac_permissions` (and `rbac_role_permissions` for `superuser` for catalog consistency).
2. Go constant matching the name.
3. `RequiredPermission` case(s) as needed.

`Has()` for superusers loads **all** rows from `rbac_permissions`, so new names apply even without junction rows. The SPA lists permissions from `ListRbacPermissions` — do not hardcode the catalog in Vue.

---

## SUPERUSER

`IsSuperuser` is true when the user is in **any** group that has the `superuser` role.

```go
func (e *EffectiveRBAC) Has(p string) bool {
	if e == nil {
		return false
	}
	if e.IsSuperuser {
		return true
	}
	return e.Permissions[p]
}
```

- Frontend: `st.rbacIsSuperuser || perms.includes(name)` everywhere (nav, buttons, router).
- `GetStatus.rbac_permissions` for a superuser is the full catalog (sorted).
- UI tags: `system role` on `superuser`/`member`; `all access` on `superuser`.
- After `SetUserGroupMembers` / `SetUserGroupRbacRoles`, call `ensureSuperuserCoverage()`; error if count of distinct users with `superuser` via groups would be 0.

---

## Authentication (httpauthshim)

YAML top-level `auth:` is `*authpublic.Config` (empty/`{}` is valid). Library docs: [httpauthshim](https://github.com/jamesread/httpauthshim), [authpublic.Config](https://pkg.go.dev/github.com/jamesread/httpauthshim/authpublic#Config).

Register providers on `AuthShimContext` in this **order**:

1. Custom: `Authorization: Bearer` against `api_keys`
2. If configured: JWT header and/or cookie (`hasjwt`)
3. If `auth.httpHeader.username` set: trusted reverse-proxy headers (`hastrustedheaders`)
4. If `auth.mtls.enabled`: mTLS (`hasmtls`)
5. Custom: `{app}-sid` cookie against `sessions`

Use a no-op session persistence; set `auth.baseDir` to a temp path if the library requires it. The app does **not** use httpauthshim file sessions for UI login.

Connect (`connectrpc.com/authn`):

- Map shim username → `user_accounts`. Unknown JWT users: auto-create (`created_by = sso-autocreated`), add to `Everyone`. UI/API creates use `admin-created`.
- Load `EffectiveRBAC` after resolve.
- **Allow-list unauthenticated:** `LoginWithUsernameAndPassword`, `GetStatus` (guests get empty RBAC / `is_logged_in = false`).
- Else `RequiredPermission(procedure)`; missing perm → `Forbidden`. Default is `app.access`.
- Dev: env flag runs as anonymous superuser; log a warning. Never enable in production.

Optional MCP: Bearer API key only (no cookies). See [jwr-soa-ai](../jwr-soa-ai/SKILL.md).

---

## User loop

1. **Empty DB** — create a first user (document default credentials; prefer forcing a password change).
2. **RBAC bootstrap** — system groups/roles/membership as above.
3. **Login form** — PicoCrank `Login` in the app shell when `!isLoggedIn` (replaces `<router-view>`). Username/password tab only unless OAuth is actually wired. `@local-login` → `LoginWithUsernameAndPassword`; errors via `setLocalLoginError` (generic message).
4. **Login RPC** — verify password hash; insert `sessions`; `Set-Cookie` HttpOnly, `Path=/`, SameSite=Strict, Secure (unless an explicit insecure-dev env).
5. **GetStatus** — `username`, `is_logged_in`, `rbac_permissions[]`, `rbac_is_superuser` (plus impersonation flags if used). Force-refresh after login.
6. **SPA cache** — `fetchAppStatus`; store `window.userRbacPermissions` / `window.userRbacIsSuperuser`. Login and logout **force-refresh**.
7. **Router** — `requiresAuth` / `requiresIam` using the same IAM permission sets as Go. System Control Panel route gates: [jwr-soa-control-panel-system](../jwr-soa-control-panel-system/SKILL.md).
8. **Logout** — delete session, clear cookie. **Impersonation** (optional): `system.impersonate` to start; `StopImpersonation` needs no extra perm (authenticated impersonator).

Password on create is optional (min 8 if set). Users without a hash cannot use username/password login (SSO/API key still can).

---

## Protocol

Gate with `RequiredPermission` (see [reference.md](reference.md)):

| Area | RPCs | Perm |
|------|------|------|
| Users | `GetUser`, `CreateUser`, `DeleteUser`, `ResetUserPassword` | `users.*` |
| Users list | `GetUsers` | `app.access` (id+username for pickers); sensitive fields stay on `GetUser` |
| Groups | `List`/`GetMembers` vs `Create`/`Delete`/`SetMembers` | `usergroups.view` / `usergroups.manage` |
| RBAC read | `ListPermissions`, `ListRoles`, `GetUserRbacRoles`, `GetUserGroupRbacRoles`, role users/groups | `rbac.view` |
| RBAC write | `Create`/`Update`/`DeleteRbacRole`, `SetUserGroupRbacRoles` | `rbac.manage` |
| Self | `GetMyPermissionsAudit`, `ChangePassword`, API-key CRUD | `app.access` |
| Impersonate | `ImpersonateUser` / `StopImpersonation` | `system.impersonate` / none |

Handlers may still call `HasPermission` for object-level rules. Settings/webhooks RPCs use `system.settings` ([jwr-soa-settings](../jwr-soa-settings/SKILL.md)).

---

## Login form (PicoCrank `Login`)

Use `picocrank/vue/components/Login.vue`. Do not hand-roll a username/password form.

**App shell:** after the client is ready, if `!isLoggedIn` render `<LoginForm @login-success="onLogin" />`; else `<router-view />`. Header username / sidebar / breadcrumbs stay empty until logged in. `onLogin` calls `fetchAppStatus({ force: true })` then rebuilds nav.

**Username/password only** (default for this IAM model): hide the OAuth tab.

```vue
<Login
  ref="loginRef"
  :show-default-tabs="false"
  :custom-tabs="[{ id: 'local', label: 'Username & Password' }]"
  @local-login="onLocalLogin"
/>
```

Keep PicoCrank’s built-in `#tab-local` form. Do **not** replace it with a duplicate slot unless you need extra fields.

| API | Use |
|-----|-----|
| `@local-login` | `{ username, password }` → Connect `LoginWithUsernameAndPassword` |
| `setLocalLoginError(msg)` | Failed login (generic copy; do not leak user-not-found vs bad password) |
| `resetLocalForm()` | After success, before emitting `login-success` |
| `@oauth-login` / `oauthProviders` | Only if the app actually implements OAuth; otherwise omit |

Wrap in a PicoCrank `Section` (`title="Login"`) or a small heading + subtitle. Copy-paste: [reference.md](reference.md).

## Admin UI

Stack: Vue + PicoCrank `Section`, `Table`, `CheckGroup`, `FormLayout`, `NavigationGrid`, `Login`. List pages follow [jwr-datatable](../jwr-datatable/SKILL.md) (icon title, refresh then create, `:padding="false"`, row-click, create-in-dialog).

Every helper: `rbacIsSuperuser || perms.includes(name)`. Mirror Go sets in `rbacAccess.js`. System Control Panel hub and root nav: [jwr-soa-control-panel-system](../jwr-soa-control-panel-system/SKILL.md).

### How to assign access

Never grant permissions on a user record:

1. Create or edit a **role** and tick **permissions** (checkbox table of the full catalog).
2. Assign that **role to a group** (CheckGroup add / revoke).
3. Add the **user to the group** (user audit CheckGroup, or group members + `UserLookupDialog`).

### Pages

| Route | Page | Notes |
|-------|------|--------|
| (shell) | Login | PicoCrank `Login` when `!isLoggedIn`; not a routed page |
| `/control-panel/iam` | IAM hub | Under System Control Panel. NavigationGrid tiles gated by `users.view`, `usergroups.view`, `rbac.view` |
| `/users` | Users | Table; create (password optional). Details + **permissions audit**: CheckGroup of groups; effective roles/perms **read-only** |
| `/user-groups` | Groups | `system group` tag. Details: members via lookup (exclude existing) + `SetUserGroupMembers`; roles CheckGroup + `SetUserGroupRbacRoles`. Warn on `Everyone` / `Administrators` |
| `/settings/rbac` | Roles | Name, description, permission names, used-by counts, `system role` / `all access`. Create dialog. |
| `/settings/rbac/:id` | Role details | Permission checkbox table (not CheckGroup). Cannot edit `superuser` perm set. Groups that have this role. |
| `/settings/rbac/permissions` | Catalog | Read-only Table: name, description, roles that grant it |
| `/my-permissions` | My Permissions | Self-service audit: groups, roles, granted + granting group names; superuser as a tag |
| `/api-keys` | API keys | Self-service Bearer keys |
| `/user-control-panel` | Profile hub | Header username click; identity, prefs, password, logout — [jwr-soa-iam-profile](../jwr-soa-iam-profile/SKILL.md) |

IAM is a System Control Panel child, not a root sidebar item. Redirect unauthorized IAM routes to `/`.

---

## Docs

Operator auth doc should cover: `auth:` YAML (JWT, trusted headers, mTLS), cookie vs API key, first-user bootstrap, that groups not users carry roles, and that stripping proxy headers is required for header SSO.

---

## Implementation checklist

- [ ] Migrations: users, sessions, api_keys, groups, memberships, rbac tables; seed catalog + `superuser`/`member`; system groups + `rbac_group_roles`; drop any user↔role table
- [ ] `internal/rbac`: permission/role/group name constants
- [ ] Store: `LoadEffectiveRBAC`, bootstrap, `EnsureUserInEveryoneGroup`, `ensureSuperuserCoverage`
- [ ] httpauthshim: YAML `auth`, no-op persistence, provider order, username → DB user, JWT auto-provision
- [ ] Connect `authn` middleware + allow-list + `RequiredPermission`
- [ ] Proto: status RBAC fields; user/group/role RPCs; `GetMyPermissionsAudit`
- [ ] First-user seed + login cookie + logout
- [ ] PicoCrank `Login` in the shell when `!isLoggedIn`; `setLocalLoginError` / `resetLocalForm`; force `GetStatus` on success
- [ ] `rbacAccess.js` matching Go; `fetchAppStatus` cache + force on login/logout
- [ ] Routes + IAM hub under System Control Panel (`/control-panel/iam`) + Users/Groups/Roles/Permissions/My Permissions/API keys
- [ ] CheckGroup for group membership and group roles; checkbox table for role permissions
- [ ] `UserLookupDialog` for adding group members
- [ ] Docs: authentication page

When adding a **new permission** later: migration + Go const + procedure map; UI lists it from the API automatically.

---

## Anti-patterns

- Assigning roles directly to users (or keeping `rbac_user_roles`)
- Letting the UI grant permissions on a user instead of via role → group → membership
- Trusting Vue `v-if` without Connect `RequiredPermission`
- Using httpauthshim file sessions instead of DB `{app}-sid`
- Allowing delete/rename of `Everyone`, `Administrators`, `superuser`, or `member`
- Leaving the system with zero superusers
- Hardcoding permission checkboxes in Vue instead of `ListRbacPermissions`
- Treating `superuser` as a list of ticked perms that can be edited
- Cookie auth on `/mcp` (Bearer API key only)
- Hand-rolled login inputs instead of PicoCrank `Login`
- Showing the OAuth tab when no OAuth providers are implemented
- Duplicating PicoCrank’s local form in `#tab-local` without a reason
- Distinguishing “user not found” from “bad password” in the login error
