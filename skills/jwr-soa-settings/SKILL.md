---
name: jwr-soa-settings
description: >-
  Implements database-backed configuration variables (cvars) and an admin
  Settings page for jwr SOA apps: Go defaults catalog, int/string storage,
  startup upsert of new keys and refreshed titles/descriptions, Connect RPC
  List/Update, PicoCrank RadioGroup UI grouped by category. Use when adding
  Settings, cvars, feature flags, admin configuration, enable_* toggles, or
  when aligning an app with Faridoon-style runtime settings.
---

# jwr-soa-settings

Runtime knobs live in the **database as cvars**, not YAML `features:` blocks or env vars (except bootstrap seeds). Admins edit them on a Settings page. Code owns the catalog of keys and UI metadata; the DB owns live values.

Reference implementation: **Faridoon** (`service/internal/cvar/`, `service/server_cvars.go`, `frontend/src/views/SettingsAdmin.vue`, `docs/configuration/index.md`).

Companion skill: [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md) (project layout, Go/Vue/PicoCrank, Connect RPC).

Copy-paste schemas and UI skeleton: [reference.md](reference.md).

## Principles

1. **Catalog in code** — `Defaults()` (or equivalent) is the single source for keys, types, titles, descriptions, categories, ordinals, and default values.
2. **Two value columns** — `value_int` and `value_string`. Bools are `int` `0`/`1` with `main_type = "bool"`. Prefer int or string; do not invent extra columns.
3. **Startup upsert** — insert missing keys; on conflict refresh **metadata only** (title, description, category, ordinal). Never overwrite admin-chosen values or `main_type` on upsert.
4. **Admin API is values-only** — `UpdateCvar` sends `key` + values; metadata is read-only over the wire.
5. **Selective Init projection** — expose SPA-needed flags via `Init` / `Features`; keep operational knobs server-only when the UI does not need them.
6. **PicoCrank Settings UI** — category sections, FormLayout, bools as `RadioGroup` `variant="boolean"`, per-section dirty Save, then reload Init.

## When to use

- Adding or extending an admin Settings / configuration page
- Introducing feature toggles (`enable_*`), site title, page sizes, or similar
- Porting Faridoon’s cvar approach into another jwr SOA app
- Replacing env/YAML feature flags with DB-backed settings

Do **not** use cvars for secrets, per-user prefs, or values that must be set before the DB is available (use YAML/env for those).

---

## Architecture

```
Defaults() in code ──ensure on startup──► cvars table
                                              │
                    ListCvars (admin) ────────┤
                    UpdateCvar (admin) ───────┤  (values only)
                                              │
                    Typed accessors ──────────┼──► handlers / enforcement
                    Init → Features ──────────┘──► SPA (useInit)
                                              │
                    SettingsAdmin.vue ◄────────┘  PicoCrank UI
```

---

## Data model

| `main_type` | Storage | UI control |
|-------------|---------|------------|
| `string` | `value_string` | text input |
| `int` | `value_int` | number input (validate range server-side) |
| `bool` | `value_int` as `0`/`1` | PicoCrank `RadioGroup` `variant="boolean"` |

### Row / Def fields

| Field | Role |
|-------|------|
| `key` | Stable PK (`snake_case`) |
| `main_type` | `string` \| `int` \| `bool` |
| `value_int` / `value_string` | Live value (one in use per type) |
| `title` | Admin label |
| `description` | Help text under the control |
| `category` | Settings section heading (e.g. `Site`, `Features`, `Access`) |
| `ordinal` | Sort order within/across categories (space by 10s: 10, 20, …) |

Enums: prefer `string` or `int` + RadioGroup `variant="default"`/`"list"` with `{ label, value }` options; validate allowed values on the server. No separate DB enum type required.

---

## Catalog and upsert

### Defaults package

Put keys, type constants, categories, and `Defaults(...)` in `service/internal/cvar/` (or app-equivalent). Seed bootstrap values (e.g. site title from YAML) only as **initial** `ValueString`/`ValueInt` on first insert.

### Startup

After migrations, call `ensureDefaultCvars` (loop `Defaults` → `InsertCvarIfMissing`).

Upsert semantics (required):

```sql
INSERT INTO cvars (...)
VALUES (...)
ON DUPLICATE KEY UPDATE
  cvar_title = VALUES(cvar_title),
  cvar_description = VALUES(cvar_description),
  cvar_category = VALUES(cvar_category),
  cvar_ordinal = VALUES(cvar_ordinal)
```

| Event | Behavior |
|-------|----------|
| New key in `Defaults` | Row inserted with default value |
| Title/description/category/ordinal changed in code | Metadata refreshed on next start |
| Admin changed a value | Value **preserved** across restarts/upgrades |

`UpdateCvar` (admin save) updates **only** `value_int` / `value_string`.

Document this contract in `docs/configuration/` (or equivalent).

---

## Protocol

Admin RPCs (gate with admin / SUPERUSER):

- `ListCvars` → ordered list (`ORDER BY ordinal, key`)
- `UpdateCvar({ key, value_int, value_string })` → updated `Cvar`

