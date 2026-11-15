# jwr-soa-iam reference templates

Copy and adapt these when implementing IAM in a new jwr SOA app. Replace `{app}` (cookie name, env prefixes, proto package) and Go module paths.

---

## SQL schema (MySQL)

Driver-split trees and `RequiredMigration`: [jwr-soa-dbmigrations](../jwr-soa-dbmigrations/SKILL.md). Postgres/SQLite: same tables; use dialect-appropriate types.

```sql
-- +migrate Up

CREATE TABLE user_accounts (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  created_at DATETIME(3) DEFAULT NULL,
  updated_at DATETIME(3) DEFAULT NULL,
  username VARCHAR(64) NOT NULL,
  password_hash VARCHAR(255) NOT NULL DEFAULT '',
  created_by VARCHAR(32) NOT NULL DEFAULT 'admin-created',
  PRIMARY KEY (id),
  UNIQUE KEY idx_user_accounts_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sessions (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  created_at DATETIME(3) DEFAULT NULL,
  updated_at DATETIME(3) DEFAULT NULL,
  sid VARCHAR(64) NOT NULL,
  user_account_id INT UNSIGNED NOT NULL,
  impersonator_user_id INT UNSIGNED DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY idx_sessions_sid (sid),
  KEY fk_sessions_user (user_account_id),
  CONSTRAINT fk_sessions_user FOREIGN KEY (user_account_id) REFERENCES user_accounts (id),
  CONSTRAINT fk_sessions_impersonator FOREIGN KEY (impersonator_user_id) REFERENCES user_accounts (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE api_keys (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  created_at DATETIME(3) DEFAULT NULL,
  updated_at DATETIME(3) DEFAULT NULL,
  user_account_id INT UNSIGNED NOT NULL,
  name VARCHAR(128) NOT NULL DEFAULT '',
  key_value VARCHAR(128) NOT NULL,
  last_used_at DATETIME(3) DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY idx_api_keys_key_value (key_value),
  KEY fk_api_keys_user (user_account_id),
  CONSTRAINT fk_api_keys_user FOREIGN KEY (user_account_id) REFERENCES user_accounts (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user_groups (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  created_at DATETIME(3) DEFAULT NULL,
  updated_at DATETIME(3) DEFAULT NULL,
  name VARCHAR(100) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY idx_user_groups_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user_group_memberships (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  created_at DATETIME(3) DEFAULT NULL,
  updated_at DATETIME(3) DEFAULT NULL,
  user_account_id INT UNSIGNED NOT NULL,
  user_group_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY idx_user_group_membership (user_account_id, user_group_id),
  KEY fk_ugm_group (user_group_id),
  CONSTRAINT fk_ugm_user FOREIGN KEY (user_account_id) REFERENCES user_accounts (id),
  CONSTRAINT fk_ugm_group FOREIGN KEY (user_group_id) REFERENCES user_groups (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rbac_permissions (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  created_at DATETIME(3) DEFAULT NULL,
  updated_at DATETIME(3) DEFAULT NULL,
  name VARCHAR(191) NOT NULL,
  description VARCHAR(512) NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  UNIQUE KEY idx_rbac_permissions_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rbac_roles (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  created_at DATETIME(3) DEFAULT NULL,
  updated_at DATETIME(3) DEFAULT NULL,
  name VARCHAR(191) NOT NULL,
  description VARCHAR(512) NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  UNIQUE KEY idx_rbac_roles_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rbac_role_permissions (
  role_id INT UNSIGNED NOT NULL,
  permission_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (role_id, permission_id),
  KEY fk_rrp_perm (permission_id),
  CONSTRAINT fk_rrp_role FOREIGN KEY (role_id) REFERENCES rbac_roles (id) ON DELETE CASCADE,
  CONSTRAINT fk_rrp_perm FOREIGN KEY (permission_id) REFERENCES rbac_permissions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rbac_group_roles (
  user_group_id INT UNSIGNED NOT NULL,
  role_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (user_group_id, role_id),
  KEY fk_rgr_role (role_id),
  CONSTRAINT fk_rgr_group FOREIGN KEY (user_group_id) REFERENCES user_groups (id) ON DELETE CASCADE,
  CONSTRAINT fk_rgr_role FOREIGN KEY (role_id) REFERENCES rbac_roles (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Seed catalog, roles, system groups

```sql
INSERT INTO rbac_permissions (created_at, updated_at, name, description) VALUES
(NOW(3), NOW(3), 'app.access', 'Use the application (non-admin APIs)'),
(NOW(3), NOW(3), 'users.view', 'List and view user accounts'),
(NOW(3), NOW(3), 'users.create', 'Create user accounts'),
(NOW(3), NOW(3), 'users.delete', 'Delete user accounts'),
(NOW(3), NOW(3), 'users.reset-password', 'Reset passwords for other users'),
(NOW(3), NOW(3), 'usergroups.view', 'List user groups and view membership'),
(NOW(3), NOW(3), 'usergroups.manage', 'Create and delete user groups; manage membership'),
(NOW(3), NOW(3), 'rbac.view', 'View roles and permissions'),
(NOW(3), NOW(3), 'rbac.manage', 'Create, update, and delete roles; assign roles to groups'),
(NOW(3), NOW(3), 'system.settings', 'View and modify system settings'),
(NOW(3), NOW(3), 'system.logs', 'View logs, job status, and run maintenance'),
(NOW(3), NOW(3), 'system.impersonate', 'Impersonate other users');

