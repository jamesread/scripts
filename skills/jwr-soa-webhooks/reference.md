# jwr-soa-webhooks reference templates

Copy and adapt these when implementing webhooks in a new jwr SOA app. Adjust package/module names, header prefixes, and app-specific events.

## SQL schema (MySQL)

```sql
-- +migrate Up
CREATE TABLE webhook_targets (
  id INT NOT NULL AUTO_INCREMENT,
  url VARCHAR(2048) NOT NULL,
  secret VARCHAR(255) NOT NULL,
  enabled TINYINT NOT NULL DEFAULT 1,
  created DATETIME DEFAULT NULL,
  updated DATETIME DEFAULT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE webhook_events (
  id INT NOT NULL AUTO_INCREMENT,
  webhook_target_id INT NOT NULL,
  event VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY webhook_events_target_event_uidx (webhook_target_id, event),
  KEY webhook_events_event_idx (event),
  CONSTRAINT webhook_events_target_fk
    FOREIGN KEY (webhook_target_id) REFERENCES webhook_targets (id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- +migrate Down
DROP TABLE IF EXISTS webhook_events;
DROP TABLE IF EXISTS webhook_targets;
```

Postgres/SQLite: same tables; use dialect-appropriate types and `ON DELETE CASCADE`. Keep migration **ids aligned** across driver trees.

### Dispatch lookup

```sql
SELECT t.id, t.url, t.secret, t.enabled, t.created, t.updated
FROM webhook_targets t
INNER JOIN webhook_events e ON e.webhook_target_id = t.id
WHERE e.event = ? AND t.enabled = 1;
```

### Replace event set (update)

In a transaction: `DELETE FROM webhook_events WHERE webhook_target_id = ?`, then insert each selected event (after `NormalizeEvent`). Allow empty set.

---

## Faridoon legacy → standard

Faridoon originally used:

```sql
CREATE TABLE webhooks (
  id ..., url ..., event VARCHAR(64) NOT NULL, secret ..., enabled ..., created ..., updated ...
);
```

When upgrading, migrate rows into `webhook_targets` + one `webhook_events` row per old `event`, then drop `webhooks`. New apps must not create the single-table shape.

---

## Go package skeleton

```go
package webhook

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/url"
	"strings"
)

var SupportedEvents = []string{"approval.requested"}

func NormalizeEvent(event string) (string, error) {
	event = strings.TrimSpace(event)
	for _, e := range SupportedEvents {
		if event == e {
			return event, nil
		}
	}
	return "", fmt.Errorf("unsupported webhook event")
}

func NormalizeEvents(events []string) ([]string, error) {
	seen := map[string]struct{}{}
	var out []string
	for _, raw := range events {
		e, err := NormalizeEvent(raw)
		if err != nil {
			return nil, err
		}
		if _, ok := seen[e]; ok {
			continue
		}
		seen[e] = struct{}{}
		out = append(out, e)
	}
	return out, nil
}

func NormalizeURL(raw string) (string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "", fmt.Errorf("webhook URL must be non-empty")
	}
	u, err := url.Parse(raw)
	if err != nil {
		return "", fmt.Errorf("webhook URL is not valid")
	}
	scheme := strings.ToLower(u.Scheme)
	if scheme != "http" && scheme != "https" {
		return "", fmt.Errorf("webhook URL scheme must be http or https")
	}
	if strings.TrimSpace(u.Host) == "" {
		return "", fmt.Errorf("webhook URL host is required")
	}
	return raw, nil
}

func Signature(payloadJSON, secret string) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(payloadJSON))
	return hex.EncodeToString(mac.Sum(nil))
}
```

Wire a `Dispatcher` with `Store` + `*http.Client` (timeout ~2s). On dispatch: marshal payload → `EnabledTargetsForEvent` → POST each with:

- `Content-Type: application/json`
- `X-<App>-Event: <event>`
- `X-<App>-Signature: sha256=<Signature(body, secret)>`

---

## Store interface sketch

```go
type WebhookTargetRow struct {
	URL     string
	Secret  string
	Created string
	Updated string
	Events  []string
	ID      int
	Enabled bool
}

type Store interface {
	ListWebhookTargets(ctx context.Context) ([]WebhookTargetRow, error)
	FindWebhookTarget(ctx context.Context, id int) (*WebhookTargetRow, error)
	EnabledTargetsForEvent(ctx context.Context, event string) ([]WebhookTargetRow, error)
	CreateWebhookTarget(ctx context.Context, url, secret string, events []string, enabled bool) (int, error)
	UpdateWebhookTarget(ctx context.Context, id int, url, secret string, events []string, enabled bool, clearSecret bool) error
	DeleteWebhookTarget(ctx context.Context, id int) error
}
```

Load `Events` via join or a follow-up `SELECT event FROM webhook_events WHERE webhook_target_id = ? ORDER BY event`. Never select `secret` into list/API responses (keep for dispatch-only queries, or strip before proto mapping).

---

## Proto sketch

