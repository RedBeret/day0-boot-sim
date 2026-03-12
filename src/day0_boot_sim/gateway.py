from __future__ import annotations

import httpx

from day0_boot_sim.exceptions import NonRetryableGatewayError, ResourceMissingError, RetryableGatewayError
from day0_boot_sim.models import BootScenario, BootstrapDocument, DhcpLease


class ServiceGateway:
    def __init__(
        self,
        dhcp_service_url: str,
        timeout_seconds: float,
        http_file_probe_url: str,
    ) -> None:
        self.dhcp_client = httpx.Client(base_url=dhcp_service_url, timeout=timeout_seconds)
        self.http_client = httpx.Client(timeout=timeout_seconds)
        self.http_file_probe_url = http_file_probe_url

    def get_lease(self, device_id: str, scenario: BootScenario) -> DhcpLease:
        try:
            response = self.dhcp_client.get(f"/lease/{device_id}", params={"scenario": scenario.value})
        except httpx.TimeoutException as exc:
            raise RetryableGatewayError(f"DHCP metadata request timed out for {device_id}") from exc
        except httpx.HTTPError as exc:
            raise RetryableGatewayError(f"DHCP metadata request failed for {device_id}: {exc}") from exc
        return self._validate_response(response, device_id, response_type="dhcp")

    def fetch_bootstrap(self, boot_file_uri: str) -> BootstrapDocument:
        try:
            response = self.http_client.get(boot_file_uri)
        except httpx.TimeoutException as exc:
            raise RetryableGatewayError(f"Bootstrap fetch timed out for {boot_file_uri}") from exc
        except httpx.HTTPError as exc:
            raise RetryableGatewayError(f"Bootstrap fetch failed for {boot_file_uri}: {exc}") from exc
        return self._validate_response(response, boot_file_uri, response_type="bootstrap")

    def dependency_health(self) -> dict[str, str]:
        return {
            "dhcp": self._probe(self.dhcp_client, "/health"),
            "http_files": self._probe(self.http_client, self.http_file_probe_url),
        }

    @staticmethod
    def _probe(client: httpx.Client, path_or_url: str) -> str:
        try:
            response = client.get(path_or_url)
            response.raise_for_status()
            return "ok"
        except httpx.HTTPError:
            return "unavailable"

    @staticmethod
    def _validate_response(response: httpx.Response, resource: str, response_type: str):
        if response.status_code == 404:
            raise ResourceMissingError(f"Synthetic resource not found: {resource}")
        if response.status_code >= 500:
            raise RetryableGatewayError(f"Temporary upstream failure for {resource}: HTTP {response.status_code}")
        if response.status_code >= 400:
            raise NonRetryableGatewayError(f"Permanent upstream failure for {resource}: HTTP {response.status_code}")

        payload = response.json()
        if response_type == "dhcp":
            return DhcpLease.model_validate(payload)
        return BootstrapDocument.model_validate(payload)
