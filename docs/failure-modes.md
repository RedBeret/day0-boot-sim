# Failure Modes

## Missing Bootstrap File

How to trigger:

- Use scenario `missing-bootstrap`.

What you should see:

- `FETCH_BOOTSTRAP` occurs.
- The device transitions to `FAILED`.
- The final timeline event is `BOOT_FAILED`.

Recovery:

- Replay with scenario `success`.
- Use `force_reboot = $true` if the device was already in another terminal state.

## Retry and Timeout Path

How to trigger:

- Use scenario `timeout-once`.

What you should see:

- The first DHCP metadata request times out.
- A `RETRY_SCHEDULED` event appears in the timeline.
- A later attempt succeeds and the device reaches `READY`.

Recovery:

- None is required if the later retry succeeds.
- If retries are exhausted, inspect `logs/dhcp-service.jsonl` and rerun the scenario.

## Bad Metadata

How to trigger:

- Use scenario `bad-metadata`.

What you should see:

- Pydantic validation rejects the synthetic DHCP payload.
- The device ends in `FAILED`.
- `last_error` explains which field failed validation.

Recovery:

- Replay with scenario `success`.
- Confirm the new timeline shows a fresh `BOOT_REQUESTED` event followed by a healthy path.

## Dependency Unavailable

How to trigger:

- Stop `http-files` or `dhcp` inside Docker Compose, then boot a device.

What you should see:

- `/health` becomes `degraded`.
- Timeline progression stops before the missing dependency can be used.

Recovery:

- Restart the lab with `pwsh ./scripts/Start-Lab.ps1`.
- Re-run the boot request once `/health` returns `ok`.

## Idempotent Re-Run

How to trigger:

- Run the same `success` scenario twice for the same device without `force_reboot`.

What you should see:

- The first request reaches `READY`.
- The second request returns immediately.
- The final timeline event is `IDEMPOTENT_NOOP`.

Recovery:

- No action is needed.
- Use `force_reboot = $true` only when you intentionally want to replay the workflow.
