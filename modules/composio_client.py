#!/usr/bin/env python3
"""
Composio MCP Tool Connector
Permet d'exécuter de manière centralisée et robuste les outils ScrapeCreators & SerpAPI
via l'infrastructure Composio MCP JSON-RPC.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger("ComposioMCPClient")

COMPOSIO_MCP_URL = os.getenv("COMPOSIO_MCP_URL", "https://connect.composio.dev/mcp")
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY", "ck_-mFSLh8Kv2PesnUSgQDZ")


def call_composio_tool(tool_slug: str, arguments: Dict[str, Any], timeout: int = 45) -> Optional[Dict[str, Any]]:
    """
    Exécute un outil ScrapeCreators / Composio via le transport MCP JSON-RPC
    avec l'authentification gérée par la clé API instantanée.
    """
    headers = {
        "x-consumer-api-key": COMPOSIO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "COMPOSIO_MULTI_EXECUTE_TOOL",
            "arguments": {
                "sync_response_to_workbench": False,
                "tools": [{
                    "tool_slug": tool_slug,
                    "arguments": arguments
                }]
            }
        }
    }

    try:
        resp = requests.post(COMPOSIO_MCP_URL, headers=headers, json=payload, timeout=timeout)
        if resp.status_code != 200:
            logger.warning(f"Composio MCP HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        raw_text = resp.text
        for line in raw_text.splitlines():
            line_str = line.strip()
            if line_str.startswith("data: "):
                data_json = json.loads(line_str[6:])
                result_obj = data_json.get("result", {})
                content_list = result_obj.get("content", [])
                if content_list and content_list[0].get("type") == "text":
                    inner_text = content_list[0].get("text", "{}")
                    inner_data = json.loads(inner_text)
                    results = inner_data.get("data", {}).get("results", [])
                    if results and len(results) > 0:
                        first_resp = results[0].get("response", {})
                        return first_resp.get("data") or first_resp.get("data_preview")
                    return inner_data.get("data") or inner_data.get("data_preview")

        try:
            direct_json = resp.json()
            result_obj = direct_json.get("result", {})
            content_list = result_obj.get("content", [])
            if content_list and content_list[0].get("type") == "text":
                inner_text = content_list[0].get("text", "{}")
                inner_data = json.loads(inner_text)
                results = inner_data.get("data", {}).get("results", [])
                if results and len(results) > 0:
                    first_resp = results[0].get("response", {})
                    return first_resp.get("data") or first_resp.get("data_preview")
                return inner_data.get("data") or inner_data.get("data_preview")
        except Exception:
            pass

        return None
    except Exception as e:
        logger.error(f"Erreur d'appel Composio ({tool_slug}): {e}")
        return None
