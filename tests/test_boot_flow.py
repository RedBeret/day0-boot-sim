from pathlib import Path

from day0_boot_sim.exceptions import ResourceMissingError, RetryableGatewayError
from day0_boot_sim.logging_utils import configure_logging
from day0_boot_sim.models import BootRequest, BootstrapDocument, DhcpLease, DeviceState
from day0_boot_sim.orchestrator import BootOrchestrator
from day0_boot_sim.storage import Storage


class FakeGateway:
    def __init__(self, lease, bootstrap, lease_errors=None, bootstrap_errors=None):
        self.lease = lease
        self.bootstrap = bootstrap
        self.lease_errors = list(lease_errors or [])
        self.bootstrap_errors = list(bootstrap_errors or [])
        self.lease_calls = 0
        self.bootstrap_calls = 0

    def get_lease(self, device_id, scenario):
        self.lease_calls += 1
        if self.lease_errors:
            raise self.lease_errors.pop(0)
        return self.lease

    def fetch_bootstrap(self, boot_file_uri):
        self.bootstrap_calls += 1
        if self.bootstrap_errors:
            raise self.bootstrap_errors.pop(0)
        return self.bootstrap

    @staticmethod
    def dependency_health():
        return {"dhcp": "ok", "http_files": "ok"}


def make_lease(device_id: str = "edge-lab-01") -> DhcpLease:
    return DhcpLease(
        device_id=device_id,
        boot_file_uri="http://files.day0.example:8080/bootstrap/basic.json",
        config_server_uri="http://files.day0.example:8080/configs/edge-lab-01.json",
        tftp_server_uri="tftp://tftp.day0.example:6969/bootstrap/basic.json",
        fake_serial="LABSN-123456",
        fake_model="LAB-CPE-48X",
        management_ip="192.0.2.21",
        dhcp_server_ip="198.51.100.53",
        lease_seconds=1800,
    )


def make_bootstrap() -> BootstrapDocument:
    return BootstrapDocument(
        schema_version="2026-03-11",
        hostname="edge-lab-01.day0.example",
        bootstrap_actions=[
            "set-system-hostname edge-lab-01.day0.example",
            "register-with-config-server http://files.day0.example:8080/configs/edge-lab-01.json",
        ],
        final_state="READY",
        config_server_uri="http://files.day0.example:8080/configs/edge-lab-01.json",
        checksum_seed="basic-bootstrap-v1",
    )


def make_orchestrator(tmp_path: Path, gateway: FakeGateway):
    storage = Storage(str(tmp_path / "day0.db"))
    storage.initialize()
    logger = configure_logging(f"test-orchestrator-{tmp_path.name}", str(tmp_path / "logs" / "test.jsonl"))
    orchestrator = BootOrchestrator(
        storage=storage,
        gateway=gateway,
        logger=logger,
        max_attempts=3,
        backoff_seconds=0.01,
        sleep_fn=lambda _: None,
    )
    return orchestrator, storage


def test_successful_boot(tmp_path: Path):
    gateway = FakeGateway(lease=make_lease(), bootstrap=make_bootstrap())
    orchestrator, storage = make_orchestrator(tmp_path, gateway)

    result = orchestrator.boot_device("edge-lab-01", BootRequest())

    assert result.state == DeviceState.READY
    assert result.ready is True
    assert result.serial == "LABSN-123456"
    assert gateway.lease_calls == 1
    assert gateway.bootstrap_calls == 1

    event_types = [event.event_type for event in storage.get_timeline("edge-lab-01")]
    assert event_types == [
        "BOOT_REQUESTED",
        "DHCP_DISCOVER",
        "DHCP_BOUND",
        "FETCH_BOOTSTRAP",
        "APPLY_BOOTSTRAP",
        "READY",
    ]


def test_missing_bootstrap_file(tmp_path: Path):
    gateway = FakeGateway(
        lease=make_lease(),
        bootstrap=make_bootstrap(),
        bootstrap_errors=[ResourceMissingError("Synthetic resource not found: missing.json")],
    )
    orchestrator, storage = make_orchestrator(tmp_path, gateway)

    result = orchestrator.boot_device("edge-lab-01", BootRequest())

    assert result.state == DeviceState.FAILED
    assert result.ready is False
    assert "missing.json" in (result.last_error or "")
    assert storage.get_timeline("edge-lab-01")[-1].event_type == "BOOT_FAILED"


def test_retry_and_timeout_path(tmp_path: Path):
    gateway = FakeGateway(
        lease=make_lease(),
        bootstrap=make_bootstrap(),
        lease_errors=[RetryableGatewayError("simulated timeout on first attempt")],
    )
    orchestrator, storage = make_orchestrator(tmp_path, gateway)

    result = orchestrator.boot_device("edge-lab-01", BootRequest())

    assert result.state == DeviceState.READY
    assert gateway.lease_calls == 2
    event_types = [event.event_type for event in storage.get_timeline("edge-lab-01")]
    assert "RETRY_SCHEDULED" in event_types


def test_idempotent_rerun(tmp_path: Path):
    gateway = FakeGateway(lease=make_lease(), bootstrap=make_bootstrap())
    orchestrator, storage = make_orchestrator(tmp_path, gateway)

    first = orchestrator.boot_device("edge-lab-01", BootRequest())
    second = orchestrator.boot_device("edge-lab-01", BootRequest())

    assert first.state == DeviceState.READY
    assert second.state == DeviceState.READY
    assert gateway.bootstrap_calls == 1

    timeline = storage.get_timeline("edge-lab-01")
    assert timeline[-1].event_type == "IDEMPOTENT_NOOP"
    assert sum(1 for event in timeline if event.event_type == "APPLY_BOOTSTRAP") == 1
