# jwr-soa-dbmigrations — reference templates

Copy and adapt. Paths assume the app root is `/var/app` in the image; change as needed.

## dbconfig.yml by driver

### MySQL / MariaDB — `database/mysql/dbconfig.yml`

```yaml
development:
  dialect: mysql
  datasource: ${DB_USER}:${DB_PASS}@tcp(${DB_HOST})/${DB_NAME}?parseTime=true
  dir: migrations
  table: migrations
```

### PostgreSQL — `database/pgsql/dbconfig.yml`

```yaml
development:
  dialect: postgres
  datasource: host=${DB_HOST} user=${DB_USER} password=${DB_PASS} dbname=${DB_NAME} sslmode=disable
  dir: migrations
  table: migrations
```

Adjust `sslmode` for production. Prefer env-driven SSL settings over hardcoding secrets.

### SQLite — `database/sqlite/dbconfig.yml`

```yaml
development:
  dialect: sqlite3
  datasource: ${DB_PATH}
  dir: migrations
  table: migrations
```

`DB_PATH` should be an absolute file path (e.g. `/data/app.db`). Ensure the parent directory is writable.

## Makefile (per driver)

`database/mysql/Makefile` (same for pgsql/sqlite):

```makefile
default:
	sql-migrate up

down:
	sql-migrate down

status:
	sql-migrate status
```

## Dockerfile (sql-migrate + database tree)

```dockerfile
FROM golang:1.25-alpine AS sqlmigrate
RUN go install github.com/rubenv/sql-migrate/sql-migrate@v1.8.1

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=sqlmigrate /go/bin/sql-migrate /usr/bin/sql-migrate
COPY app-service /usr/bin/app-service
COPY database /var/app/database
COPY docker-entrypoint.sh /usr/local/bin/app-entrypoint.sh
RUN chmod +x /usr/local/bin/app-entrypoint.sh /usr/bin/app-service /usr/bin/sql-migrate
ENTRYPOINT ["/usr/local/bin/app-entrypoint.sh"]
```

Pin the sql-migrate module version deliberately; bump intentionally.

## Entrypoint

```sh
#!/bin/sh
set -e

if [ -n "${DB_DATABASE:-}" ] && [ -z "${DB_NAME:-}" ]; then
  export DB_NAME="$DB_DATABASE"
fi
if [ -n "${DB_USERNAME:-}" ] && [ -z "${DB_USER:-}" ]; then
  export DB_USER="$DB_USERNAME"
fi
if [ -n "${DB_PASSWORD:-}" ] && [ -z "${DB_PASS:-}" ]; then
  export DB_PASS="$DB_PASSWORD"
fi

DRIVER="${DB_DRIVER:-mysql}"
case "$DRIVER" in
  mysql|pgsql|sqlite) ;;
  *)
    echo "unsupported DB_DRIVER: $DRIVER" >&2
    exit 1
    ;;
esac

cd "/var/app/database/${DRIVER}" && sql-migrate up
exec /usr/bin/app-service "$@"
```

## Migration id / RequiredMigration test

```go
func TestRequiredMigration(t *testing.T) {
	if RequiredMigration != "12.quotes-content-fulltext.sql" {
		t.Fatalf("migration=%s", RequiredMigration)
	}
}
```

Update the expected string whenever you bump the const.

## Placeholder styles

| Driver | Placeholder |
|--------|-------------|
| MySQL | `?` |
| PostgreSQL | `$1`, `$2`, … |
| SQLite | `?` |

Always pass args to `Query`/`Exec`/`QueryRow` — never fmt user data into the query string.
