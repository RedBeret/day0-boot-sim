from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import AnyUrl, BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DeviceState(str, Enum):
    INIT = "INIT"
    DHCP_DISCOVER = "DHCP_DISCOVER"
    DHCP_BOUND = "DHCP_BOUND"
    FETCH_BOOTSTRAP = "FETCH_BOOTSTRAP"
    APPLY_BOOTSTRAP = "APPLY_BOOTSTRAP"
    READY = "READY"
    FAILED = "FAILED"


class BootScenario(str, Enum):
    SUCCESS = "success"
    MISSING_BOOTSTRAP = "missing-bootstrap"
    TIMEOUT_ONCE = "timeout-once"
    BAD_METADATA = "bad-metadata"


class BootRequest(BaseModel):
    operator: str = Field(default="bootstrap-operator", pattern=r"^[a-z0-9-]+$")
    scenario: BootScenario = BootScenario.SUCCESS
    force_reboot: bool = False
    requested_at: datetime = Field(default_factory=utc_now)


class DhcpLease(BaseModel):
    device_id: str = Field(pattern=r"^[a-z0-9-]+$")
    boot_file_uri: AnyUrl
    config_server_uri: AnyUrl | None = None
    tftp_server_uri: AnyUrl | None = None
    fake_serial: str = Field(pattern=r"^LABSN-\d{6}$")
    fake_model: str = Field(pattern=r"^LAB-[A-Z0-9-]+$")
    management_ip: str = Field(pattern=r"^\d{1,3}(\.\d{1,3}){3}$")
    dhcp_server_ip: str = Field(pattern=r"^\d{1,3}(\.\d{1,3}){3}$")
    lease_seconds: int = Field(default=1800, ge=60, le=86400)


class BootstrapDocument(BaseModel):
    schema_version: str
    hostname: str
    bootstrap_actions: list[str] = Field(min_length=1)
    final_state: str = Field(pattern=r"^READY$")
    config_server_uri: AnyUrl | None = None
    checksum_seed: str = Field(min_length=3)

    @field_validator("hostname")
    @classmethod
    def hostname_must_be_synthetic(cls, value: str) -> str:
        if not value.endswith(".day0.example"):
            raise ValueError("hostname must use the synthetic .day0.example suffix")
        return value


class DeviceRecord(BaseModel):
    device_id: str = Field(pattern=r"^[a-z0-9-]+$")
    state: DeviceState = DeviceState.INIT
    scenario: BootScenario = BootScenario.SUCCESS
    operator: str = Field(default="bootstrap-operator", pattern=r"^[a-z0-9-]+$")
    serial: str | None = None
    model: str | None = None
    management_ip: str | None = None
    dhcp_server_ip: str | None = None
    boot_file_uri: str | None = None
    config_server_uri: str | None = None
    bootstrap_checksum: str | None = None
    last_error: str | None = None
    ready: bool = False
    last_boot_at: datetime | None = None


class TimelineEvent(BaseModel):
    id: int
    device_id: str
    state: DeviceState
    event_type: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime


class HealthResponse(BaseModel):
    status: str
    service: str
    database_path: str
    dependencies: dict[str, str]