INSERT INTO rbac_roles (created_at, updated_at, name, description) VALUES
(NOW(3), NOW(3), 'superuser', 'All permissions (system role)'),
(NOW(3), NOW(3), 'member', 'Standard application access');

INSERT INTO rbac_role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM rbac_roles r CROSS JOIN rbac_permissions p WHERE r.name = 'superuser';

INSERT INTO rbac_role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM rbac_roles r JOIN rbac_permissions p ON p.name = 'app.access' WHERE r.name = 'member';

INSERT INTO user_groups (name, created_at, updated_at) VALUES
('Everyone', NOW(3), NOW(3)),
('Administrators', NOW(3), NOW(3));

INSERT INTO rbac_group_roles (user_group_id, role_id)
SELECT g.id, r.id FROM user_groups g CROSS JOIN rbac_roles r
WHERE g.name = 'Everyone' AND r.name = 'member';

INSERT INTO rbac_group_roles (user_group_id, role_id)
SELECT g.id, r.id FROM user_groups g CROSS JOIN rbac_roles r
WHERE g.name = 'Administrators' AND r.name = 'superuser';
```

### Adding a permission later

```sql
INSERT INTO rbac_permissions (created_at, updated_at, name, description) VALUES
(NOW(3), NOW(3), 'example.manage', 'Description of the new permission');

INSERT INTO rbac_role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM rbac_roles r CROSS JOIN rbac_permissions p
WHERE r.name = 'superuser' AND p.name = 'example.manage';
```

### Effective RBAC queries

```sql
-- Superuser via groups?
SELECT COUNT(*) FROM user_group_memberships ugm
INNER JOIN rbac_group_roles gr ON gr.user_group_id = ugm.user_group_id
INNER JOIN rbac_roles r ON r.id = gr.role_id
WHERE ugm.user_account_id = ? AND r.name = 'superuser';

-- Role names
SELECT DISTINCT r.name FROM rbac_roles r
INNER JOIN rbac_group_roles gr ON gr.role_id = r.id
INNER JOIN user_group_memberships ugm ON ugm.user_group_id = gr.user_group_id
WHERE ugm.user_account_id = ?
ORDER BY r.name;

-- Permissions (non-superuser)
SELECT DISTINCT p.name FROM rbac_permissions p
INNER JOIN rbac_role_permissions rp ON rp.permission_id = p.id
INNER JOIN rbac_group_roles gr ON gr.role_id = rp.role_id
INNER JOIN user_group_memberships ugm ON ugm.user_group_id = gr.user_group_id
WHERE ugm.user_account_id = ?;

-- Count of users with superuser (coverage check)
SELECT COUNT(DISTINCT ugm.user_account_id)
FROM user_group_memberships ugm
INNER JOIN rbac_group_roles gr ON gr.user_group_id = ugm.user_group_id
INNER JOIN rbac_roles r ON r.id = gr.role_id
WHERE r.name = 'superuser';
```

Replace membership or group roles in a transaction: `DELETE` then `INSERT` each id, then `ensureSuperuserCoverage`.

---

## Proto (excerpt)

Package/service names follow the app. Add to `GetStatusResponse`:

```protobuf
repeated string rbac_permissions = 14;
bool rbac_is_superuser = 15;
bool is_impersonating = 16;
string impersonator_username = 17;
```

Messages:

```protobuf
message RbacPermission {
  uint32 id = 1;
  string name = 2;
  string description = 3;
}

message RbacRole {
  uint32 id = 1;
  string name = 2;
  string description = 3;
  repeated uint32 permission_ids = 4;
  uint32 group_count = 5;
  uint32 user_count = 6;
}

message MyPermissionAuditRow {
  string permission = 1;
  bool granted = 2;
  repeated string granting_groups = 3;
}

