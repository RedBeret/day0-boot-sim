# Contributing

Thanks for taking a look at `day0-boot-sim`.

This repo is meant to stay easy to run, easy to explain, and safe to publish. If you want to contribute, please optimize for clarity and training value over cleverness.

## Ground Rules

- Keep the repo local-only and synthetic.
- Do not add real credentials, customer data, proprietary images, or real device identifiers.
- Keep the primary user path on Windows PowerShell.
- Linux-only tooling should stay in Docker or WSL2.
- Prefer small, explicit changes over large framework jumps.

## Development Workflow

### Windows host

```powershell
pwsh ./scripts/Start-Lab.ps1
pwsh ./scripts/Invoke-Demo.ps1
pwsh ./scripts/Stop-Lab.ps1
```

### WSL2 Ubuntu

```bash
make install
make test
```

## Code Style

- Prefer Python 3.12 features when they improve readability.
- Keep structured logging intact.
- Preserve explicit validation, retries, timeouts, idempotency, and health checks.
- Favor deterministic artifacts over environment-specific behavior.
- Use fake hostnames, fake serials, and RFC 5737 example IPs.

## Docs

If you change the workflow, update the docs in the same pass:

- `README.md`
- `docs/runbook.md`
- `docs/failure-modes.md`
- `docs/engineering-notes.md`

## Test Expectations

Please keep these scenarios covered:

- successful boot
- missing bootstrap file
- retry and timeout path
- idempotent re-run
