from __future__ import annotations

from pathlib import Path

import typer
import uvicorn

from day0_boot_sim.pcap_sidecar import PcapSidecar
from day0_boot_sim.tftp_server import ReadOnlyTftpServer


app = typer.Typer(help="Synthetic Day 0 boot simulation toolkit.")


@app.command()
def api(host: str = "0.0.0.0", port: int = 8000) -> None:
    uvicorn.run("day0_boot_sim.api:app", host=host, port=port, reload=False)


@app.command()
def dhcp(host: str = "0.0.0.0", port: int = 8100) -> None:
    uvicorn.run("day0_boot_sim.dhcp_service:app", host=host, port=port, reload=False)


@app.command("pcap-sidecar")
def pcap_sidecar() -> None:
    PcapSidecar().run_forever()


@app.command()
def tftp(root: str, host: str = "0.0.0.0", port: int = 6969, health_file: str | None = None) -> None:
    ReadOnlyTftpServer(root=Path(root), host=host, port=port, health_file=health_file).serve_forever()