message GetMyPermissionsAuditResponse {
  repeated string group_names = 1;
  repeated string role_names = 2;
  bool is_superuser = 3;
  repeated MyPermissionAuditRow permissions = 4;
}

message UserGroup {
  uint32 id = 1;
  string name = 2;
  uint32 member_count = 3;
}
```

RPCs (on the control service):

```protobuf
rpc LoginWithUsernameAndPassword(...) returns (...);
rpc GetStatus(GetStatusRequest) returns (GetStatusResponse);
rpc GetUsers(...) returns (...);
rpc GetUser(...) returns (...);
rpc CreateUser(...) returns (...);
rpc DeleteUser(...) returns (...);
rpc ResetUserPassword(...) returns (...);
rpc ListRbacPermissions(...) returns (...);
rpc ListRbacRoles(...) returns (...);
rpc CreateRbacRole(...) returns (...);
rpc UpdateRbacRole(...) returns (...);
rpc DeleteRbacRole(...) returns (...);
rpc GetUserRbacRoles(...) returns (...);           // effective, read-only
rpc GetUserGroupRbacRoles(...) returns (...);
rpc SetUserGroupRbacRoles(...) returns (...);
rpc GetRbacRoleUsers(...) returns (...);
rpc GetRbacRoleGroups(...) returns (...);
rpc GetMyPermissionsAudit(...) returns (...);
rpc ListUserGroups(...) returns (...);
rpc CreateUserGroup(...) returns (...);
rpc DeleteUserGroup(...) returns (...);
rpc GetUserGroupMembers(...) returns (...);
rpc SetUserGroupMembers(...) returns (...);
rpc ImpersonateUser(...) returns (...);
rpc StopImpersonation(...) returns (...);
```

`GetUserRbacRoles` returns role IDs inherited via groups. There is no `SetUserRbacRoles`.

---

## Go: permission constants

`internal/rbac/permissions.go`:

```go
package rbac

const (
	PermissionAppAccess          = "app.access"
	PermissionUsersView          = "users.view"
	PermissionUsersCreate        = "users.create"
	PermissionUsersDelete        = "users.delete"
	PermissionUsersResetPassword = "users.reset-password"
	PermissionUserGroupsView     = "usergroups.view"
	PermissionUserGroupsManage   = "usergroups.manage"
	PermissionRbacView           = "rbac.view"
	PermissionRbacManage         = "rbac.manage"
	PermissionSystemSettings     = "system.settings"
	PermissionSystemLogs         = "system.logs"
	PermissionSystemImpersonate  = "system.impersonate"
)

const RoleSuperuser = "superuser"
const RoleMember    = "member"

const GroupEveryone       = "Everyone"
const GroupAdministrators = "Administrators"
```

---

## Go: EffectiveRBAC

```go
type EffectiveRBAC struct {
	IsSuperuser bool
	Permissions map[string]bool
	RoleNames   []string
}

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

`LoadEffectiveRBAC(userID)`: count superuser via groups; if superuser, `SELECT name FROM rbac_permissions` into the map; else the distinct-permissions join. Always load distinct role names via groups.

`EnsureRBACBootstrap`: ensure system groups, `Everyone`→`member`, `Administrators`→`superuser`; if zero superusers, add `MIN(id)` user to Administrators; `INSERT IGNORE` all users with no memberships into Everyone.

`ensureSuperuserCoverage`: `CountUsersWithSuperuserViaGroups() == 0` → error `"refusing to leave the system without a superuser"`. Call after `SetUserGroupMembers` and `SetUserGroupRbacRoles`.

Cannot delete groups named `Everyone`/`Administrators`. Cannot rename/delete `superuser`/`member`. Cannot `SetRBACRolePermissions` for `superuser`.

`created_by` values: `admin-created`, `sso-autocreated`.

---

## Go: procedure map

Allow-list **before** this runs: Login, GetStatus.

```go
func RequiredPermission(procedureName string) string {
	switch procedureName {
	case /* GetUser */:
		return rbac.PermissionUsersView
	case /* CreateUser */:
		return rbac.PermissionUsersCreate
	case /* DeleteUser */:
		return rbac.PermissionUsersDelete
	case /* ResetUserPassword */:
		return rbac.PermissionUsersResetPassword
	case /* ListRbacPermissions, ListRbacRoles, GetUserRbacRoles,
	        GetUserGroupRbacRoles, GetRbacRoleUsers, GetRbacRoleGroups */:
		return rbac.PermissionRbacView
	case /* CreateRbacRole, UpdateRbacRole, DeleteRbacRole, SetUserGroupRbacRoles */:
		return rbac.PermissionRbacManage
	case /* GetUserGroupMembers */:
		return rbac.PermissionUserGroupsView
	case /* CreateUserGroup, DeleteUserGroup, SetUserGroupMembers */:
		return rbac.PermissionUserGroupsManage
	case /* ListCvars, webhooks CRUD, … */:
		return rbac.PermissionSystemSettings
	case /* logs / jobs */:
		return rbac.PermissionSystemLogs
	case /* ImpersonateUser */:
		return rbac.PermissionSystemImpersonate
	case /* StopImpersonation */:
		return "" // any authenticated user (typically the impersonator)
	}
	return rbac.PermissionAppAccess
}
```

