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


def test_bridge_can_get_role(rag_url):
    # Ingest the toolsmith role into rag-service
    ingest_payload = {
        "domain": "roles",
        "doc_id": "mcp_toolsmith",
        "text": ROLE_TEXT,
        "metadata": {"kind": "role"},
    }
    resp = requests.post(f"{rag_url}/ingest", json=ingest_payload, timeout=5)
    assert resp.status_code == 200, resp.text

    # Start MCP bridge pointing at rag-service
    env = os.environ.copy()
    env["RAG_SERVICE_URL"] = rag_url
    bridge_cmd = [sys.executable, "-m", "mcp_rag_bridge.server"]
    proc = subprocess.Popen(
        bridge_cmd,
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
        assert "result" in init and init["result"]["serverInfo"]["name"] == "mcp-rag-bridge"

        tools = _jsonrpc_call(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool_names = [t["name"] for t in tools["result"]["tools"]]
        assert "rag_get_role" in tool_names

        role_res = _jsonrpc_call(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "rag_get_role",
                    "arguments": {"name": "MCP Toolsmith", "top_k": 1},
                },
            },
        )
        content = role_res["result"]["content"][0]["text"]
        assert "MCP Toolsmith Role" in content
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
