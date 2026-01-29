import os
from typing import Any, Dict, Optional

import requests


class PendoClient:
    def __init__(self, base_url: Optional[str] = None, integration_key: Optional[str] = None) -> None:
        self.base_url = (base_url or os.environ.get("PENDO_BASE_URL") or "https://app.pendo.io").rstrip("/")
        self.integration_key = (
            integration_key
            or os.environ.get("PENDO_INTEGRATION_KEY")
            or os.environ.get("PENDO_API_KEY")
            or os.environ.get("PENDO_TOKEN")
        )
        if not self.integration_key:
            raise ValueError(
                "Missing Pendo integration key. Set PENDO_INTEGRATION_KEY (preferred) or PENDO_API_KEY."
            )

        timeout_env = os.environ.get("PENDO_REQUEST_TIMEOUT_SECONDS")
        self.timeout_seconds = int(timeout_env) if timeout_env else 60

    def run_query(self, query_payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/aggregation"
        headers = {
            "x-pendo-integration-key": self.integration_key,
            "content-type": "application/json",
        }
        response = requests.post(url, headers=headers, json=query_payload, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()