Use generated Connect procedure path constants in the real switch. `GetUsers` stays `app.access` (pickers); `GetUser` is `users.view`.

`AuthenticatedUser.CanAccessIam`: superuser or `users.view` / `usergroups.view` / `rbac.view`. System Control Panel access (union of implemented children): [jwr-soa-control-panel-system](../jwr-soa-control-panel-system/SKILL.md).

---

## Go: httpauthshim wiring

Config:

```go
Auth *authpublic.Config `yaml:"auth"`
```

Provider order:

```go
ctx.AddProvider(apiKeyBearerProvider(db))          // Authorization: Bearer vs api_keys
// if jwt configured:
ctx.AddProvider(hasjwt.CheckUserFromJwtHeader)
ctx.AddProvider(hasjwt.CheckUserFromJwtCookie)
// if auth.httpHeader.username != "":
ctx.AddProvider(hastrustedheaders.CheckUserFromHeaders)
// if auth.mtls.enabled:
ctx.AddProvider(hasmtls.CheckUserFromMtls)
ctx.AddProvider(sessionCookieProvider(db))         // {app}-sid vs sessions
```

No-op persistence:

```go
type nopSessionPersistence struct{}

func (nopSessionPersistence) Load(_, _ string, _ *sessions.SessionStorage) error { return nil }
func (nopSessionPersistence) Save(_, _ string, _ *sessions.SessionStorage) error { return nil }
func (nopSessionPersistence) RequiresFileLock() bool                             { return false }
```

Cookie provider returns `&authpublic.AuthenticatedUser{Username, Provider: "{app}-session", SID}`. API-key provider: `Provider: "{app}-api-key"`. JWT provider name from the library is `"jwt"` — only that provider auto-creates DB users.

Connect middleware: `authn.NewMiddleware(layer.Handle).Wrap(handler)`. Guest on allow-listed procedures returns `nil, nil` (no identity). Map shim user → DB; load RBAC; check `RequiredPermission`.

Login cookie:

```go
http.Cookie{
	Name:     "{app}-sid",
	Value:    sid, // uuid
	HttpOnly: true,
	Path:     "/",
	SameSite: http.SameSiteStrictMode,
	Secure:   os.Getenv("{APP}_SECURE_COOKIES") != "false",
}
```

Dev disable-auth: env `{APP}_DEV_DISABLE_AUTH=true` → anonymous superuser; log a warning.

---

## Vue: PicoCrank Login

Import `Login` from `picocrank/vue/components/Login.vue`. Wrap in `Section` (or a small heading). Default tabs are **local + OAuth**; for password-only IAM hide OAuth.

**App.vue (shell):**

```vue
<div v-if="!isLoggedIn">
  <LoginForm @login-success="onLogin" />
</div>
<div v-else>
  <router-view />
</div>
```

```js
async function onLogin() {
  await fetchAppStatus({ force: true })
  // apply username / rbac window fields and rebuild sidebar
}
```

**LoginForm.vue:**

```vue
<script setup>
import { ref } from 'vue'
import Login from 'picocrank/vue/components/Login.vue'
import Section from 'picocrank/vue/components/Section.vue'

const emit = defineEmits(['login-success'])
const loginRef = ref(null)

async function onLocalLogin({ username, password }) {
  try {
    const res = await window.client.loginWithUsernameAndPassword({ username, password })
    if (res.standardResponse?.success) {
      loginRef.value?.resetLocalForm()
      emit('login-success', res)
      return
    }
    loginRef.value?.setLocalLoginError(res.standardResponse?.message || 'Login failed')
  } catch {
    loginRef.value?.setLocalLoginError('Login failed')
  }
}
</script>

<template>
  <Section title="Login" subtitle="Sign in with your username and password" :padding="true">
    <Login
      ref="loginRef"
      :show-default-tabs="false"
      :custom-tabs="[{ id: 'local', label: 'Username & Password' }]"
      @local-login="onLocalLogin"
    />
  </Section>
</template>
```

