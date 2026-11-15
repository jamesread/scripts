# jwr-soa-iam-profile reference templates

Copy and adapt these when adding a profile hub and per-user preferences. Replace `{app}` proto package and module paths.

Theme fields (Color scheme preference, Theme name) and header switcher: [jwr-soa-theming](../jwr-soa-theming/reference.md).

---

## SQL schema (MySQL)

```sql
-- +migrate Up
CREATE TABLE user_preferences (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  created_at DATETIME(3) DEFAULT NULL,
  updated_at DATETIME(3) DEFAULT NULL,
  user_account_id INT UNSIGNED NOT NULL,
  language VARCHAR(32) NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  UNIQUE KEY idx_user_preferences_user_account_id (user_account_id),
  CONSTRAINT fk_user_preferences_user_account
    FOREIGN KEY (user_account_id) REFERENCES user_accounts (id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- +migrate Down
DROP TABLE IF EXISTS user_preferences;
```

Get missing row → in-memory default (`language ""`). Upsert:

```sql
INSERT INTO user_preferences (
  user_account_id, language, created_at, updated_at
) VALUES (?, ?, NOW(), NOW())
ON DUPLICATE KEY UPDATE
  language = VALUES(language),
  updated_at = NOW();
```

---

## Proto

```protobuf
message SaveUserPreferencesRequest {
  string language = 1;              // empty = browser default
}

message SaveUserPreferencesResponse {
  StandardResponse standard_response = 1;
  string username = 2;
}

message GetUserPreferencesRequest {}

message GetUserPreferencesResponse {
  string language = 1;
  repeated string available_languages = 2;
}

// On GetStatusResponse, at minimum username. Optional for the hub:
// string email = …;
// string created_at = …;
// string last_login_at = …;

rpc GetUserPreferences(GetUserPreferencesRequest) returns (GetUserPreferencesResponse);
rpc SaveUserPreferences(SaveUserPreferencesRequest) returns (SaveUserPreferencesResponse);
rpc ChangePassword(ChangePasswordRequest) returns (ChangePasswordResponse);
rpc Logout(LogoutRequest) returns (LogoutResponse);
```

Validate language: empty **or** in `AvailableLanguageCodes()`. Save only `authenticatedUser.User.ID`.

---

## Go: i18n allow-list

```go
func IsSupportedLanguage(code string) bool {
	if code == "" {
		return true
	}
	for _, available := range AvailableLanguageCodes() {
		if available == code {
			return true
		}
	}
	return false
}
```

`GetUserPreferences` sets `AvailableLanguages` from that catalog every time (not stored per user).

---

## Vue: Header + appliers (App.vue)

```vue
<Header
  :username="isLoggedIn ? username : ''"
  :themeToggleEnabled="isLoggedIn && themeColorSchemeSwitcherEnabled"
  @userClick="() => router.push({ name: 'userControlPanel' })"
/>
```

`themeColorSchemeSwitcherEnabled` from Init ([jwr-soa-theming](../jwr-soa-theming/reference.md)).

If `userClick` is missing, slot:

```vue
<template #user-info>
  <button
    v-if="username"
    type="button"
    class="user-info"
    @click="router.push({ name: 'userControlPanel' })"
  >{{ username }}</button>
</template>
```

`userPreferences.js`:

```js
export function applyUserLanguage(localeRef, fallbackLocale, language) {
  const next = (language || '').trim()
  localeRef.value = next || fallbackLocale || 'en'
}

export async function loadAndApplyUserPreferences({ localeRef, fallbackLocale } = {}) {
  if (!window.client) return
  try {
    const res = await window.client.getUserPreferences({})
    if (localeRef && res.language) {
      applyUserLanguage(localeRef, fallbackLocale, res.language)
    }
    return res
  } catch (e) {
    console.warn('Failed to load user preferences', e)
    return null
  }
}
```

Call `loadAndApplyUserPreferences` from `applyAuthFromStatus` (after login / GetStatus).

---

## Vue: profile hub (sections)

Identity `<dl>` grid:

```css
.account-info {
  display: grid;
  grid-template-columns: 200px 1fr;
  column-gap: 1em;
  row-gap: 0.25em;
  margin: 0;
}
.account-info dt { font-weight: bold; }
.account-info dd { margin: 0; }
```

Quick actions (after `refreshUserData`):

```js
nav.addCallback('User Preferences', () => router.push('/user-control-panel/preferences'), {
  icon: Settings01Icon,
  name: 'user-preferences',
  description: 'Language and personal settings',
})
nav.addCallback('Change Password', () => router.push('/change-password'), {
  icon: SecurityValidationIcon,
  name: 'change-password',
  description: 'Change your account password',
})
nav.addCallback('API Keys', () => router.push('/api-keys'), {
  icon: KeyIcon,
  name: 'api-keys',
  description: 'View and manage your API keys',
})
nav.addCallback('My Permissions', () => router.push('/user-control-panel/permissions'), {
  icon: WebSecurityIcon,
  name: 'my-permissions',
  description: 'Review your group membership and effective permissions',
})
```

Logout:

```js
await window.client.logout({})
invalidateAppStatus()
router.push('/')
window.location.reload()
```

---

## Vue: preferences form

Language (DB-backed Save) plus theme fields from [jwr-soa-theming](../jwr-soa-theming/reference.md):

```vue
<FormLayout @submit.prevent="save">
  <FormField label="Language" for="user-preferences-language" :disabled="saving"
    description="Empty (browser default) follows the browser on the next full page load.">
    <select id="user-preferences-language" v-model="language" :disabled="saving">
      <option value="">Browser default</option>
      <option v-for="code in availableLanguages" :key="code" :value="code">
        {{ languageLabel(code) }}
      </option>
    </select>
  </FormField>

  <!-- Color scheme preference + Theme name: see jwr-soa-theming/reference.md -->

  <template #actions>
    <button type="submit" class="good" :disabled="saving || !dirty">
      {{ saving ? 'Saving…' : 'Save preferences' }}
    </button>
  </template>
</FormLayout>
```

`dirty` = language vs last saved only. Theme composables persist immediately.

---

## Vue: routes

```js
{ path: '/user-control-panel', name: 'userControlPanel', component: UserControlPanel,
  meta: { title: 'User Control Panel', requiresAuth: true } },
{ path: '/user-control-panel/preferences', name: 'userPreferences', component: UserPreferences,
  meta: { title: 'User Preferences', requiresAuth: true } },
{ path: '/user-control-panel/permissions', name: 'myPermissions', component: MyPermissions,
  meta: { title: 'My Permissions', requiresAuth: true } },
{ path: '/change-password', name: 'changePassword', component: ChangePassword,
  meta: { title: 'Change Password', requiresAuth: true } },
```

Change password: current + new + confirm; new min 8; `ChangePassword` RPC; generic errors. Prefer PicoCrank `FormLayout` / `FormField` over a raw grid.
