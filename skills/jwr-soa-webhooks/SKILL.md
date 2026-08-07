---
name: jwr-soa-webhooks
description: >-
  Implements outbound HTTP webhooks for jwr SOA apps: webhook_targets stored in
  the database with 0..n webhook_events, enable/disable, HMAC-signed POSTs,
  Connect admin CRUD, and a PicoCrank Table management page with CheckGroup for
  supported events. Use when adding webhooks, webhook targets, event
  subscriptions, approval.requested-style callbacks, or aligning an app with
  Faridoon-style webhook delivery.
---

# jwr-soa-webhooks

Outbound webhooks are **DB-backed targets** that POST JSON to an admin-configured URL when app events fire. Each target can subscribe to **zero or more** events from a code-defined catalog, and can be enabled or disabled without deleting the row.

Inspired by **Faridoon** (`service/internal/webhook/`, `service/server_admin.go` webhook RPCs, `frontend/src/views/WebhooksAdmin.vue`, `WebhookCreate.vue`). Faridoon’s live schema still uses a single `webhooks.event` column; **new apps (and Faridoon upgrades) must use `webhook_targets` + `webhook_events`** as below.

Companions: [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md) (layout, Go/Vue/PicoCrank, Connect), [jwr-soa-dbmigrations](../jwr-soa-dbmigrations/SKILL.md).

Copy-paste schemas and UI skeleton: [reference.md](reference.md).

## Principles

1. **Targets in the DB** — `webhook_targets` holds URL, signing secret, enabled flag, timestamps. Not YAML/env lists.
2. **Events are many** — `webhook_events` associates **0..n** event names to one target. Never store a single event column on the target.
3. **Catalog in code** — `SupportedEvents` (or equivalent) is the source of allowed event strings; validate on create/update; expose via Init / List for the UI.
4. **CheckGroup for subscriptions** — admin create/edit uses PicoCrank `CheckGroup` over the supported-events catalog (not a single `<select>`).
5. **PicoCrank Table list** — `/admin/webhooks` lists targets in a PicoCrank `Table`; create is a separate route.
6. **Sign and fire** — HMAC-SHA256 over the JSON body; short HTTP timeout; only **enabled** targets that subscribe to the event are delivered.

## When to use

- Adding outbound webhooks / HTTP callbacks for domain events
- Porting Faridoon’s webhook approach into another jwr SOA app
- Splitting a single-event webhook table into targets + event subscriptions
- Building an admin Webhooks page with PicoCrank Table + CheckGroup

Do **not** use this for inbound webhooks (receiving third-party callbacks), websockets, or per-user notification preferences.

---

## Architecture

```
SupportedEvents in code ──validate──► webhook_events.event
                                              │
webhook_targets ◄──0..n── webhook_events      │
       │                                      │
       │     List/Create/Update/Delete (admin)┤
       │                                      │
       └── Dispatcher ──EnabledTargetsForEvent──► POST JSON + HMAC
                                              │
WebhooksAdmin.vue (Table) / WebhookCreate.vue ◄┘  CheckGroup events
Account nav → /admin/webhooks
```

---

## Data model

### `webhook_targets`

| Column | Role |
|--------|------|
| `id` | PK |
| `url` | Destination (`http`/`https`, host required) |
| `secret` | Shared HMAC secret (never return in list/detail responses) |
| `enabled` | `0`/`1` — disabled targets are skipped at dispatch |
| `created` / `updated` | Timestamps |

### `webhook_events`

| Column | Role |
|--------|------|
| `id` | PK (optional if composite unique is enough) |
| `webhook_target_id` | FK → `webhook_targets.id` (CASCADE delete) |
| `event` | Event name from `SupportedEvents` |

Constraints: **UNIQUE (`webhook_target_id`, `event`)**. Index `(event)` (and join on target `enabled`) for dispatch lookups.

A target with **zero** event rows is valid (configured but subscribed to nothing). Dispatch for event `E` loads targets where `enabled = 1` AND a matching `webhook_events` row exists.

### Event catalog

Keep allowed names in Go, e.g.:

```go
var SupportedEvents = []string{"approval.requested"}
```

Apps add more string constants as features need them. Do not invent a separate DB catalog table unless product requirements demand admin-editable event types.

---

## Delivery

Package under `service/internal/webhook/` (or app-equivalent):

| Concern | Behavior |
|---------|----------|
| URL normalize | Trim; parse; scheme `http` or `https`; host required |
| Event normalize | Must be in `SupportedEvents` |
| Payload | JSON with at least `event`, `timestamp` (RFC3339 UTC), plus event-specific object |
| Headers | `Content-Type: application/json`; app event header; `X-*-Signature: sha256=<hex>` (HMAC-SHA256 of raw body with target secret) |
| Client | Shared `http.Client` with short timeout (~2s); fire-and-forget from handlers (log/swallow delivery errors; do not fail the user action) |
| Lookup | `EnabledTargetsForEvent(ctx, event)` → join targets + events |