Do not add a `#tab-local` slot unless you need extra fields — PicoCrank already renders username, password, submit, and the error div.

`Login` props/events/expose:

| | |
|--|--|
| `showDefaultTabs` | `true` → local + OAuth tabs; `false` → only `customTabs` |
| `customTabs` | `[{ id, label }]` — use `id: 'local'` to keep the built-in password form |
| `oauthProviders` | `{ id, name, icon?, class? }[]` — omit when unused |
| `tabLabels` | Override default local/OAuth labels when `showDefaultTabs` is true |
| `@local-login` | `{ username, password }` |
| `@oauth-login` | provider object (only if implemented) |
| `setLocalLoginError(msg)` / `resetLocalForm()` | via `ref` |

---

## Vue: rbacAccess.js

Keep arrays in sync with Go helpers.

```js
export const IAM_PERMISSIONS = [
	'users.view',
	'usergroups.view',
	'rbac.view',
]

export function hasPermission(st, name) {
	return Boolean(st?.rbacIsSuperuser) || (st?.rbacPermissions || []).includes(name)
}

export function canAccessIamFromStatus(st) {
	if (!st?.isLoggedIn) return false
	if (st.rbacIsSuperuser) return true
	return IAM_PERMISSIONS.some((p) => (st.rbacPermissions || []).includes(p))
}
```

System Control Panel helpers (`canAccessControlPanelFromStatus`): [jwr-soa-control-panel-system](../jwr-soa-control-panel-system/SKILL.md).

Status cache: one in-flight `GetStatus` per page load; `applyAppStatusToWindow` sets `window.userRbacPermissions` / `window.userRbacIsSuperuser`; `fetchAppStatus({ force: true })` after login/logout.

Router `beforeEach`: if `meta.requiresAuth` and not `isLoggedIn` → `/`. Same for `requiresIam` using `canAccessIamFromStatus`.

IAM hub: PicoCrank `Navigation` + `NavigationGrid`; `addCallback` only when `hasPermission(st, …)` for Users, User Groups, Permissions catalog, Roles.

---

## Vue: assign groups to a user (CheckGroup)

```vue
<FormField label="Groups for this user" fake :disabled="saving">
  <CheckGroup
    v-model="userGroupIds"
    name="user-access-groups"
    :options="groupCheckOptions"
    :disabled="saving"
  />
</FormField>
```

`groupCheckOptions` = `{ value: g.id, label: `${g.name} (${g.memberCount} members)` }`. Save by updating each group's member set, or a dedicated set-user-groups RPC if you add one. Effective roles/permissions stay **read-only**.

---

## Vue: add roles to a group (CheckGroup)

```vue
<FormField label="Roles" fake :disabled="rolesSaving">
  <CheckGroup
    v-model="addRoleIds"
    name="user-group-add-roles"
    :options="availableRoleOptions"
    :disabled="rolesSaving"
  />
</FormField>
```

Then `setUserGroupRbacRoles({ groupId, roleIds: [...existing, ...addRoleIds] })`. Revoke removes one id and writes the remainder.

---

## Vue: role permission table (not CheckGroup)

```vue
<table class="perm-table data-table">
  <thead>
    <tr>
      <th class="perm-col-check" scope="col"><span class="a11yhidden">Grant</span></th>
      <th scope="col">Permission</th>
      <th scope="col">Description</th>
    </tr>
  </thead>
  <tbody>
    <tr v-for="p in permissionsSorted" :key="p.id">
      <td class="perm-col-check">
        <input
          v-model="form.permissionIds"
          type="checkbox"
          :value="p.id"
          :disabled="saving || role.name === 'superuser'"
          :aria-label="'Grant ' + p.name"
        />
      </td>
      <td><code>{{ p.name }}</code></td>
      <td>{{ p.description || '—' }}</td>
    </tr>
  </tbody>
</table>
```

Tags: `system role` if name is `superuser` or `member`; `all access` if `superuser`. Do not allow delete of those two roles.

---

## Vue: UserLookupDialog

`<dialog>` with search input, PicoCrank `CheckGroup` of users (`multiple`), `excludeUserIds` for current members. Confirm → append ids and `SetUserGroupMembers`. Single-select mode: click a row to pick one user.

`GetUsers` must be callable with `app.access` so pickers work for non-admins who still share resources with users.

---

## Vue: My Permissions audit

`GetMyPermissionsAudit` → group name tags, role name tags, table of every catalog permission with granted icon and granting group names. If `isSuperuser`, show a note that all permissions are granted and use a `superuser` tag when `grantingGroups` is empty.
