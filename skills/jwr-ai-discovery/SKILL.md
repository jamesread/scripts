---
name: jwr-ai-discovery
description: >-
  Expose llms.txt, /openapi, and /mcp endpoints so LLMs and AI agents can discover
  and integrate with a web service. Use when adding AI/agent discovery surfaces,
  MCP server integration, OpenAPI exposure, llms.txt, AGENTS.md, or mcp-go setup
  to a Go (Connect/gRPC) or similar HTTP service.
---

# AI & Agent Discovery Endpoints

Expose three complementary surfaces on the **same base URL** as the web app:

| Surface | Path | Purpose |
|---------|------|---------|
| `llms.txt` | `/llms.txt` | Human/LLM-readable index of integration options |
| OpenAPI | `/openapi` | Machine-readable REST/OpenAPI spec for the API |
| MCP | `/mcp` | Model Context Protocol tools for AI assistants |

Reference implementation: [SickRock](https://github.com/jamesread/SickRock) (`service/main.go`, `service/llms.txt`, `service/internal/mcp/server.go`).

## Architecture

```
Browser / LLM / MCP client
        │
        ├── GET /llms.txt     → static discovery doc (text/plain)
        ├── GET /openapi      → embedded OpenAPI JSON
        ├── ANY /mcp          → MCP Streamable HTTP (auth required)
        └── /api/*            → Connect/gRPC-over-HTTP API
```

All three discovery endpoints share the app's origin. MCP and the API use the **same auth** (no separate MCP credentials).

---

## 1. llms.txt

### Purpose

[llms.txt](https://llmstxt.org/) is a plain-text index at the site root. Crawlers, LLMs, and developers use it to find API docs, MCP, and related resources without scraping HTML.

### File location and content

Place `llms.txt` next to the server binary (e.g. `service/llms.txt`). Use this structure:

```markdown
# {AppName}

> One-line description. Mention Connect RPC, OpenAPI, and/or MCP as applicable.

Brief paragraph: machine-readable endpoints live on the same base URL as the web app.

Document authentication once, clearly:

`Authorization: Bearer <api-key>`

Explain where to create keys and that MCP and the API share auth.

## API

- [Connect RPC API](/api): {description} (prefix `/api`)
- [OpenAPI spec](/openapi): OpenAPI 3.1 JSON description of the Connect RPC API

## MCP

- [MCP server](/mcp): Model Context Protocol (Streamable HTTP) endpoint for AI assistants and agents

## Documentation

- [GitHub repository](https://github.com/{org}/{repo}): Source code, issues, and releases
- [README](https://github.com/{org}/{repo}#readme): Project overview and setup
- [AGENTS.md](https://github.com/{org}/{repo}/blob/main/AGENTS.md): AI agent integration guide and MCP tool reference
```

Use **relative paths** for same-origin links (`/openapi`, `/mcp`, `/api`). Use absolute URLs only for external docs (GitHub, llmstxt.org).

### Serving (Go)

Embed and serve **before** SPA/static fallback:

```go
//go:embed llms.txt
var llmsTxt []byte

router.GET("/llms.txt", func(c *gin.Context) {
    c.Header("Content-Type", "text/plain; charset=utf-8")
    c.Data(http.StatusOK, "text/plain; charset=utf-8", llmsTxt)
})
```

### Service worker

If the frontend has a service worker, add `/llms.txt` to a network-only bypass list so cached SPA shells never intercept it:

```javascript
const BYPASS_PATHS = ['/llms.txt', '/openapi', '/openapi.json'];
```

---

## 2. /openapi

### Purpose

Publish a stable OpenAPI 3.x JSON document so agents, codegen tools, and documentation generators can consume the API without protobuf tooling.

### Generation (Connect + buf)

For Connect RPC services, generate OpenAPI from protobuf via buf:

```yaml
# proto/buf.gen.yaml
plugins:
  - remote: buf.build/community/sudorandom-connect-openapi:v0.22.1
    out: ../service/gen
    opt:
      - format=json
      - path=openapi.json
      - path-prefix=/api    # must match HTTP mount prefix
```

Run `buf generate` in CI and locally. Commit `service/gen/openapi.json`.

### Serving (Go)

Embed the generated file; do not read from disk at runtime:

```go
//go:embed gen/openapi.json
var openAPISpec []byte

router.GET("/openapi", func(c *gin.Context) {
    c.Header("Content-Type", "application/json")
    c.Data(http.StatusOK, "application/json", openAPISpec)
})
```

Register this route before SPA `NoRoute` fallback. Add `/openapi` to service-worker bypass paths.

### Checklist

- [ ] `path-prefix` in buf plugin matches API mount (e.g. `/api`)
- [ ] OpenAPI regenerated when protobuf changes
- [ ] `llms.txt` links to `/openapi`
- [ ] `AGENTS.md` references OpenAPI for non-MCP integrations

---

## 3. /mcp (embedded HTTP MCP)

### Purpose

Expose high-value API operations as **MCP tools** on the same server. AI clients (Cursor, Claude Desktop, etc.) connect via **Streamable HTTP** at `/mcp` — no separate MCP process required in production.

### Go library

Use [mark3labs/mcp-go](https://github.com/mark3labs/mcp-go):

```go
import (
    "github.com/mark3labs/mcp-go/mcp"
    "github.com/mark3labs/mcp-go/server"
)
```

Add to `go.mod`:

```
github.com/mark3labs/mcp-go v0.49.0
```

### Package layout

```
service/
  internal/mcp/
    server.go      # NewHandler(srv) → http.Handler
  cmd/{app}-mcp/   # optional stdio proxy for local dev
    main.go
    README.md
```

### Handler pattern

1. Create MCP server with name, version, recovery.
2. Register one tool per API operation (`AddTool` + handler).
3. Handlers call the **same business layer** as Connect RPC handlers (not a duplicate HTTP client in-process).
4. Return JSON text results; map API errors to `mcp.NewToolResultError`.
5. Wrap with Streamable HTTP:

```go
func NewHandler(srv *YourServer) http.Handler {
    mcpServer := server.NewMCPServer(
        "YourApp",
        "1.0.0",
        server.WithToolCapabilities(false),
        server.WithRecovery(),
    )

    mcpServer.AddTool(mcp.NewTool("yourapp_ping",
        mcp.WithDescription("Health check."),
        mcp.WithString("message", mcp.Description("Optional message to echo")),
    ), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
        // delegate to srv.Ping(ctx, ...)
        return jsonResult(result)
    })

    // ... more tools ...

    return server.NewStreamableHTTPServer(mcpServer, server.WithEndpointPath("/mcp"))
}
```

Tool naming: prefix with app slug and snake_case, e.g. `sickrock_list_items`.

Parameter docs: use `mcp.WithString("field", mcp.Required(), mcp.Description("..."))`.

### Auth middleware

MCP must use the **same auth as the API**. Run auth middleware before the MCP handler:

```go
mcpHandler := mcp.NewHandler(srv)
router.Any("/mcp", mcpAuthMiddleware(authService), gin.WrapH(mcpHandler))
router.Any("/mcp/*path", mcpAuthMiddleware(authService), gin.WrapH(mcpHandler))
```

Middleware should:

- Reject unauthenticated/guest requests with `401`
- Put authenticated user on `request.Context()` (same keys as Connect interceptors)
- Propagate read-only API key flags for mutating tools

Mutating MCP tools must check read-only context and return a clear tool error.

### Tool selection

Start with a small, high-value set:

- Health/ping
- List/discover resources (navigation, schemas, configs)
- Read operations (get, list)
- Write operations (create, update, delete) — gated by auth

Document every tool in `AGENTS.md` with name, parameters, and behavior.

### Optional: stdio MCP binary

For MCP clients that only support stdio (older Cursor setups), ship `cmd/{app}-mcp`:

- Reads `APP_API_KEY` and `APP_API_URL` from env
- Connect RPC client with Bearer interceptor
- Same tools as embedded server
- `server.ServeStdio(mcpServer)` instead of Streamable HTTP

Prefer embedded `/mcp` when the app is reachable over HTTP.

### Cursor client config (HTTP transport)

```json
{
  "mcpServers": {
    "yourapp": {
      "url": "https://your-host/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

Exact schema varies by client; point at `{baseUrl}/mcp` with the same Bearer token as the API.

---

## 4. AGENTS.md (companion doc)

Add `AGENTS.md` at the repo root. It expands what `llms.txt` links to:

- Project overview for AI agents
- MCP endpoint URL, transport, auth
- Table of MCP tools with descriptions
- Key RPC/API endpoints agents may call directly
- Development and security notes

Keep `llms.txt` short; keep detailed tool/API reference in `AGENTS.md`.

---

## 5. Route ordering and SPA safety

Register discovery routes **before** static files and SPA fallback:

```go
router.Any("/api/*any", ...)   // API first
router.GET("/openapi", ...)
router.GET("/llms.txt", ...)
router.Any("/mcp", auth, mcpHandler)
router.Any("/mcp/*path", auth, mcpHandler)
// static assets, then NoRoute → index.html
```

Ensure `NoRoute` does not swallow `/llms.txt`, `/openapi`, or `/mcp`.

---

## 6. Implementation checklist

When adding AI discovery to a new or existing service:

```
- [ ] Create service/llms.txt (llmstxt.org format, auth section, relative links)
- [ ] Add AGENTS.md with MCP tool reference
- [ ] Generate OpenAPI from protobuf (buf plugin) or hand-maintain spec
- [ ] //go:embed llms.txt and gen/openapi.json in main
- [ ] GET /llms.txt and GET /openapi handlers
- [ ] internal/mcp/server.go with mcp-go Streamable HTTP
- [ ] Shared auth middleware on /mcp
- [ ] Register /mcp before SPA fallback; bypass in service worker
- [ ] Optional cmd/{app}-mcp for stdio clients
- [ ] CI: buf generate (or equivalent) keeps openapi.json current
```

---

## 7. SickRock reference summary

| Artifact | Location |
|----------|----------|
| Route registration | `service/main.go` |
| llms.txt content | `service/llms.txt` |
| MCP tools | `service/internal/mcp/server.go` |
| Stdio MCP | `service/cmd/sickrock-mcp/` |
| OpenAPI generation | `proto/buf.gen.yaml` → `service/gen/openapi.json` |
| Agent docs | `AGENTS.md` |
| SW bypass | `frontend/public/sw.js` |

**llms.txt (SickRock):**

```markdown
# SickRock

> No-code database web application builder for real databases. Integrate via the Connect RPC API, OpenAPI spec, or MCP server.

SickRock exposes machine-readable integration endpoints on the same base URL as the web application.

Both MCP clients and API clients must authenticate with a Bearer token (API key) in the `Authorization` header:

`Authorization: Bearer <api-key>`

Create API keys in the SickRock UI (Settings → API Keys). The MCP server and Connect API use the same authentication.

## API

- [Connect RPC API](/api): SickRock Connect/gRPC-over-HTTP API (prefix `/api`)
- [OpenAPI spec](/openapi): OpenAPI 3.1 JSON description of the Connect RPC API

## MCP

- [MCP server](/mcp): Model Context Protocol (Streamable HTTP) endpoint for AI assistants and agents

## Documentation

- [GitHub repository](https://github.com/jamesread/SickRock): Source code, issues, and releases
- [README](https://github.com/jamesread/SickRock#readme): Project overview and setup
- [AGENTS.md](https://github.com/jamesread/SickRock/blob/main/AGENTS.md): AI agent integration guide and MCP tool reference
```

**MCP tools (SickRock):** `sickrock_ping`, `sickrock_get_navigation`, `sickrock_get_table_configurations`, `sickrock_get_database_tables`, `sickrock_get_table_structure`, `sickrock_list_items`, `sickrock_get_item`, `sickrock_create_item`, `sickrock_edit_item`, `sickrock_delete_item`.
