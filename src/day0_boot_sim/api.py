from __future__ import annotations

from fastapi import FastAPI, HTTPException

from day0_boot_sim.gateway import ServiceGateway
from day0_boot_sim.logging_utils import configure_logging
from day0_boot_sim.models import BootRequest, DeviceRecord, HealthResponse, TimelineEvent
from day0_boot_sim.orchestrator import BootOrchestrator
from day0_boot_sim.settings import AppSettings
from day0_boot_sim.storage import Storage


def create_app(
    settings: AppSettings | None = None,
    storage: Storage | None = None,
    gateway: ServiceGateway | None = None,
) -> FastAPI:
    settings = settings or AppSettings()
    logger = configure_logging(settings.service_name, settings.log_path)
    storage = storage or Storage(settings.database_path)
    storage.initialize()
    gateway = gateway or ServiceGateway(
        dhcp_service_url=settings.dhcp_service_url,
        timeout_seconds=settings.http_timeout_seconds,
        http_file_probe_url=settings.http_file_probe_url,
    )
    orchestrator = BootOrchestrator(
        storage=storage,
        gateway=gateway,
        logger=logger,
        max_attempts=settings.max_attempts,
        backoff_seconds=settings.backoff_seconds,
    )

    app = FastAPI(title="day0-boot-sim", version="0.1.0")
    app.state.settings = settings
    app.state.storage = storage
    app.state.orchestrator = orchestrator

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        payload = orchestrator.get_health(settings.database_path, settings.service_name)
        return HealthResponse.model_validate(payload)

    @app.get("/devices", response_model=list[DeviceRecord])
    def list_devices() -> list[DeviceRecord]:
        return storage.list_devices()

    @app.post("/devices/{device_id}/boot", response_model=DeviceRecord)
    def boot_device(device_id: str, request: BootRequest | None = None) -> DeviceRecord:
        try:
            return orchestrator.boot_device(device_id, request or BootRequest())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/devices/{device_id}/timeline", response_model=list[TimelineEvent])
    def get_timeline(device_id: str) -> list[TimelineEvent]:
        if storage.get_device(device_id) is None:
            raise HTTPException(status_code=404, detail="Unknown device_id")
        return storage.get_timeline(device_id)

    return app


app = create_app()