Call the dispatcher from the business handler after the domain write succeeds (e.g. pending approval created → `Dispatch(ctx, "approval.requested", payload)`).

---

## Protocol

Admin-gated RPCs (SUPERUSER / admin):

| RPC | Role |
|-----|------|
| `ListWebhooks` | Targets with `repeated string events`; response also returns catalog `events` (= `SupportedEvents`) |
| `CreateWebhook` | `url`, `secret` (required), `repeated events`, `enabled` |
| `UpdateWebhook` | `id`, `url`, `secret` (empty = keep), `repeated events` (replace set), `enabled` |
| `DeleteWebhook` | Deletes target; DB CASCADE removes event rows |

Proto shape: target message uses **`repeated string events`**, not a single `event` field. Never include `secret` in responses.

Optional: audit `webhook.create` / `webhook.update` / `webhook.delete`.

### Init

Expose `webhook_events` (catalog strings) on `Init` so create forms can render CheckGroup options without an extra round-trip. After deploy, new catalog entries appear once the binary ships; no migration needed for catalog-only changes.

---

## Admin UI

**Routes (admin-only):**

- `/admin/webhooks` — list (`WebhooksAdmin.vue`)
- `/admin/webhooks/create` — create (`WebhookCreate.vue`)

**Entry:** Account (or admin nav) callback → `/admin/webhooks` (e.g. Hugeicons `WebhookIcon`, description “Configure event webhook endpoints”).

**Stack:** Vue + PicoCrank `Section`, `Table`, `CheckGroup`, `RadioGroup` (enabled On/Off), `FormField` / form layout. Prefer femtocrank/picocrank styling.

### List page

1. **Section** — title “Webhooks”, short subtitle, toolbar **Add** link to create.
2. **PicoCrank `Table`** — columns: ID, URL, Events (joined labels), Status (Enabled/Disabled), Actions (Edit).
3. Empty state when no targets.
4. **Edit** — inline or adjacent Section: URL, secret (blank keeps current), **CheckGroup** of supported events, enabled RadioGroup, Save / Cancel; **DangerZone** delete.

### Create page

Form: URL, secret (required), **CheckGroup** for events (options from Init / list catalog), enabled default On, then Create → redirect to list.

**CheckGroup (required pattern for events):**

```vue
<FormField label="Events" fake>
  <div>
    <CheckGroup
      v-model="selectedEvents"
      :options="eventOptions"
      name="webhook-events"
      aria-label="Webhook events"
    />
    <p class="subtle">Select one or more events that should POST to this URL.</p>
  </div>
</FormField>
```

`eventOptions` = catalog strings as `{ label, value }` (label may equal value). `selectedEvents` is `string[]` sent as `events` on create/update.

**Enabled:** PicoCrank `RadioGroup` `variant="boolean"` (On/Off), same pattern as [jwr-soa-settings](../jwr-soa-settings/SKILL.md) — not a raw checkbox.

---

## Docs / ops

Document:

- Supported event names and payload shapes
- Signature header format and verification sketch for consumers
- That targets are admin-only and secrets are write-only
- Migration names under driver-split trees ([jwr-soa-dbmigrations](../jwr-soa-dbmigrations/SKILL.md))

---

## Implementation checklist

When adding webhooks to an app:

- [ ] Migration: `webhook_targets` + `webhook_events` (FK CASCADE, unique target+event, index for dispatch)
- [ ] Bump `RequiredMigration` / apply via sql-migrate
- [ ] `webhook` package: `SupportedEvents`, `NormalizeEvent` / `NormalizeURL`, `Signature`, `Dispatcher`
- [ ] Store: CRUD targets; replace event set on update; `EnabledTargetsForEvent`
- [ ] Proto: target with `repeated events`; List/Create/Update/Delete; Init catalog field
- [ ] Admin-gated handlers + validation (URL, secret on create, events ⊆ catalog)
- [ ] Dispatch from domain handlers after successful writes
- [ ] `WebhooksAdmin.vue`: PicoCrank `Table` + edit with CheckGroup
- [ ] `WebhookCreate.vue`: CheckGroup + RadioGroup enabled
- [ ] Routes `/admin/webhooks`, `/admin/webhooks/create` + Account link
- [ ] Unit tests: normalize event/URL, signature length/hex
- [ ] Docs: events, payloads, signing

When adding a **new** event later:

1. Append to `SupportedEvents`
2. Build payload + dispatch call site
3. Document payload; UI CheckGroup picks it up from Init/List automatically

---

## Anti-patterns

- Single `event` column on the target (use `webhook_events`)
- `<select>` / radio for event subscription when multiple events are supported — use **CheckGroup**
- Returning secrets over the API
- Blocking the user request on slow webhook HTTP
- Storing webhook URLs only in YAML/env after the DB exists
- Firing disabled targets or targets without a matching event row
- ORMs for persistence (prepared statements via store interface)
