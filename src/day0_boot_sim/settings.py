from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DAY0_", extra="ignore")

    service_name: str = "boot-sim"
    log_path: str = "/artifacts/logs/boot-sim.jsonl"
    database_path: str = "/data/day0.db"
    dhcp_service_url: str = "http://dhcp.day0.example:8100"
    http_file_probe_url: str = "http://files.day0.example:8080/"
    http_timeout_seconds: float = 1.0
    max_attempts: int = 3
    backoff_seconds: float = 0.3


class DhcpServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DAY0_DHCP_", extra="ignore")

    log_path: str = "/artifacts/logs/dhcp-service.jsonl"
    http_boot_base_url: str = "http://files.day0.example:8080/bootstrap"
    config_base_url: str = "http://files.day0.example:8080/configs"
    tftp_server_uri: str = "tftp://tftp.day0.example:6969/bootstrap/basic.json"
    slow_response_seconds: float = 1.5


class PcapSidecarSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DAY0_PCAP_", extra="ignore")

    log_path: str = "/artifacts/logs/pcap-sidecar.jsonl"
    api_url: str = "http://boot-sim:8000"
    output_path: str = "/artifacts/pcaps/day0-boot-sim.pcap"
    poll_interval_seconds: float = 1.0
    health_file: str = "/tmp/pcap-sidecar.ready"


class TftpSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DAY0_TFTP_", extra="ignore")

    log_path: str = "/artifacts/logs/tftp-service.jsonl"
