from __future__ import annotations

import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from day0_boot_sim.logging_utils import configure_logging
from day0_boot_sim.models import BootScenario, DhcpLease
from day0_boot_sim.settings import DhcpServiceSettings


_ATTEMPT_COUNTER: dict[tuple[str, str], int] = {}


def create_app(settings: DhcpServiceSettings | None = None) -> FastAPI:
    settings = settings or DhcpServiceSettings()
    logger = configure_logging("dhcp-service", settings.log_path)
    app = FastAPI(title="synthetic-dhcp-service", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "dhcp-service"}

    @app.get("/lease/{device_id}")
    def get_lease(device_id: str, scenario: BootScenario = BootScenario.SUCCESS):
        key = (device_id, scenario.value)
        _ATTEMPT_COUNTER[key] = _ATTEMPT_COUNTER.get(key, 0) + 1
        attempt = _ATTEMPT_COUNTER[key]

        if scenario == BootScenario.TIMEOUT_ONCE and attempt == 1:
            logger.info(
                "Delaying first response to force a retry path.",
                extra={"device_id": device_id, "scenario": scenario.value, "attempt": attempt},
            )
            time.sleep(settings.slow_response_seconds)

        if scenario == BootScenario.BAD_METADATA:
            payload = {
                "device_id": device_id,
                "boot_file_uri": "http://files.day0.example:8080/bootstrap/%%%invalid",
                "config_server_uri": "http://files.day0.example:8080/configs/edge-lab-01.json",
                "tftp_server_uri": settings.tftp_server_uri,
                "fake_serial": "LABSN-ABCDEF",
                "fake_model": "LAB-CPE-48X",
                "management_ip": "192.0.2.21",
                "dhcp_server_ip": "198.51.100.53",
                "lease_seconds": 1800,
            }
            logger.info(
                "Returning intentionally bad metadata for training.",
                extra={"device_id": device_id, "scenario": scenario.value},
            )
            return JSONResponse(payload)

        seed = sum(ord(char) for char in device_id)
        host_octet = 20 + (seed % 40)
        boot_file_name = "missing.json" if scenario == BootScenario.MISSING_BOOTSTRAP else "basic.json"
        lease = DhcpLease(
            device_id=device_id,
            boot_file_uri=f"{settings.http_boot_base_url}/{boot_file_name}",
            config_server_uri=f"{settings.config_base_url}/edge-lab-01.json",
            tftp_server_uri=settings.tftp_server_uri,
            fake_serial=f"LABSN-{(100000 + seed % 900000):06d}",
            fake_model="LAB-CPE-48X" if seed % 2 == 0 else "LAB-EDGE-12S",
            management_ip=f"192.0.2.{host_octet}",
            dhcp_server_ip="198.51.100.53",
            lease_seconds=1800,
        )
        logger.info(
            "Issued synthetic DHCP metadata.",
            extra={"device_id": device_id, "scenario": scenario.value, "attempt": attempt},
        )
        return lease.model_dump(mode="json")

    return app


app = create_app()
