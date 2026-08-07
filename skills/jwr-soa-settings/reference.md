# jwr-soa-settings reference templates

Copy and adapt these when implementing cvars in a new jwr SOA app. Adjust package/module names and app-specific keys.

## SQL schema

```sql
CREATE TABLE cvars (
  cvar_key VARCHAR(255) NOT NULL PRIMARY KEY,
  cvar_value_int TINYINT NULL,
  cvar_value_string VARCHAR(255) NULL,
  cvar_main_type VARCHAR(255) NOT NULL,
  cvar_title VARCHAR(255) NOT NULL DEFAULT '',
  cvar_description VARCHAR(512) NOT NULL DEFAULT '',
  cvar_category VARCHAR(255) NOT NULL DEFAULT '',
  cvar_ordinal INT NOT NULL DEFAULT 0
);
```

List query order: `ORDER BY cvar_ordinal, cvar_key`.

## Upsert and update

```sql
-- Insert missing; refresh metadata only on conflict
INSERT INTO cvars (
  cvar_key, cvar_value_int, cvar_value_string, cvar_main_type,
  cvar_title, cvar_description, cvar_category, cvar_ordinal
) VALUES (?, ?, NULLIF(?, ''), ?, ?, ?, ?, ?)
ON DUPLICATE KEY UPDATE
  cvar_title = VALUES(cvar_title),
  cvar_description = VALUES(cvar_description),
  cvar_category = VALUES(cvar_category),
  cvar_ordinal = VALUES(cvar_ordinal);

-- Admin save: values only
UPDATE cvars
SET cvar_value_int = ?, cvar_value_string = NULLIF(?, '')
WHERE cvar_key = ? LIMIT 1;
```

## Go catalog skeleton

```go
package cvar

const (
	TypeString = "string"
	TypeInt    = "int"
	TypeBool   = "bool"

	CategorySite     = "Site"
	CategoryFeatures = "Features"
	CategoryAccess   = "Access"
)

type Def struct {
	Key, MainType, Title, Description, Category, ValueString string
	Ordinal, ValueInt                                         int
}

func Defaults(siteTitle string) []Def {
	return []Def{
		{
			Key: "site_title", MainType: TypeString, ValueString: siteTitle,
			Title: "Site title", Description: "Shown in the header and browser tab.",
			Category: CategorySite, Ordinal: 10,
		},
		{
			Key: "enable_example", MainType: TypeBool, ValueInt: 0,
			Title: "Enable example", Description: "Turn the example feature on or off.",
			Category: CategoryFeatures, Ordinal: 20,
		},
	}
}
```

## Store row and interface

```go
type CvarRow struct {
	Key, MainType, Title, Description, Category, ValueString string
	Ordinal, ValueInt                                         int
}

type Store interface {
	ListCvars(ctx context.Context) ([]CvarRow, error)
	FindCvar(ctx context.Context, key string) (*CvarRow, error)
	InsertCvarIfMissing(ctx context.Context, row CvarRow) error
	UpdateCvar(ctx context.Context, key string, valueInt int, valueString string) error
}
```

## Proto

```protobuf
message Cvar {
  string key = 1;
  string main_type = 2;
  int32 value_int = 3;
  string value_string = 4;
  string title = 5;
  string description = 6;
  string category = 7;
  int32 ordinal = 8;
}

message ListCvarsRequest {}
message ListCvarsResponse { repeated Cvar cvars = 1; }

message UpdateCvarRequest {
  string key = 1;
  int32 value_int = 2;
  string value_string = 3;
}

// On Init — only SPA-needed flags
message Features {
  bool example_enabled = 1;
}

// Service RPCs (admin-gated in handlers):
//   rpc ListCvars(ListCvarsRequest) returns (ListCvarsResponse);
//   rpc UpdateCvar(UpdateCvarRequest) returns (Cvar);
```

## Ensure on startup

```go
func ensureDefaultCvars(ctx context.Context, st store.Store, siteTitle string) error {
	for _, def := range cvar.Defaults(siteTitle) {
		if err := st.InsertCvarIfMissing(ctx, store.CvarRow{
			Key: def.Key, MainType: def.MainType,
			Title: def.Title, Description: def.Description,
			Category: def.Category, Ordinal: def.Ordinal,
			ValueInt: def.ValueInt, ValueString: def.ValueString,
		}); err != nil {
			return err
		}
	}
	return nil
}
```

## SettingsAdmin.vue skeleton

