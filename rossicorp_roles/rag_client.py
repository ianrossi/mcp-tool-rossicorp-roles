from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class RagClient:
    """Lightweight HTTP client for rag-service with domain-agnostic helpers."""

    def __init__(self, base_url: str, request_timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = requests.post(url, json=payload, timeout=self.request_timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:  # pragma: no cover - surfaced to caller
            raise RuntimeError(f"rag-service request failed for {path}: {exc}") from exc

    def query(self, domain: str, query: str, top_k: int, actor: str) -> Dict[str, Any]:
        payload = {"domain": domain, "query": query, "actor": actor, "top_k": int(top_k)}
        return self._post("/query", payload)

    def list(self, domain: str, limit: int = 100, include_text: bool = False) -> Dict[str, Any]:
        payload = {"domain": domain, "limit": int(limit), "include_text": bool(include_text)}
        return self._post("/list", payload)

    def get(self, domain: str, doc_id: str) -> Dict[str, Any]:
        payload = {"domain": domain, "doc_id": doc_id}
        return self._post("/get", payload)

    def upsert(self, domain: str, doc_id: str, text: str, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {"domain": domain, "doc_id": doc_id, "text": text, "metadata": metadata or {}}
        return self._post("/ingest", payload)

    def delete(self, domain: str, doc_id: str) -> Dict[str, Any]:
        payload = {"domain": domain, "doc_id": doc_id}
        return self._post("/delete", payload)
