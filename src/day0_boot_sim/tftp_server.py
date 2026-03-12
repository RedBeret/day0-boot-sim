from __future__ import annotations

import socket
import struct
from pathlib import Path

from day0_boot_sim.logging_utils import configure_logging
from day0_boot_sim.settings import TftpSettings


RRQ = 1
DATA = 3
ACK = 4
ERROR = 5
BLOCK_SIZE = 512


def _read_rrq(payload: bytes) -> tuple[str, str]:
    parts = payload[2:].split(b"\x00")
    if len(parts) < 2:
        raise ValueError("invalid RRQ packet")
    filename = parts[0].decode("utf-8")
    mode = parts[1].decode("utf-8").lower()
    return filename, mode


def _data_packet(block: int, chunk: bytes) -> bytes:
    return struct.pack("!HH", DATA, block) + chunk


def _error_packet(code: int, message: str) -> bytes:
    return struct.pack("!HH", ERROR, code) + message.encode("utf-8") + b"\x00"


class ReadOnlyTftpServer:
    def __init__(self, root: Path, host: str, port: int, health_file: str | None = None) -> None:
        settings = TftpSettings()
        self.root = root.resolve()
        self.host = host
        self.port = port
        self.health_file = Path(health_file) if health_file else None
        self.logger = configure_logging("tftp-service", settings.log_path)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def serve_forever(self) -> None:
        self.socket.bind((self.host, self.port))
        if self.health_file:
            self.health_file.write_text("ready", encoding="utf-8")
        self.logger.info("Synthetic TFTP service started.", extra={"host": self.host, "port": self.port})
        while True:
            payload, address = self.socket.recvfrom(2048)
            self._handle_request(payload, address)

    def _handle_request(self, payload: bytes, address: tuple[str, int]) -> None:
        opcode = struct.unpack("!H", payload[:2])[0]
        if opcode != RRQ:
            self.socket.sendto(_error_packet(4, "Only RRQ is supported"), address)
            return

        try:
            filename, mode = _read_rrq(payload)
        except ValueError:
            self.socket.sendto(_error_packet(0, "Malformed RRQ"), address)
            return

        if mode != "octet":
            self.socket.sendto(_error_packet(0, "Only octet mode is supported"), address)
            return

        file_path = (self.root / filename).resolve()
        if self.root not in file_path.parents and file_path != self.root:
            self.socket.sendto(_error_packet(2, "Access violation"), address)
            return
        if not file_path.exists() or not file_path.is_file():
            self.socket.sendto(_error_packet(1, "File not found"), address)
            return

        self.logger.info("Serving synthetic TFTP file.", extra={"filename": filename, "client": str(address)})
        with file_path.open("rb") as handle:
            block = 1
            while True:
                chunk = handle.read(BLOCK_SIZE)
                packet = _data_packet(block, chunk)
                if not self._send_with_ack(packet, block, address):
                    self.logger.info(
                        "Synthetic TFTP transfer abandoned after retries.",
                        extra={"filename": filename, "block": block},
                    )
                    return
                if len(chunk) < BLOCK_SIZE:
                    return
                block = 1 if block == 65535 else block + 1

    def _send_with_ack(self, packet: bytes, block: int, address: tuple[str, int]) -> bool:
        for _ in range(3):
            self.socket.sendto(packet, address)
            self.socket.settimeout(1.0)
            try:
                ack, ack_address = self.socket.recvfrom(1024)
            except socket.timeout:
                continue
            finally:
                self.socket.settimeout(None)
            if ack_address != address:
                continue
            if len(ack) >= 4 and struct.unpack("!HH", ack[:4]) == (ACK, block):
                return True
        return False
