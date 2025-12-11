# Rossicorp Roles MCP Tool - SPEC

## Purpose & Scope
- Expose role management (search, CRUD, list) for the `roles` domain in `rag-service` via MCP stdio.
- Keep contracts small: call only `/query`, `/ingest`, `/get`, `/list`, `/delete` on `rag-service`.

## Tools
- `roles_search(query, top_k=5, actor="rossicorp-roles")` → `{success, results[]}`.
- `roles_list(limit=100, include_text=false)` → `{success, results[]}`.
- `roles_get(role_id)` → `{success, result}` or `{success:false, error}`.
- `roles_upsert(role_id, text, metadata=None)` → `{success:true, id}`.
- `roles_delete(role_id)` → `{success:true, deleted}` or error.

## Transport & Config
- Transport: MCP stdio (FastMCP).
- Env:
  - `RAG_SERVICE_URL` (default `http://localhost:8002`)
  - `RAG_DEFAULT_ACTOR` (default `rossicorp-roles`)
  - `RAG_REQUEST_TIMEOUT` (default `15` seconds)

## Dependencies
- External: `rag-service` reachable over HTTP; no local storage.
- Tests/CI: requires `rag-service` importable (PYTHONPATH to `../rag-service` in this monorepo) or installed as a package.

## Versioning & Release
- Semver; current version `0.2.0`.
- Docker image tags: `rossicorp-roles:<version>` and `rossicorp-roles:latest`.

## CI
- GitHub Actions (containerized): pip install, pytest, then build versioned Docker image tags.

## Client Snippets
- Codex:
  ```
  [mcp_servers.rossicorp-roles]
  command = "docker"
  args = [
    "run","--rm","-i",
    "--add-host","host.docker.internal:host-gateway",
    "-e","RAG_SERVICE_URL=http://host.docker.internal:8002",
    "rossicorp-roles:0.2.0"
  ]
  ```
