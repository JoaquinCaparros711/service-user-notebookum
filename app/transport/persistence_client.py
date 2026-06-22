"""HTTP client for communicating with downstream persistence microservice."""

from typing import Any, Dict, Optional
from flask import current_app
import requests


class PersistenceClient:
    """HTTP Client for communicating with the Persistence microservice."""

    def __init__(self, base_url: Optional[str] = None):
        self._base_url = base_url

    @property
    def base_url(self) -> str:
        return self._base_url or current_app.config.get("PERSISTENCE_URL", "")

    def post_user(self, payload: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        return requests.post(
            f"{self.base_url}/api/v1/users",
            json=payload,
            headers=headers,
            timeout=5,
            verify=False
        )

    def get_user_by_id(self, user_id: int, headers: Dict[str, str]) -> requests.Response:
        return requests.get(
            f"{self.base_url}/api/v1/users/{user_id}",
            headers=headers,
            timeout=5,
            verify=False
        )

    def patch_user(self, user_id: int, payload: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        return requests.patch(
            f"{self.base_url}/api/v1/users/{user_id}",
            json=payload,
            headers=headers,
            timeout=5,
            verify=False
        )

    def delete_user(self, user_id: int, headers: Dict[str, str]) -> requests.Response:
        return requests.delete(
            f"{self.base_url}/api/v1/users/{user_id}",
            headers=headers,
            timeout=5,
            verify=False
        )

    def get_user_by_email(self, email: str, headers: Dict[str, str]) -> requests.Response:
        return requests.get(
            f"{self.base_url}/api/v1/users/email/{email}",
            headers=headers,
            timeout=5,
            verify=False
        )