```protobuf
message Webhook {
  int32 id = 1;
  string url = 2;
  repeated string events = 3;
  bool enabled = 4;
  string created = 5;
  string updated = 6;
}

message ListWebhooksRequest {}

message ListWebhooksResponse {
  repeated Webhook webhooks = 1;
  repeated string events = 2; // SupportedEvents catalog
}

message CreateWebhookRequest {
  string url = 1;
  string secret = 2;
  repeated string events = 3;
  bool enabled = 4;
}

message UpdateWebhookRequest {
  int32 id = 1;
  string url = 2;
  string secret = 3; // empty keeps existing
  repeated string events = 4; // full replacement set
  bool enabled = 5;
}

message DeleteWebhookRequest {
  int32 id = 1;
}

// On InitResponse:
// repeated string webhook_events = N;
```

RPCs: `ListWebhooks`, `CreateWebhook`, `UpdateWebhook`, `DeleteWebhook` — admin only.

---

## Vue list + CheckGroup

```vue
<script setup>
import { computed, ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import Section from 'picocrank/vue/components/Section.vue'
import Table from 'picocrank/vue/components/Table.vue'
import CheckGroup from 'picocrank/vue/components/CheckGroup.vue'
import RadioGroup from 'picocrank/vue/components/RadioGroup.vue'
import FormField from 'picocrank/vue/components/FormField.vue'
import { client } from '../composables/client'

const webhooks = ref([])
const catalog = ref([])
const editingId = ref(null)
const edits = ref(null)

const listHeaders = [
  { key: 'id', label: 'ID', sortable: true, width: '4rem' },
  { key: 'url', label: 'URL', sortable: true },
  { key: 'events', label: 'Events', sortable: false },
  { key: 'status', label: 'Status', sortable: true, width: '6rem' },
  { key: 'actions', label: 'Actions', sortable: false, width: '6rem' },
]

const listRows = computed(() =>
  webhooks.value.map((wh) => ({
    id: wh.id,
    url: wh.url,
    events: (wh.events || []).join(', '),
    status: wh.enabled ? 'Enabled' : 'Disabled',
    actions: '',
  })),
)

const eventOptions = computed(() =>
  catalog.value.map((e) => ({ label: e, value: e })),
)

async function load() {
  const res = await client.listWebhooks({})
  webhooks.value = res.webhooks || []
  catalog.value = res.events?.length ? res.events : []
}

function startEdit(id) {
  const wh = webhooks.value.find((w) => w.id === id)
  editingId.value = id
  edits.value = {
    url: wh.url,
    secret: '',
    events: [...(wh.events || [])],
    enabled: !!wh.enabled,
  }
}

async function save() {
  await client.updateWebhook({
    id: editingId.value,
    url: edits.value.url,
    secret: edits.value.secret || '',
    events: edits.value.events,
    enabled: edits.value.enabled,
  })
  editingId.value = null
  await load()
}

onMounted(load)
</script>

<template>
  <Section title="Webhooks" subtitle="HTTP callbacks for app events" :padding="false">
    <template #toolbar>
      <RouterLink to="/admin/webhooks/create" class="button" title="Add webhook">Add</RouterLink>
    </template>
    <Table
      v-if="webhooks.length"
      :data="listRows"
      :headers="listHeaders"
      :show-pagination="webhooks.length > 10"
    >
      <template #cell-actions="{ row }">
        <button type="button" class="button" @click="startEdit(row.id)">Edit</button>
      </template>
    </Table>
    <p v-else class="padding">No webhooks configured yet.</p>
  </Section>

  <Section v-if="edits" :title="`Edit webhook #${editingId}`" :padding="true">
    <form class="form-stack" @submit.prevent="save">
      <label>URL <input v-model="edits.url" type="url" required /></label>
      <label>Secret <input v-model="edits.secret" type="text" placeholder="Leave blank to keep current secret" /></label>
      <FormField label="Events" fake>
        <CheckGroup
          v-model="edits.events"
          :options="eventOptions"
          name="webhook-events"
          aria-label="Webhook events"
        />
      </FormField>
      <FormField label="Enabled" fake>
        <RadioGroup
          v-model="edits.enabled"
          name="webhook-enabled"
          variant="boolean"
          :options="[{ label: 'On', value: true }, { label: 'Off', value: false }]"
        />
      </FormField>
      <button type="submit" class="button">Save</button>
    </form>
  </Section>
</template>
```

Create page mirrors the same CheckGroup / RadioGroup fields; secret required; `router.push('/admin/webhooks')` on success.

### Account link

```js
n.addCallback('Webhooks', () => router.push('/admin/webhooks'), {
  name: 'webhooks',
  icon: WebhookIcon,
  description: 'Configure event webhook endpoints',
})
```

### Routes

```js
{ path: '/admin/webhooks', name: 'admin-webhooks', component: WebhooksAdmin, meta: { requiresAdmin: true } },
{ path: '/admin/webhooks/create', name: 'admin-webhook-create', component: WebhookCreate, meta: { requiresAdmin: true } },
```

---

## Example payload

```json
{
  "event": "approval.requested",
  "timestamp": "2026-08-05T13:52:00Z",
  "quote": {
    "id": 42,
    "content": "...",
    "created": "2026-08-05 13:51:00",
    "approval": 0
  }
}
```

Consumer verifies `X-<App>-Signature` as `sha256=` + hex(HMAC-SHA256(raw_body, secret)).
