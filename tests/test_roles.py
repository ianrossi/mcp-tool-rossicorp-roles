import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests


ROOT = Path(__file__).resolve().parent.parent
ROLE_TEXT = """# MCP Toolsmith Role
You are an MCP toolsmith. Design, implement, test, and wire MCP servers/clients using the official spec and client configs. Use Inspector to validate initialize/tools/list/tools/call."""


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for(url: str, timeout: float = 10.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=1)
            if resp.status_code == 200:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"Service at {url} did not become ready")


def _jsonrpc_call(proc: subprocess.Popen, msg: dict) -> dict:
    line = json.dumps(msg) + "\n"
    assert proc.stdin
    proc.stdin.write(line)
    proc.stdin.flush()
    assert proc.stdout
    resp_line = proc.stdout.readline()
    if not resp_line:
        raise RuntimeError("No response from MCP bridge")
    return json.loads(resp_line)


@pytest.fixture(scope="session")
def rag_url():
    port = _find_free_port()
    env = os.environ.copy()
    # Ensure rag-service source is importable
    rag_repo = ROOT.parent / "rag-service"
    env["PYTHONPATH"] = f"{rag_repo}:{env.get('PYTHONPATH','')}"
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "rag.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        _wait_for(f"http://127.0.0.1:{port}/health")
        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_roles_server_crud_and_search(rag_url):
    env = os.environ.copy()
    env["RAG_SERVICE_URL"] = rag_url
    server_cmd = [sys.executable, "-m", "rossicorp_roles.server"]
    proc = subprocess.Popen(
        server_cmd,
        env=env,
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        init = _jsonrpc_call(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0.0.1"},
                },
            },
        )
        assert "result" in init and init["result"]["serverInfo"]["name"] == "rossicorp-roles"

        tools = _jsonrpc_call(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool_names = {t["name"] for t in tools["result"]["tools"]}
        expected = {"roles_search", "roles_list", "roles_get", "roles_upsert", "roles_delete"}
        assert expected.issubset(tool_names)

        # Upsert a role via MCP
        upsert_res = _jsonrpc_call(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "roles_upsert",
                    "arguments": {"role_id": "mcp_toolsmith", "text": ROLE_TEXT, "metadata": {"kind": "role"}},
                },
            },
        )
        assert upsert_res["result"]["content"][0]["text"].startswith("{")

        # Fetch it
        get_res = _jsonrpc_call(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "roles_get", "arguments": {"role_id": "mcp_toolsmith"}},
            },
        )
        fetched = json.loads(get_res["result"]["content"][0]["text"])
        assert fetched["success"] is True
        assert "Toolsmith Role" in fetched["result"]["text"]

        # Search
        search_res = _jsonrpc_call(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "roles_search", "arguments": {"query": "toolsmith", "top_k": 2}},
            },
        )
        search_data = json.loads(search_res["result"]["content"][0]["text"])
        assert search_data["results"][0]["id"] == "mcp_toolsmith"

        # List
        list_res = _jsonrpc_call(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {"name": "roles_list", "arguments": {"include_text": False}},
            },
        )
        list_data = json.loads(list_res["result"]["content"][0]["text"])
        assert list_data["results"][0]["id"] == "mcp_toolsmith"
        assert "text" not in list_data["results"][0]

        # Delete
        delete_res = _jsonrpc_call(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {"name": "roles_delete", "arguments": {"role_id": "mcp_toolsmith"}},
            },
        )
        delete_data = json.loads(delete_res["result"]["content"][0]["text"])
        assert delete_data["deleted"] is True

        # List again to confirm empty
        list_after = _jsonrpc_call(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {"name": "roles_list", "arguments": {}},
            },
        )
        list_after_data = json.loads(list_after["result"]["content"][0]["text"])
        assert list_after_data["results"] == []
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
