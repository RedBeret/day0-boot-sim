from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from logging import Logger

from pydantic import ValidationError

from day0_boot_sim.exceptions import Day0BootSimError, NonRetryableGatewayError, RetryableGatewayError
from day0_boot_sim.models import BootRequest, DeviceRecord, DeviceState
from day0_boot_sim.storage import Storage


DEVICE_ID_PATTERN = re.compile(r"^[a-z0-9-]{3,50}$")


class BootOrchestrator:
    def __init__(
        self,
        storage: Storage,
        gateway,
        logger: Logger,
        max_attempts: int,
        backoff_seconds: float,
        sleep_fn=time.sleep,
    ) -> None:
        self.storage = storage
        self.gateway = gateway
        self.logger = logger
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.sleep_fn = sleep_fn

    def boot_device(self, device_id: str, request: BootRequest) -> DeviceRecord:
        if not DEVICE_ID_PATTERN.fullmatch(device_id):
            raise ValueError("device_id must contain only lowercase letters, digits, and hyphens")

        existing = self.storage.get_device(device_id)
        if existing and existing.ready and not request.force_reboot and existing.scenario == request.scenario:
            self._event(
                device_id,
                DeviceState.READY,
                "IDEMPOTENT_NOOP",
                "Device already READY for the requested scenario; no changes applied.",
                {"scenario": request.scenario.value},
            )
            return existing

        device = existing or DeviceRecord(device_id=device_id)
        device = device.model_copy(
            update={
                "state": DeviceState.INIT,
                "scenario": request.scenario,
                "operator": request.operator,
                "ready": False,
                "last_error": None,
            }
        )
        device = self.storage.upsert_device(device)
        self._event(
            device_id,
            DeviceState.INIT,
            "BOOT_REQUESTED",
            "Synthetic Day 0 boot requested.",
            {
                "scenario": request.scenario.value,
                "force_reboot": request.force_reboot,
                "operator": request.operator,
            },
        )

        try:
            if request.force_reboot and existing and existing.ready:
                self._event(
                    device_id,
                    DeviceState.INIT,
                    "FORCE_REBOOT",
                    "Force reboot requested; replaying the synthetic workflow.",
                    {"previous_state": existing.state.value},
                )

            device = self._transition(device, DeviceState.DHCP_DISCOVER)
            self._event(
                device_id,
                DeviceState.DHCP_DISCOVER,
                "DHCP_DISCOVER",
                "Requesting synthetic DHCP metadata.",
                {"scenario": request.scenario.value},
            )
            lease = self._retry(
                device_id=device_id,
                state=DeviceState.DHCP_DISCOVER,
                operation="dhcp-metadata",
                func=lambda: self.gateway.get_lease(device_id, request.scenario),
            )

            device = device.model_copy(
                update={
                    "state": DeviceState.DHCP_BOUND,
                    "serial": lease.fake_serial,
                    "model": lease.fake_model,
                    "management_ip": lease.management_ip,
                    "dhcp_server_ip": lease.dhcp_server_ip,
                    "boot_file_uri": str(lease.boot_file_uri),
                    "config_server_uri": str(lease.config_server_uri) if lease.config_server_uri else None,
                }
            )
            device = self.storage.upsert_device(device)
            self._event(
                device_id,
                DeviceState.DHCP_BOUND,
                "DHCP_BOUND",
                "Synthetic DHCP lease bound.",
                {
                    "boot_file_uri": str(lease.boot_file_uri),
                    "config_server_uri": str(lease.config_server_uri) if lease.config_server_uri else None,
                    "management_ip": lease.management_ip,
                    "dhcp_server_ip": lease.dhcp_server_ip,
                    "fake_serial": lease.fake_serial,
                    "fake_model": lease.fake_model,
                },
            )

            device = self._transition(device, DeviceState.FETCH_BOOTSTRAP)
            self._event(
                device_id,
                DeviceState.FETCH_BOOTSTRAP,
                "FETCH_BOOTSTRAP",
                "Fetching synthetic bootstrap document.",
                {"boot_file_uri": str(lease.boot_file_uri)},
            )
            bootstrap = self._retry(
                device_id=device_id,
                state=DeviceState.FETCH_BOOTSTRAP,
                operation="bootstrap-fetch",
                func=lambda: self.gateway.fetch_bootstrap(str(lease.boot_file_uri)),
            )

            checksum = hashlib.sha256(
                json.dumps(bootstrap.model_dump(mode="json"), sort_keys=True).encode("utf-8")
            ).hexdigest()
            device = device.model_copy(
                update={
                    "state": DeviceState.APPLY_BOOTSTRAP,
                    "bootstrap_checksum": checksum,
                    "config_server_uri": str(bootstrap.config_server_uri or lease.config_server_uri)
                    if (bootstrap.config_server_uri or lease.config_server_uri)
                    else None,
                }
            )
            device = self.storage.upsert_device(device)
            self._event(
                device_id,
                DeviceState.APPLY_BOOTSTRAP,
                "APPLY_BOOTSTRAP",
                "Applying synthetic bootstrap actions.",
                {
                    "hostname": bootstrap.hostname,
                    "action_count": len(bootstrap.bootstrap_actions),
                    "checksum": checksum,
                    "final_state": bootstrap.final_state,
                },
            )

            ready_at = datetime.now(timezone.utc)
            device = device.model_copy(
                update={
                    "state": DeviceState.READY,
                    "ready": True,
                    "last_error": None,
                    "last_boot_at": ready_at,
                }
            )
            device = self.storage.upsert_device(device)
            self._event(
                device_id,
                DeviceState.READY,
                "READY",
                "Synthetic device reached READY state.",
                {"last_boot_at": ready_at.isoformat()},
            )
            return device
        except (RetryableGatewayError, NonRetryableGatewayError, ValidationError, Day0BootSimError, ValueError) as exc:
            failed_at = datetime.now(timezone.utc)
            device = device.model_copy(
                update={
                    "state": DeviceState.FAILED,
                    "ready": False,
                    "last_error": str(exc),
                    "last_boot_at": failed_at,
                }
            )
            device = self.storage.upsert_device(device)
            self._event(
                device_id,
                DeviceState.FAILED,
                "BOOT_FAILED",
                "Synthetic boot failed.",
                {"error": str(exc), "failed_at": failed_at.isoformat()},
            )
            return device

    def get_health(self, database_path: str, service_name: str) -> dict[str, object]:
        dependencies = self.gateway.dependency_health()
        status = "ok" if self.storage.health() and all(value == "ok" for value in dependencies.values()) else "degraded"
        return {
            "status": status,
            "service": service_name,
            "database_path": database_path,
            "dependencies": dependencies,
        }

    def _transition(self, device: DeviceRecord, state: DeviceState) -> DeviceRecord:
        updated = device.model_copy(update={"state": state})
        return self.storage.upsert_device(updated)

    def _retry(self, device_id: str, state: DeviceState, operation: str, func):
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return func()
            except RetryableGatewayError as exc:
                last_error = exc
                if attempt >= self.max_attempts:
                    break
                delay = round(self.backoff_seconds * (2 ** (attempt - 1)), 3)
                self._event(
                    device_id,
                    state,
                    "RETRY_SCHEDULED",
                    f"{operation} failed temporarily; scheduling retry.",
                    {
                        "operation": operation,
                        "attempt": attempt,
                        "next_delay_seconds": delay,
                        "error": str(exc),
                    },
                )
                self.sleep_fn(delay)
            except NonRetryableGatewayError:
                raise
        raise RetryableGatewayError(f"{operation} exhausted retries: {last_error}")

    def _event(
        self,
        device_id: str,
        state: DeviceState,
        event_type: str,
        message: str,
        details: dict[str, object],
    ) -> None:
        occurred_at = datetime.now(timezone.utc)
        self.storage.add_timeline_event(
            device_id=device_id,
            state=state.value,
            event_type=event_type,
            message=message,
            details=details,
            occurred_at=occurred_at,
        )
        self.logger.info(
            message,
            extra={
                "device_id": device_id,
                "state": state.value,
                "event_type": event_type,
                **details,
            },
        )
