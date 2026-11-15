# jwr-soa-theming reference templates

Copy and adapt. Replace `{app}` paths and storage keys.

---

## Cvar catalog (Go)

```go
const (
	CategoryTheme = "Theme"

	KeyThemeColorSchemeSwitcherEnabled = "theme_color_scheme_switcher_enabled"
	KeyThemeName                       = "theme_name"
	KeyThemeControl                    = "theme_control"

	ThemeControlSystem = "system"
	ThemeControlUser   = "user"
)

// In Defaults():
{
	Key: KeyThemeColorSchemeSwitcherEnabled, MainType: TypeBool, ValueInt: 0,
	Title: "Color scheme switcher",
	Description: "Show the auto/light/dark color scheme control in the PicoCrank header.",
	Category: CategoryTheme, Ordinal: 10,
},
{
	Key: KeyThemeName, MainType: TypeString, ValueString: "",
	Title: "Theme name",
	Description: "Default or enforced drop-in CSS theme (empty = Femtocrank base styling only).",
	Category: CategoryTheme, Ordinal: 20,
},
{
	Key: KeyThemeControl, MainType: TypeString, ValueString: ThemeControlUser,
	Title: "Theme control",
	Description: "System preference forces the theme name cvar for everyone. User preference uses the cvar as default and allows overrides on User Preferences.",
	Category: CategoryTheme, Ordinal: 30,
},
```

Validate on `UpdateCvar`:

- `theme_control`: `system` or `user` only
- `theme_name`: empty or in `AvailableThemeNames()`

Expose accessors: `ThemeColorSchemeSwitcherEnabled`, `ThemeName`, `ThemeControl`.

---

## Init / Features (proto sketch)

```protobuf
message Features {
  // …existing fields…
  bool theme_color_scheme_switcher_enabled = …;
  string theme_name = …;
  string theme_control = …;  // "system" | "user"
  repeated string available_themes = …;
}
```

Populate `available_themes` from the same catalog the Settings theme select uses.

---

## applyAppTheming.js

```js
import { useTheme } from 'picocrank/vue/composables/useTheme.js'
import { useCustomTheme } from 'picocrank/vue/composables/useCustomTheme.js'

export function themeControlFromFeatures(features = {}) {
  const raw = (features.themeControl || features.theme_control || 'user').trim()
  return raw === 'system' ? 'system' : 'user'
}

export function applyAppTheming(features = {}) {
  const { setTheme: setColorScheme } = useTheme()
  const { themePreference, setTheme, clearTheme } = useCustomTheme()

  const control = themeControlFromFeatures(features)
  const systemTheme = (features.themeName || features.theme_name || '').trim()

  if (control === 'system') {
    if (systemTheme) {
      setTheme(systemTheme)
    } else {
      clearTheme()
    }
    return { control, appliedTheme: systemTheme }
  }

  // user preference: keep stored override, else system default
  const stored = (themePreference.value || '').trim()
  if (stored) {
    setTheme(stored)
    return { control, appliedTheme: stored }
  }
  if (systemTheme) {
    setTheme(systemTheme)
    return { control, appliedTheme: systemTheme }
  }
  clearTheme()
  return { control, appliedTheme: '' }
}

export function themeColorSchemeSwitcherEnabledFromFeatures(features = {}) {
  return features.themeColorSchemeSwitcherEnabled === true
    || features.theme_color_scheme_switcher_enabled === true
}
```

Call from `App.vue` after `loadInit()`:

```js
import { applyAppTheming, themeColorSchemeSwitcherEnabledFromFeatures } from './applyAppTheming.js'

const themeColorSchemeSwitcherEnabled = computed(() =>
  themeColorSchemeSwitcherEnabledFromFeatures(initFeatures.value),
)

onMounted(async () => {
  await loadInit()
  applyAppTheming(initFeatures.value)
})
```

Re-call `applyAppTheming` when Init reloads (Settings save) or on login.

---

## Vue: Header

```vue
<Header
  :username="isLoggedIn ? username : ''"
  :themeToggleEnabled="isLoggedIn && themeColorSchemeSwitcherEnabled"
  @userClick="goToUserControlPanel"
/>
```

---

## Vue: User Preferences (theme fields)

