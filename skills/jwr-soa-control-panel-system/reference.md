# jwr-soa-control-panel-system reference

Copy and adapt. Omit IAM or Settings tiles and routes when that feature is not implemented.

---

## rbacAccess.js

`CONTROL_PANEL_PERMISSIONS` is the union of implemented children. Do not list perms for pages this app does not have.

```js
const CONTROL_PANEL_PERMISSIONS = [
  // IAM (if implemented) — from jwr-soa-iam:
  'users.view', 'usergroups.view', 'rbac.view',
  // Settings (if implemented):
  'system.settings',
  // Extra children: that page’s permission(s) only
]

export function canAccessControlPanelFromStatus(st) {
  if (!st?.isLoggedIn) return false
  if (st.rbacIsSuperuser) return true
  const perms = st.rbacPermissions || []
  return CONTROL_PANEL_PERMISSIONS.some((p) => perms.includes(p))
}

export function canAccessSettingsFromStatus(st) {
  if (!st?.isLoggedIn) return false
  if (st.rbacIsSuperuser) return true
  return (st.rbacPermissions || []).includes('system.settings')
}
```

`canAccessIamFromStatus`: [jwr-soa-iam](../jwr-soa-iam/SKILL.md).

Go: the same union on `AuthenticatedUser` (`CanAccessControlPanel`). Unauthorized routes redirect to `/`.

---

## Sidebar (root item)

```js
export function setupSidebarNavigation(navigation, { showControlPanel = false } = {}) {
  navigation.clearNavigationLinks()

  // … app domain sections …

  if (showControlPanel) {
    navigation.addSection('System Control Panel', { name: 'nav-control-panel' })
    navigation.addRouterLink('controlPanel', null, {
      description: 'System and app settings',
    })
  }
}
```

Pass `showControlPanel: canAccessControlPanelFromStatus(status)`. Rebuild after login/`GetStatus`. Do not `addRouterLink` IAM or Settings at the root.

---

## Hub (`ControlPanel.vue`)

```vue
<template>
  <Section v-if="canAccessControlPanel" title="System Control Panel" subtitle="System and app settings">
    <template #toolbar>
      <button type="button" class="neutral" @click="refresh" :disabled="!clientReady">Refresh</button>
    </template>
    <Navigation ref="localNavigation">
      <NavigationGrid />
    </Navigation>
  </Section>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import Section from 'picocrank/vue/components/Section.vue'
import Navigation from 'picocrank/vue/components/Navigation.vue'
import NavigationGrid from 'picocrank/vue/components/NavigationGrid.vue'
import { UserShield01Icon, Settings01Icon } from '@hugeicons/core-free-icons'
import {
  canAccessControlPanelFromStatus,
  canAccessIamFromStatus,
  canAccessSettingsFromStatus,
} from '../javascript/rbacAccess.js'

const clientReady = ref(false)
const status = ref({})
const localNavigation = ref(null)
const canAccessControlPanel = computed(() => canAccessControlPanelFromStatus(status.value))

onMounted(async () => {
  status.value = await window.client.getStatus()
  clientReady.value = true
  if (!canAccessControlPanelFromStatus(status.value)) {
    window.router.push('/')
    return
  }
  await nextTick()
  const nav = localNavigation.value
  if (!nav) return

  if (canAccessIamFromStatus(status.value)) {
    nav.addCallback('IAM', () => window.router.push('/control-panel/iam'), {
      icon: UserShield01Icon,
      name: 'iam',
      description: 'Users, groups, and roles',
    })
  }
  if (canAccessSettingsFromStatus(status.value)) {
    nav.addCallback('Settings', () => window.router.push('/control-panel/settings'), {
      icon: Settings01Icon,
      name: 'settings',
      description: 'Configure system settings',
    })
  }
})
</script>
```

Skip the IAM or Settings `addCallback` when that feature is not implemented.

---

## Routes

```js
{
  path: '/control-panel',
  name: 'controlPanel',
  component: ControlPanel,
  meta: { title: 'System Control Panel', requiresAuth: true, requiresControlPanel: true },
},
{
  path: '/control-panel/iam',
  name: 'iam',
  component: Iam,
  meta: { title: 'IAM', requiresAuth: true, requiresIam: true },
},
{
  path: '/control-panel/settings',
  name: 'settings',
  component: SettingsAdmin,
  meta: { title: 'Settings', requiresAuth: true, requiresSettings: true },
},
```

Guard: `requiresControlPanel` → `canAccessControlPanelFromStatus`; `requiresIam` → `canAccessIamFromStatus`; `requiresSettings` → `canAccessSettingsFromStatus`. Else `/`.

---

## Breadcrumbs and Back

```js
export const crumb = {
  controlPanel: { name: 'System Control Panel', href: '/control-panel' },
  iam: { name: 'IAM', href: '/control-panel/iam' },
  settings: { name: 'Settings', href: '/control-panel/settings' },
}

export const breadcrumbsByRouteName = {
  controlPanel: () => [crumb.controlPanel],
  iam: () => [crumb.controlPanel, crumb.iam],
  settings: () => [crumb.controlPanel, crumb.settings],
}
```

On IAM and Settings pages:

```vue
<router-link :to="{ name: 'controlPanel' }" class="button inline-icon neutral">
  <span>System Control Panel</span>
</router-link>
```