`Cvar` message includes metadata for the UI (`title`, `description`, `category`, `ordinal`, `main_type`) plus values. Clients never send metadata on update.

Validate by `main_type` before write (non-empty string ≤255, int ranges, bool normalize to 0/1).

Optional: audit log `cvar.update` after successful save.

### Init / Features

Project only what the SPA needs into `InitResponse.features` (and fields like `site_title`). After Settings save, frontend must call `loadInit()` so nav and feature gates refresh without process restart.

---

## Backend accessors

Provide typed helpers, not raw row reads everywhere:

- `boolCvar(ctx, key, fallback) bool`
- Named wrappers per flag (`votingEnabled`, …)
- Clamped ints (`quotesPerPage` with min/max)
- String with config fallback for bootstrap (`siteTitle`)

Enforce flags in handlers even when also exposed via Init (defense in depth).

---

## Settings page design

**Route:** `/admin/settings` (admin-only). Entry from Account (or equivalent admin nav).

**Stack:** Vue + PicoCrank `Section`, `FormLayout`, `FormField`, `RadioGroup`. Prefer femtocrank/picocrank styling; minimal custom CSS.

### Page structure

1. **Intro Section** — title “Settings”, short subtitle, flash error/success, empty state if no cvars.
2. **One Section per category** — `title` = category name from API. Group rows preserving list order (API is ordinal-sorted); use `category || 'Other'`.
3. **Inside each Section** — one `FormLayout` with every cvar in that category, then a **Save** action for that section only.

### Controls by type

| Type | Pattern |
|------|---------|
| `string` | `FormField` + `<input type="text" maxlength="255">` |
| `int` | `FormField` + `<input type="number">` (+ min/max when known) |
| `bool` | `FormField fake` + `RadioGroup` `variant="boolean"` with On/Off options |

Under every control: description as `<p class="subtle">` when present. Label = `title` or key with `_` → spaces.

**Bool RadioGroup (required pattern):**

```vue
<FormField :label="labelFor(cvar)" fake>
  <div>
    <RadioGroup
      v-model="edits[cvar.key].boolValue"
      :name="fieldId(cvar)"
      variant="boolean"
      :options="[{ label: 'On', value: true }, { label: 'Off', value: false }]"
      :aria-label="labelFor(cvar)"
      @change="markDirty(group.name)"
    />
    <p v-if="cvar.description" class="subtle">{{ cvar.description }}</p>
  </div>
</FormField>
```

Use `fake` on `FormField` because RadioGroup is not a single labeled input id. Persist bools as `valueInt: 0|1`.

### Edit / save UX

- Local `edits[key]` mirrors server (`valueString`, `valueInt`, `boolValue`).
- Track **dirty per section**; Save disabled until dirty; show “Saving…” while in flight.
- Save writes **all cvars in that category** (sequential `updateCvar`), then `load()` + `loadInit()`.
- No global Save — categories are independent units of work.
- Do not hardcode field lists in the Vue file; render from `ListCvars` so new catalog keys appear automatically after deploy + restart upsert.

### Out of scope for the Settings page

- Per-user preferences
- Secrets / credentials
- Non-admin self-service config
- Live preview of every side effect (document effects in `description` + docs instead)

---

## Docs

Operator-facing configuration doc should state:

- YAML/env vs cvars (what seeds vs what is live)
- Upsert / metadata refresh on startup
- Table of keys, types, defaults, effects
- That saving Settings reloads Init (no process restart)

---

## Implementation checklist

When adding this approach to an app:

- [ ] Migration: `cvars` table with int + string values, `main_type`, title, description, category, ordinal
- [ ] `cvar` package: types, keys, categories, `Def`, `Defaults()`
- [ ] Store: `ListCvars`, `FindCvar`, `InsertCvarIfMissing` (metadata-only upsert), `UpdateCvar` (values only)
- [ ] Startup: `ensureDefaultCvars` after migrations
- [ ] Proto: `Cvar`, `ListCvars`, `UpdateCvar`; optional `Features` on `Init`
- [ ] Admin-gated handlers + validation + typed accessors
- [ ] Enforce flags in business logic
- [ ] `SettingsAdmin.vue`: category sections, RadioGroup bools, dirty Save, `loadInit()`
- [ ] Admin route + Account link
- [ ] Docs: configuration page with key table and upsert contract
- [ ] Unit test: `Defaults()` entries have title, description, category, ordinal

When adding a **new** setting later:

1. Add key + `Def` to `Defaults()` with spaced ordinal
2. Accessor + Init/Features if the SPA needs it
3. Enforce in handlers
4. Document in configuration docs  
   (No Vue field wiring — Settings page is data-driven.)

---

## Anti-patterns

- Storing feature flags only in YAML/env after the DB exists
- Overwriting `value_*` on startup upsert
- Letting the client update title/description via RPC
- Custom bool toggles/checkboxes instead of PicoCrank `RadioGroup` `variant="boolean"`
- Hardcoding each setting as a separate Vue form field
- Putting every cvar into `Features` (leak operational knobs; keep Init lean)