```vue
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import Section from 'picocrank/vue/components/Section.vue'
import FormLayout from 'picocrank/vue/components/FormLayout.vue'
import FormField from 'picocrank/vue/components/FormField.vue'
import RadioGroup from 'picocrank/vue/components/RadioGroup.vue'
// import client + loadInit from app composables

const cvars = ref([])
const edits = reactive({})
const dirtySections = reactive({})
const error = ref('')
const success = ref('')
const savingSection = ref('')

const booleanOptions = [
  { label: 'On', value: true },
  { label: 'Off', value: false },
]

const categories = computed(() => {
  const groups = []
  const indexByName = {}
  for (const c of cvars.value) {
    const name = c.category || 'Other'
    if (indexByName[name] === undefined) {
      indexByName[name] = groups.length
      groups.push({ name, cvars: [] })
    }
    groups[indexByName[name]].cvars.push(c)
  }
  return groups
})

function labelFor(cvar) {
  return cvar.title || cvar.key.replace(/_/g, ' ')
}
function fieldId(cvar) {
  return `cvar-${cvar.key}`
}
function markDirty(sectionName) {
  dirtySections[sectionName] = true
}

function syncEdits() {
  for (const key of Object.keys(edits)) delete edits[key]
  for (const c of cvars.value) {
    edits[c.key] = {
      valueString: c.valueString || '',
      valueInt: c.valueInt || 0,
      boolValue: !!c.valueInt,
    }
  }
  for (const key of Object.keys(dirtySections)) delete dirtySections[key]
}

function valuesFor(cvar) {
  const edit = edits[cvar.key]
  if (cvar.mainType === 'bool') {
    return { valueInt: edit.boolValue ? 1 : 0, valueString: '' }
  }
  if (cvar.mainType === 'int') {
    return { valueInt: Number(edit.valueInt) || 0, valueString: '' }
  }
  return { valueInt: 0, valueString: edit.valueString || '' }
}

async function load() {
  const res = await client.listCvars({})
  cvars.value = res.cvars || []
  syncEdits()
}

async function saveSection(group) {
  savingSection.value = group.name
  try {
    for (const cvar of group.cvars) {
      const { valueInt, valueString } = valuesFor(cvar)
      await client.updateCvar({ key: cvar.key, valueInt, valueString })
    }
    success.value = `${group.name} settings saved.`
    await load()
    await loadInit()
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    savingSection.value = ''
  }
}

onMounted(load)
</script>

<template>
  <Section title="Settings" subtitle="Configuration variables" :padding="true">
    <p>Site-wide options stored in the database. Edits apply after you save.</p>
    <p v-if="error" class="form-error">{{ error }}</p>
    <p v-if="success" class="flash-success">{{ success }}</p>
  </Section>

  <Section v-for="group in categories" :key="group.name" :title="group.name" :padding="true">
    <FormLayout @submit.prevent="saveSection(group)">
      <template v-for="cvar in group.cvars" :key="cvar.key">
        <!-- string / int FormFields as in Faridoon SettingsAdmin.vue -->
        <FormField v-if="cvar.mainType === 'bool'" :label="labelFor(cvar)" fake>
          <div>
            <RadioGroup
              v-model="edits[cvar.key].boolValue"
              :name="fieldId(cvar)"
              variant="boolean"
              :options="booleanOptions"
              :aria-label="labelFor(cvar)"
              @change="markDirty(group.name)"
            />
            <p v-if="cvar.description" class="subtle">{{ cvar.description }}</p>
          </div>
        </FormField>
      </template>
      <template #actions>
        <button
          type="submit"
          class="button"
          :disabled="!dirtySections[group.name] || savingSection === group.name"
        >
          {{ savingSection === group.name ? 'Saving…' : 'Save' }}
        </button>
      </template>
    </FormLayout>
  </Section>
</template>
```

## Faridoon file map

| Path | Role |
|------|------|
| `service/internal/cvar/cvar.go` | Catalog |
| `service/server_cvars.go` | Upsert, accessors, List/Update |
| `service/internal/store/mysql.go` | `CvarRow`, SQL |
| `database/migrations/*cvar*.sql` | Schema |
| `protocol/proto/.../*.proto` | `Cvar`, RPCs, `Features` |
| `frontend/src/views/SettingsAdmin.vue` | Admin UI |
| `frontend/src/composables/useInit.js` | Feature cache |
| `docs/configuration/index.md` | Operator contract |
