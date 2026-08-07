---
name: jwr-soa-dbmigrations
description: >-
  Implements sql-migrate database migrations for jwr SOA apps: driver-split SQL
  scripts under database/mysql/, database/pgsql/, and database/sqlite/, applied
  at container startup or via make in development, with a RequiredMigration
  compile-time constant that fails service startup if missing. Use when adding
  or changing schema migrations, sql-migrate setup, Dockerfile entrypoint
  migrate-on-start, database Makefiles, or when ORMs/raw SQL access patterns
  are discussed. ORMs are forbidden; prefer prepared statements.
---

# jwr-soa-dbmigrations

Schema changes are **versioned SQL files** applied with [sql-migrate](https://github.com/rubenv/sql-migrate). The service never auto-migrates itself in-process; migrations run **before** the binary starts (container entrypoint) or via **`make`** in development. At startup the service checks a compile-time **required migration id** and refuses to run if that row is absent from the `migrations` table.

Inspired by **Faridoon** (`database/`, `docker-entrypoint.sh`, `config.RequiredMigration`, `assertMigration`). Faridoon keeps a single MySQL tree under `database/migrations/`; **new apps must use driver-split directories** (below).

Companion: [jwr-soa-2.0](../jwr-soa-2.0/SKILL.md) (store interface, no ORM). Templates: [reference.md](reference.md).

## Principles

1. **sql-migrate only** — numbered `.sql` files with `-- +migrate Up` / `-- +migrate Down`. No GORM, ent, Bun, sqlc-as-migrator, or hand-rolled migrators.
2. **ORMs are forbidden** — use `database/sql` (or equivalent) behind a store interface. Prefer **prepared statements** / placeholders (`?`, `$1`, …) for all parameterized queries; never concatenate user input into SQL.
3. **Driver-split trees** — migrations live under the driver directory, not a shared `migrations/` folder:
   - `database/mysql/`
   - `database/pgsql/`
   - `database/sqlite/`
4. **Apply outside the process** — `sql-migrate up` in the container entrypoint (production/runtime) and via `make` (dev). The Go service only **asserts** the expected version.
5. **RequiredMigration const** — bump the constant to the newest migration filename whenever the binary depends on that schema. Fail fast on mismatch.

## Directory layout

```
database/
  mysql/
    dbconfig.yml
    Makefile
    migrations/
      0.base.sql
      1.groups.sql
      …
  pgsql/
    dbconfig.yml
    Makefile
    migrations/
      …
  sqlite/
    dbconfig.yml
    Makefile
    migrations/
      …
```

Ship only the drivers the app supports. Keep migration **ids (filenames) aligned across drivers** when the same logical change exists for each (e.g. `9.cvars.sql` in mysql and pgsql), even if SQL dialects differ inside the files.

### Naming

- `{n}.{short-kebab-description}.sql` — integer prefix, then a stable slug (e.g. `12.quotes-content-fulltext.sql`).
- The **sql-migrate id** is the filename; that string is what `RequiredMigration` must match.
- Always include both Up and Down when practical.

```sql
-- +migrate Up
CREATE TABLE example (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- +migrate Down
DROP TABLE IF EXISTS example;
```

## dbconfig.yml

One config per driver directory. Dialect and `dir` must match that tree. Datasource uses env vars so entrypoint/`make` share the same file.

MySQL example (`database/mysql/dbconfig.yml`):

```yaml
development:
  dialect: mysql
  datasource: ${DB_USER}:${DB_PASS}@tcp(${DB_HOST})/${DB_NAME}?parseTime=true
  dir: migrations
  table: migrations
```

Postgres and SQLite variants: see [reference.md](reference.md). Table name stays `migrations` so store helpers stay consistent.

## Applying migrations

### Development (`make`)

Each driver dir has a Makefile whose default target runs `sql-migrate up` (cwd = that directory so `dbconfig.yml` resolves):

```makefile
default:
	sql-migrate up
```

Developers run:

```bash
make -C database/mysql
# or
cd database/mysql && make
```

Optional root Makefile wrappers (`make migrate`, `make migrate-pgsql`) are fine; they must `cd` into the correct driver directory.

### Runtime (Dockerfile / entrypoint)

1. Image includes the `sql-migrate` binary and the `database/` tree.
2. Entrypoint runs `sql-migrate up` in the **active driver** directory, then `exec`s the service.

```sh
#!/bin/sh
set -e
# map legacy env names if needed (DB_DATABASE → DB_NAME, etc.)
DRIVER="${DB_DRIVER:-mysql}"
cd "/var/app/database/${DRIVER}" && sql-migrate up
exec /usr/bin/app-service "$@"
```

Pin sql-migrate in the image (Faridoon pattern: multi-stage `go install github.com/rubenv/sql-migrate/sql-migrate@v…`).

Document required env vars for operators (`DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`, and `DB_DRIVER` when multi-dialect).

## Required migration check (service)

### Constant

```go
// RequiredMigration is the sql-migrate id this binary expects to be applied.
const RequiredMigration = "12.quotes-content-fulltext.sql"
```

Update this **in the same change** that adds a migration the binary depends on. Add/adjust a unit test that asserts the constant equals the expected filename so bumps are intentional.

### Startup assert

After opening the DB and before serving traffic:

1. Query whether `RequiredMigration` exists in `migrations`.
2. If the table cannot be read → error telling the operator to run `sql-migrate up`.
3. If the id is missing → error with required vs latest applied id.
4. Log the latest migration id on success.

```go
func assertMigration(ctx context.Context, st Store, required string) error {
	ok, err := st.HasMigration(ctx, required)
	if err != nil {
		return fmt.Errorf("connected to the database, but the migrations table could not be queried. run sql-migrate up: %w", err)
	}
	if ok {
		return nil
	}
	latest, _ := st.LatestMigration(ctx)
	if latest == "" {
		latest = "null"
	}
	return fmt.Errorf("requires database version %s but the database is at version %s; run database migrations", required, latest)
}
```

### Store helpers

Use prepared / parameterized queries:

```go
func (m *MySQL) HasMigration(ctx context.Context, id string) (bool, error) {
	var n int
	err := m.db.QueryRowContext(ctx,
		`SELECT COUNT(*) FROM migrations WHERE id = ?`, id).Scan(&n)
	return n > 0, err
}

func (m *MySQL) LatestMigration(ctx context.Context) (string, error) {
	var id sql.NullString
	err := m.db.QueryRowContext(ctx,
		`SELECT id FROM migrations ORDER BY applied_at DESC, id DESC LIMIT 1`).Scan(&id)
	// …
}
```

Postgres uses `$1` placeholders; SQLite typically `?`. Keep driver-specific SQL in the driver store implementation.

## Access layer rules

| Do | Do not |
|----|--------|
| `database/sql` + store interface | GORM, ent, Bun, ActiveRecord-style ORMs |
| Placeholders / prepared statements | String-built SQL with unsanitized input |
| Explicit SQL in store packages | Hiding schema behind opaque ORM models |
| Migrations as the schema source of truth | Auto-migrate / `CREATE TABLE` inside app init |

## Docs

Operator docs should cover:

- That migrations run on container start (`sql-migrate up` in the entrypoint)
- How to run manually (`make -C database/<driver>` or exec into the container)
- Current `RequiredMigration` id and what the latest migration does
- Env vars for `dbconfig.yml`

## Implementation checklist

When adding migrations to an app:

- [ ] `database/{mysql,pgsql,sqlite}/` trees as needed, each with `migrations/`, `dbconfig.yml`, `Makefile`
- [ ] sql-migrate binary in the container image
- [ ] Entrypoint: `cd database/$DRIVER && sql-migrate up` then exec service
- [ ] `config.RequiredMigration` (or equivalent) + unit test for the const value
- [ ] Store: `HasMigration`, `LatestMigration` with parameterized SQL
- [ ] Startup: `assertMigration` before handlers/cvars/etc.
- [ ] Docs: install/migrate page + env vars
- [ ] No ORM; queries use prepared statements

When adding a **new** migration later:

1. Add `N.name.sql` under each supported driver (dialect-appropriate SQL)
2. Bump `RequiredMigration` if the binary needs that schema
3. Update the const unit test and operator docs
4. Apply with `make -C database/<driver>` (dev) or redeploy (runtime entrypoint)

## Anti-patterns

- Single shared `database/migrations/` for multi-driver apps (use driver directories)
- Running migrations inside Go `init` / main instead of entrypoint + make
- Shipping a binary that soft-continues when the required migration is missing
- Using an ORM or query builder that owns schema
- Interpolating values into SQL strings instead of prepared statements
- Forgetting to bump `RequiredMigration` when code depends on a new column/table
