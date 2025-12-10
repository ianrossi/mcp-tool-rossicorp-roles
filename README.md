# mcp-rag-bridge

MCP stdio server that forwards queries to `rag-service` so agents can retrieve roles and knowledge via MCP tools.

## What it exposes
- **Tools**
  - `rag_query(domain, query, top_k=5, actor="mcp-bridge")`: call `rag-service` `/query`.
  - `rag_get_role(name, top_k=3, actor="mcp-bridge")`: query the `roles` domain for a role prompt (expects role docs ingested into rag-service; this repo does not store roles).

## Configuration
- `RAG_SERVICE_URL` (default `http://localhost:8002`): base URL of `rag-service`.
- `RAG_DEFAULT_ACTOR` (default `mcp-bridge`): actor/role passed to rag-service.

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
RAG_SERVICE_URL=http://localhost:8002 python -m mcp_rag_bridge.server
```

## Testing locally
The repo ships a test that starts `rag-service` (uvicorn) on a random free port, ingests a test role into the `roles` domain, then runs the MCP bridge via JSON-RPC stdio:
```bash
pip install -e .
pip install rag-service  # or run from the local rag-service source tree
pytest
```

## Inspector/Codex usage
- Inspector: `npx @modelcontextprotocol/inspector --stdio "python -m mcp_rag_bridge.server"`
- Codex TOML snippet:
```toml
[mcp_servers.mcp-rag-bridge]
command = "python"
args = ["-m", "mcp_rag_bridge.server"]
env = { RAG_SERVICE_URL = "http://localhost:8002" }
startup_timeout_sec = 20
tool_timeout_sec = 60
```
