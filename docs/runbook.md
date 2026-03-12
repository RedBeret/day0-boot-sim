# Runbook

## 1. Start the Lab From Windows PowerShell

```powershell
pwsh ./scripts/Start-Lab.ps1
```

Expected result:

- Docker Compose starts the synthetic services.
- `http://localhost:8000/health` returns `status: ok`.
- `logs/` begins receiving JSONL logs.

Rollback notes:

- If startup fails, run `pwsh ./scripts/Stop-Lab.ps1` to stop partially started containers.
- No customer data exists in the stack, so rollback is limited to stopping containers and preserving artifacts for review.

## 2. Run the Under-5-Minute Demo

```powershell
pwsh ./scripts/Invoke-Demo.ps1
```

Expected result:

- The synthetic device `edge-lab-01` reaches `READY`.
- Timeline JSON lands in `reports/edge-lab-01-timeline.json`.
- A summary lands in `reports/demo-summary.json`.
- A synthetic capture lands in `pcaps/day0-boot-sim.pcap`.

Rollback notes:

- If the demo ends in `FAILED`, inspect `reports/health.json`, `reports/devices.json`, and `logs/*.jsonl`.
- Then either re-run the same command for an idempotent replay or stop the lab with `pwsh ./scripts/Stop-Lab.ps1`.

## 3. Trigger a Manual Boot Scenario

Happy path:

```powershell
$body = @{
  operator = "bootstrap-operator"
  scenario = "success"
  force_reboot = $false
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://localhost:8000/devices/edge-lab-01/boot -ContentType application/json -Body $body
```

Failure drill:

```powershell
$body = @{
  operator = "bootstrap-operator"
  scenario = "missing-bootstrap"
  force_reboot = $true
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://localhost:8000/devices/edge-lab-01/boot -ContentType application/json -Body $body
```

Other supported scenarios:

- `success`
- `missing-bootstrap`
- `timeout-once`
- `bad-metadata`

Rollback notes:

- If a manual scenario leaves the device in `FAILED`, rerun a `success` boot with `force_reboot = $true`.
- If you want to stop instead of replaying, use `pwsh ./scripts/Stop-Lab.ps1`. This preserves the failure evidence.

## 4. Inspect Health and Timeline

```powershell
Invoke-RestMethod -Method Get -Uri http://localhost:8000/health
Invoke-RestMethod -Method Get -Uri http://localhost:8000/devices
Invoke-RestMethod -Method Get -Uri http://localhost:8000/devices/edge-lab-01/timeline
```

This workflow is read-only, so no rollback action is needed.

## 5. Stop the Lab

```powershell
pwsh ./scripts/Stop-Lab.ps1
```

Expected result:

- Containers stop and are removed.
- `logs/`, `pcaps/`, `reports/`, and `data/` remain for review.

Rollback notes:

- If you stopped the lab accidentally, rerun `pwsh ./scripts/Start-Lab.ps1`.
- Since state is stored in `data/day0.db`, the lab resumes with the same synthetic history unless you manually delete the database.