```vue
<script setup>
import { computed } from 'vue'
import RadioGroup from 'picocrank/vue/components/RadioGroup.vue'
import { useTheme } from 'picocrank/vue/composables/useTheme.js'
import { useCustomTheme } from 'picocrank/vue/composables/useCustomTheme.js'
import { themeControlFromFeatures } from '../javascript/applyAppTheming.js'

const props = defineProps({
  initFeatures: { type: Object, default: () => ({}) },
})

const { theme, setTheme: setColorScheme } = useTheme()
const { availableThemes, themeLabels, themePreference, setTheme } = useCustomTheme()

const themeControl = computed(() => themeControlFromFeatures(props.initFeatures))
const userThemeControl = computed(() => themeControl.value === 'user')

const colorSchemeOptions = [
  { label: 'Auto (system)', value: 'auto' },
  { label: 'Light', value: 'light' },
  { label: 'Dark', value: 'dark' },
]

function onThemeNameChange(event) {
  setTheme(event.target.value)
}
</script>

<template>
  <FormField label="Color scheme preference" fake
    description="Choose light, dark, or match your operating system. Saved in this browser.">
    <RadioGroup
      v-model="theme"
      name="user-preferences-color-scheme"
      variant="list"
      :options="colorSchemeOptions"
      aria-label="Color scheme preference"
    />
  </FormField>

  <FormField
    v-if="userThemeControl"
    label="Theme name"
    for="user-preferences-theme-name"
    description="Override the administrator default theme. Saved in this browser."
  >
    <select
      id="user-preferences-theme-name"
      :value="themePreference"
      @change="onThemeNameChange"
    >
      <option value="">Default (Femtocrank only)</option>
      <option v-for="name in availableThemes" :key="name" :value="name">
        {{ themeLabels[name] || name }}
      </option>
    </select>
  </FormField>
</template>
```

Mount `discoverThemes()` once at app boot so `availableThemes` is populated before the prefs page opens.

---

## Vue: Settings Theme category

The generic Settings page renders bool/string cvars from `ListCvars`. For Theme, either:

1. **Dedicated Theme section** in `SettingsAdmin.vue` (recommended), or
2. Key-specific overrides when `cvar.key` matches the three theme keys.

Dedicated section sketch:

```vue
<Section v-if="themeCvars.length" title="Theme" subtitle="Appearance and theme policy">
  <FormLayout @submit.prevent="saveThemeSection">
    <FormField label="Color scheme switcher" fake>
      <RadioGroup
        v-model="themeEdits.colorSchemeSwitcher"
        name="settings-theme-color-scheme-switcher"
        variant="boolean"
        :options="[{ label: 'On', value: true }, { label: 'Off', value: false }]"
        aria-label="Color scheme switcher"
        @change="themeSectionDirty = true"
      />
      <p class="subtle">Show the auto/light/dark control in the header.</p>
    </FormField>

    <FormField label="Theme name" for="settings-theme-name">
      <select
        id="settings-theme-name"
        v-model="themeEdits.themeName"
        @change="themeSectionDirty = true"
      >
        <option value="">Default (Femtocrank only)</option>
        <option v-for="name in availableThemes" :key="name" :value="name">
          {{ themeLabels[name] || name }}
        </option>
      </select>
      <p class="subtle">Drop-in CSS theme for the app.</p>
    </FormField>

    <FormField label="Theme control" fake>
      <RadioGroup
        v-model="themeEdits.themeControl"
        name="settings-theme-control"
        variant="list"
        :options="[
          { label: 'System preference', value: 'system' },
          { label: 'User preference', value: 'user' },
        ]"
        aria-label="Theme control"
        @change="themeSectionDirty = true"
      />
      <p class="subtle">
        System preference forces the theme name for all users.
        User preference uses this theme as the default; users may override on User Preferences.
      </p>
    </FormField>

    <template #actions>
      <button type="submit" class="good" :disabled="!themeSectionDirty || themeSaving">
        {{ themeSaving ? 'Saving…' : 'Save' }}
      </button>
    </template>
  </FormLayout>
</Section>
```

On save: `updateCvar` for each key → `loadInit()` → `applyAppTheming(initFeatures)`.

---

## App boot (main.js)

```js
import { initCustomTheme } from 'picocrank/vue/composables/useCustomTheme.js'

initCustomTheme({
  storageKey: '{app}-custom-theme',
  includeSupplementalThemes: false,
})

// In App.vue after Init:
const { discoverThemes } = useCustomTheme()
await discoverThemes()
applyAppTheming(initFeatures)
```

Color scheme initializes automatically via `useTheme` module side effects.

---

## Drop-in themes layout

```
frontend/public/themes/
  index.json          # { "themes": ["olivetin", …] } optional
  olivetin/
    theme.css
```

`discoverThemes()` fetches `{baseUrl}/themes/index.json`. Keep server `AvailableThemeNames()` in sync for cvar validation.

---

## Migration from iam-profile

If `user_preferences.theme_toggle_enabled` exists, remove it:

```sql
-- +migrate Up
ALTER TABLE user_preferences DROP COLUMN theme_toggle_enabled;

-- +migrate Down
ALTER TABLE user_preferences
  ADD COLUMN theme_toggle_enabled TINYINT(1) NOT NULL DEFAULT 0;
```

Remove theme fields from `GetUserPreferences` / `SaveUserPreferences` proto and handlers. Theme switcher visibility moves to cvar `theme_color_scheme_switcher_enabled`.
