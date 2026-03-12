# ADR-002: Make Windows PowerShell the Primary Entrypoint

## Status

Accepted

## Context

The host requirement is Windows-first, but some tooling is Linux-native. The repo needs a single user path that starts from Windows and delegates Linux-only behavior into Docker or WSL2.

## Decision

Use PowerShell 7 wrapper scripts as the primary entrypoint:

- `scripts/Start-Lab.ps1`
- `scripts/Stop-Lab.ps1`
- `scripts/Invoke-Demo.ps1`

Use Docker Compose and the WSL `Makefile` only behind that host-facing workflow.

## Consequences

- Windows users get a one-command demo path.
- Linux-only tools stay in containers or WSL2.
- Documentation can teach one canonical path first and Linux-side tasks second.
