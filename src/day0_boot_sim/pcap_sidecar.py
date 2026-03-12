from __future__ import annotations

import hashlib
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from scapy.layers.dhcp import BOOTP, DHCP
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Raw
from scapy.utils import wrpcap

from day0_boot_sim.logging_utils import configure_logging
from day0_boot_sim.models import TimelineEvent
from day0_boot_sim.settings import PcapSidecarSettings


HOST_IP_MAP = {
    "dhcp.day0.example": "198.51.100.53",
    "files.day0.example": "192.0.2.80",
    "config.day0.example": "192.0.2.81",
    "tftp.day0.example": "203.0.113.69",
}


def _timestamp(value: str) -> float:
    return datetime.fromisoformat(value).timestamp()


def _mac_from_device(device_id: str) -> str:
    digest = hashlib.sha256(device_id.encode("utf-8")).digest()
    return f"02:00:{digest[0]:02x}:{digest[1]:02x}:{digest[2]:02x}:{digest[3]:02x}"


def _mac_bytes(mac: str) -> bytes:
    return bytes.fromhex(mac.replace(":", ""))


class PcapSidecar:
    def __init__(self, settings: PcapSidecarSettings | None = None) -> None:
        self.settings = settings or PcapSidecarSettings()
        self.logger = configure_logging("pcap-sidecar", self.settings.log_path)
        self.client = httpx.Client(timeout=2.0)
        self.last_event_ids: dict[str, int] = {}
        self.output_path = Path(self.settings.output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def run_forever(self) -> None:
        Path(self.settings.health_file).write_text("ready", encoding="utf-8")
        while True:
            try:
                self.process_once()
            except Exception as exc:  # pragma: no cover - defensive service loop
                self.logger.info("PCAP sidecar loop failed.", extra={"error": str(exc)})
            time.sleep(self.settings.poll_interval_seconds)

    def process_once(self) -> None:
        devices = self.client.get(f"{self.settings.api_url}/devices").json()
        for device in devices:
            device_id = device["device_id"]
            response = self.client.get(f"{self.settings.api_url}/devices/{device_id}/timeline")
            response.raise_for_status()
            timeline = [TimelineEvent.model_validate(item) for item in response.json()]
            new_events = [event for event in timeline if event.id > self.last_event_ids.get(device_id, 0)]
            if not new_events:
                continue

            packets = []
            for event in new_events:
                packets.extend(self._event_to_packets(event, device))
            if packets:
                wrpcap(str(self.output_path), packets, append=self.output_path.exists())
                self.logger.info(
                    "Wrote synthetic packets to the capture file.",
                    extra={"device_id": device_id, "packet_count": len(packets), "pcap": str(self.output_path)},
                )
            self.last_event_ids[device_id] = new_events[-1].id

    def _event_to_packets(self, event: TimelineEvent, device: dict[str, object]):
        device_id = device["device_id"]
        device_ip = str(device.get("management_ip") or "192.0.2.21")
        dhcp_server_ip = str(device.get("dhcp_server_ip") or "198.51.100.53")
        device_mac = _mac_from_device(device_id)
        stamp = _timestamp(event.occurred_at.isoformat())
        packets = []

        if event.event_type == "DHCP_DISCOVER":
            packet = (
                Ether(src=device_mac, dst="ff:ff:ff:ff:ff:ff")
                / IP(src="0.0.0.0", dst="255.255.255.255")
                / UDP(sport=68, dport=67)
                / BOOTP(chaddr=_mac_bytes(device_mac), xid=0x12345678)
                / DHCP(options=[("message-type", "discover"), ("hostname", device_id), "end"])
            )
            packet.time = stamp
            packets.append(packet)
        elif event.event_type == "DHCP_BOUND":
            packet = (
                Ether(src="02:00:00:53:00:01", dst=device_mac)
                / IP(src=dhcp_server_ip, dst=device_ip)
                / UDP(sport=67, dport=68)
                / BOOTP(yiaddr=device_ip, siaddr=dhcp_server_ip, chaddr=_mac_bytes(device_mac), xid=0x12345678)
                / DHCP(options=[("message-type", "ack"), ("server_id", dhcp_server_ip), "end"])
            )
            packet.time = stamp
            packets.append(packet)
        elif event.event_type == "FETCH_BOOTSTRAP":
            boot_uri = str(event.details.get("boot_file_uri", "http://files.day0.example:8080/bootstrap/basic.json"))
            parsed = urlparse(boot_uri)
            server_ip = HOST_IP_MAP.get(parsed.hostname or "files.day0.example", "192.0.2.80")
            port = parsed.port or 8080
            packet = (
                Ether(src=device_mac, dst="02:00:00:80:00:01")
                / IP(src=device_ip, dst=server_ip)
                / TCP(sport=49152, dport=port, flags="PA", seq=1, ack=1)
                / Raw(load=f"GET {parsed.path} HTTP/1.1\r\nHost: {parsed.netloc}\r\nUser-Agent: day0-boot-sim\r\n\r\n")
            )
            packet.time = stamp
            packets.append(packet)
        elif event.event_type == "APPLY_BOOTSTRAP":
            packet = (
                Ether(src=device_mac, dst="02:00:00:81:00:01")
                / IP(src=device_ip, dst="192.0.2.81")
                / UDP(sport=5514, dport=514)
                / Raw(load=f"apply-bootstrap hostname={event.details.get('hostname', 'unknown')}")
            )
            packet.time = stamp
            packets.append(packet)
        elif event.event_type == "READY":
            packet = (
                Ether(src="02:00:00:80:00:01", dst=device_mac)
                / IP(src="192.0.2.80", dst=device_ip)
                / TCP(sport=8080, dport=49152, flags="PA", seq=2, ack=2)
                / Raw(load="HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"READY\"}")
            )
            packet.time = stamp
            packets.append(packet)

        return packets
