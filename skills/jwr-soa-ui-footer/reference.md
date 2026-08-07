# jwr-soa-ui-footer reference templates

Copy and adapt for a new jwr SOA app. Adjust package names, product URLs, and whether themes/i18n chips exist.

## Proto (Init footer fields)

Add to the app’s `InitResponse` (or nest policy as OliveTin does):

```protobuf
message InitResponse {
  bool show_footer = 1;
  bool show_new_versions = 2;
  string available_version = 3;
  string current_version = 4;
  string page_title = 5;
  // Optional: list themes; theme chip only if len > 1
  repeated string available_themes = 6;
  // Optional: hide version + update UI
  bool show_version_number = 7;
  // Or: EffectivePolicy effective_policy = N; with show_version_number inside
}
```

Field numbers are examples — use the next free tags in the real message.

## Go Init population (sketch)

```go
showVersion := policy.ShowVersionNumber // from ACL / default policy / cvar
currentVersion := ""
availableVersion := ""
showNew := false
if showVersion {
	currentVersion = buildinfo.Version
	showNew = cfg.ShowNewVersions // or cvar
	if showNew {
		availableVersion = runtimeInfo.AvailableVersion // "" / "none" / newer tag
	}
}

res := &apiv1.InitResponse{
	ShowFooter:       cfg.ShowFooter, // default true
	ShowNewVersions:  showVersion && showNew,
	AvailableVersion: availableVersion,
	CurrentVersion:   currentVersion,
	PageTitle:        siteTitle,
	ShowVersionNumber: showVersion,
	AvailableThemes:  themes, // may be empty
}
```

Sentinels like `"none"` or `"you-are-using-a-dev-build"` must **not** be shown as an update link; only treat a real newer version as visible.

## Vue layout placement

```vue
<div id="content">
  <main>
    <router-view />
  </main>

  <AppFooter
    v-if="showFooter"
    :app-name="appName"
    :logo-url="logoUrl"
    :current-version="currentVersion"
    :show-version-number="showVersionNumber"
    :show-new-versions="showNewVersions"
    :available-version="availableVersion"
    :docs-url="docsUrl"
    :issues-url="issuesUrl"
    :available-themes="availableThemes"
  />
</div>
```

Bind props from the Init composable / `initResponse` after Init succeeds (and again if Settings save reloads Init).

## `AppFooter.vue` skeleton

```vue
<template>
  <footer title="footer">
    <p>
      <img
        v-if="logoUrl"
        class="logo"
        :src="logoUrl"
        :alt="appName + ' logo'"
        title="application icon"
        style="height: 1em;"
      >
      {{ appName }}
      <span v-if="showVersionNumber && currentVersion">{{ currentVersion }}</span>
    </p>

    <p>
      <span v-if="docsUrl">
        <a :href="docsUrl" target="_blank" rel="noopener noreferrer">Docs</a>
      </span>
      <span v-if="issuesUrl">
        <a :href="issuesUrl" target="_blank" rel="noopener noreferrer">Raise an issue</a>
      </span>
      <!-- Optional: language / theme triggers when the app supports them -->
      <span v-if="availableThemes && availableThemes.length > 1">
        <a href="#" @click.prevent="$emit('open-theme')">{{ themeLabel }}</a>
      </span>
    </p>

    <p v-if="showUpdateLink">
      <a
        id="available-version"
        :href="updateUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{ availableVersion }}
      </a>
    </p>
  </footer>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  appName: { type: String, required: true },
  logoUrl: { type: String, default: '' },
  currentVersion: { type: String, default: '' },
  showVersionNumber: { type: Boolean, default: true },
  showNewVersions: { type: Boolean, default: true },
  availableVersion: { type: String, default: '' },
  docsUrl: { type: String, default: '' },
  issuesUrl: { type: String, default: '' },
  updateUrl: { type: String, default: '' },
  availableThemes: { type: Array, default: () => [] },
  themeLabel: { type: String, default: 'Theme' },
})

defineEmits(['open-theme'])

const showUpdateLink = computed(() => {
  if (!props.showVersionNumber || !props.showNewVersions) return false
  const v = (props.availableVersion || '').trim()
  if (!v || v === 'none' || v === '?' || v.startsWith('you-are-using')) return false
  return true
})
</script>
```

No scoped footer CSS required when femtocrank is loaded.

## Config / cvar defaults

| Knob | Default | Notes |
|------|---------|-------|
| `showFooter` / `show_footer` | `true` | Hide entire footer |
| `showNewVersions` / `show_new_versions` | `true` | Update hint when a newer version exists |
| `showVersionNumber` (policy or setting) | `true` | Brand shows name only when false |

Document in the app’s WebUI / configuration docs: footer visibility, version display, and update checks.

## Integration test notes

- Config with `showFooter: false` → wait for app ready → no `footer` element (or not displayed).
- Policy/setting with version hidden → footer brand without version; no `#available-version`.
- Prefer selectors: `footer`, `#available-version`, text containing the product name.

## OliveTin mapping

| Concept | OliveTin |
|---------|----------|
| Visibility | `InitResponse.showFooter` ← `config.ShowFooter` |
| Version text | `currentVersion` + `effectivePolicy.showVersionNumber` |
| Update hint | `showNewVersions`, `availableVersion` from update check |
| Themes chip | `availableThemes` from `custom-webui/themes` |
| Styles | femtocrank `footer` / `footer span`; optional `sm-transparent-footer` |
| Markup | Inline in `App.vue` today — new apps should prefer `AppFooter.vue` |
