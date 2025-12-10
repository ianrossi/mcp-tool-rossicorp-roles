import argparse
import logging
import os
import sys
import traceback
from typing import Annotated

import requests
from mcp.server.fastmcp import FastMCP, Context


RAG_SERVICE_URL = os.environ.get("RAG_SERVICE_URL", "http://localhost:8002").rstrip("/")
DEFAULT_ACTOR = os.environ.get("RAG_DEFAULT_ACTOR", "mcp-bridge")

mcp = FastMCP(name="mcp-rag-bridge")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def _post_json(path: str, payload: dict) -> dict:
    url = f"{RAG_SERVICE_URL}{path}"
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def rag_query(
    domain: Annotated[str, "Domain to query"],
    query: Annotated[str, "Search query"],
    top_k: Annotated[int, "Number of results"] = 5,
    actor: Annotated[str, "Actor/role for rate limiting and ACLs"] = DEFAULT_ACTOR,
    ctx: Context | None = None,
) -> dict:
    """Query rag-service /query for a domain."""
    payload = {"domain": domain, "query": query, "actor": actor, "top_k": int(top_k)}
    data = _post_json("/query", payload)
    return data


@mcp.tool()
def rag_get_role(
    name: Annotated[str, "Role name to retrieve from rag-service roles domain"],
    top_k: Annotated[int, "Number of matches to return"] = 3,
    actor: Annotated[str, "Actor/role for rate limiting and ACLs"] = DEFAULT_ACTOR,
    ctx: Context | None = None,
) -> dict:
    """Query the 'roles' domain for a role prompt."""
    payload = {"domain": "roles", "query": name, "actor": actor, "top_k": int(top_k)}
    data = _post_json("/query", payload)
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the mcp-rag-bridge server.")
    parser.add_argument("--refresh-only", action="store_true", help="No-op for compatibility.")
    args = parser.parse_args()

    if args.refresh_only:
        logger.info("Nothing to refresh in bridge; exiting.")
        return

    try:
        logger.info("Starting mcp-rag-bridge stdio server (RAG_SERVICE_URL=%s)", RAG_SERVICE_URL)
        mcp.run()
    except Exception:  # pragma: no cover
        logger.error("Fatal error in mcp-rag-bridge server:\n%s", traceback.format_exc())
        sys.stderr.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
