from __future__ import annotations

import argparse
import logging
import os
import sys
import traceback
from typing import Annotated, Any, Dict, Optional

from mcp.server.fastmcp import Context, FastMCP
from rossicorp_roles.rag_client import RagClient


RAG_SERVICE_URL = os.environ.get("RAG_SERVICE_URL", "http://localhost:8002").rstrip("/")
DEFAULT_ACTOR = os.environ.get("RAG_DEFAULT_ACTOR", "rossicorp-roles")
REQUEST_TIMEOUT = int(os.environ.get("RAG_REQUEST_TIMEOUT", "15"))

mcp = FastMCP(name="rossicorp-roles")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


client = RagClient(RAG_SERVICE_URL, request_timeout=REQUEST_TIMEOUT)


@mcp.tool()
def roles_search(
    query: Annotated[str, "Full-text search query for the roles domain"],
    top_k: Annotated[int, "Number of matches to return"] = 5,
    actor: Annotated[str, "Actor/role for rate limiting and ACLs"] = DEFAULT_ACTOR,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Search the roles domain in rag-service."""
    return client.query(domain="roles", query=query, top_k=top_k, actor=actor)


@mcp.tool()
def roles_list(
    limit: Annotated[int, "Maximum roles to return"] = 100,
    include_text: Annotated[bool, "Include full role prompts"] = False,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """List roles stored in rag-service."""
    return client.list(domain="roles", limit=limit, include_text=include_text)


@mcp.tool()
def roles_get(
    role_id: Annotated[str, "Role id (doc_id) to retrieve"],
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Fetch a single role by id."""
    return client.get(domain="roles", doc_id=role_id)


@mcp.tool()
def roles_upsert(
    role_id: Annotated[str, "Role id (doc_id) to create or update"],
    text: Annotated[str, "Role prompt text"],
    metadata: Annotated[Dict[str, Any] | None, "Optional metadata to store with the role"] = None,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Create or update a role in the roles domain."""
    return client.upsert(domain="roles", doc_id=role_id, text=text, metadata=metadata)


@mcp.tool()
def roles_delete(
    role_id: Annotated[str, "Role id (doc_id) to delete"],
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Delete a role from the roles domain."""
    return client.delete(domain="roles", doc_id=role_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the rossicorp-roles MCP server.")
    parser.add_argument("--refresh-only", action="store_true", help="No-op for compatibility.")
    args = parser.parse_args()

    if args.refresh_only:
        logger.info("Nothing to refresh in rossicorp-roles; exiting.")
        return

    try:
        logger.info("Starting rossicorp-roles stdio server (RAG_SERVICE_URL=%s)", RAG_SERVICE_URL)
        mcp.run()
    except Exception:  # pragma: no cover
        logger.error("Fatal error in rossicorp-roles server:\n%s", traceback.format_exc())
        sys.stderr.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
