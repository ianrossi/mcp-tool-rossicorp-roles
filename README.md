# mcp-tool-rossicorp-roles

`rossicorp-roles` is an MCP stdio server for managing role prompts in `rag-service`. It provides search plus CRUD/list helpers over the `roles` domain so agents/IDEs can keep role prompts discoverable and up to date. Semver is used for the MCP server and Docker images; current version: `0.2.0`.

## RAG dependency (architecture)
- External service: `rag-service` is the single dependency; point via `RAG_SERVICE_URL` (shared across MCP tools).
- Contracts: this server only calls `/query`, `/ingest`, `/get`, `/list`, `/delete`; no local persistence.
- Multi-tool pattern: each MCP tool container mounts only its code and calls the shared RAG endpoint; keep RAG reachable on the same network (e.g., Compose with `rag-service` or host.docker.internal).
- Tests/CI expect `rag-service` code available (PYTHONPATH to `../rag-service` in this monorepo) or an installed `rag-service` package.

## Tools
- `roles_search(query, top_k=5, actor="rossicorp-roles")`: full-text search across roles.
- `roles_list(limit=100, include_text=false)`: list role ids/metadata (optionally including full text).
- `roles_get(role_id)`: fetch a single role by id.
- `roles_upsert(role_id, text, metadata=None)`: create or update a role prompt.
- `roles_delete(role_id)`: delete a role.

## Configuration
- `RAG_SERVICE_URL` (default `http://localhost:8002`): base URL of `rag-service`.
- `RAG_DEFAULT_ACTOR` (default `rossicorp-roles`): actor passed to `rag-service` for rate limiting.
- `RAG_REQUEST_TIMEOUT` (seconds, default `15`): HTTP timeout for bridge calls.

## Quick start (container-first)
```bash
# Build versioned image (tags 0.2.0 and latest)
docker build -t rossicorp-roles:0.2.0 -t rossicorp-roles:latest .

# Run (connects to host rag-service on 8002)
docker run --rm -i \
  --add-host host.docker.internal:host-gateway \
  -e RAG_SERVICE_URL=http://host.docker.internal:8002 \
  rossicorp-roles:0.2.0
```

### Local dev (optional)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
RAG_SERVICE_URL=http://localhost:8002 python -m rossicorp_roles.server
```

## Testing locally
The test suite boots a `rag-service` instance, ingests a sample role, and exercises the MCP tools end-to-end:
```bash
# Inside this monorepo (has rag-service/):
PYTHONPATH=../rag-service pytest

# Or install rag-service locally first:
pip install rag-service
pytest
```

## Inspector/Codex usage
- Inspector: `npx @modelcontextprotocol/inspector --stdio "python -m rossicorp_roles.server"`
- Codex TOML snippet:
```toml
[mcp_servers.rossicorp-roles]
command = "docker"
args = [
  "run", "--rm", "-i",
  "--add-host", "host.docker.internal:host-gateway",
  "-e", "RAG_SERVICE_URL=http://host.docker.internal:8002",
  "rossicorp-roles:0.2.0"
]
startup_timeout_sec = 20
tool_timeout_sec = 60
```
