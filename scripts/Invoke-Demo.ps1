[CmdletBinding()]
param(
    [string]$DeviceId = "edge-lab-01",
    [switch]$WithTftp,
    [int]$TimeoutSeconds = 300
)

. (Join-Path $PSScriptRoot "_Common.ps1")

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "PowerShell 7 or newer is required. Run this with pwsh."
}

$repoRoot = Get-RepoRoot
Ensure-ArtifactDirectories -RepoRoot $repoRoot

& (Join-Path $PSScriptRoot "Start-Lab.ps1") -WithTftp:$WithTftp -StartupTimeoutSeconds ([Math]::Min($TimeoutSeconds, 120))

$bootBody = @{
    operator = "bootstrap-operator"
    scenario = "success"
    force_reboot = $false
}

$bootResult = Invoke-RestMethod `
    -Uri "http://localhost:8000/devices/$DeviceId/boot" `
    -Method Post `
    -TimeoutSec 30 `
    -ContentType "application/json" `
    -Body ($bootBody | ConvertTo-Json -Depth 5)

$timeline = Invoke-RestMethod -Uri "http://localhost:8000/devices/$DeviceId/timeline" -Method Get -TimeoutSec 10
$devices = Invoke-RestMethod -Uri "http://localhost:8000/devices" -Method Get -TimeoutSec 10
$health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 10

$timelinePath = Join-Path $repoRoot "reports\$DeviceId-timeline.json"
$summaryPath = Join-Path $repoRoot "reports\demo-summary.json"
$devicesPath = Join-Path $repoRoot "reports\devices.json"
$healthPath = Join-Path $repoRoot "reports\health.json"
$pcapPath = Join-Path $repoRoot "pcaps\day0-boot-sim.pcap"

Write-JsonArtifact -InputObject $timeline -Path $timelinePath
Write-JsonArtifact -InputObject $devices -Path $devicesPath
Write-JsonArtifact -InputObject $health -Path $healthPath
Write-JsonArtifact -InputObject @{
    completed_at = (Get-Date).ToUniversalTime().ToString("o")
    device_id = $DeviceId
    final_state = $bootResult.state
    ready = $bootResult.ready
    last_error = $bootResult.last_error
    timeline_artifact = $timelinePath
    devices_artifact = $devicesPath
    health_artifact = $healthPath
    pcap_artifact = $pcapPath
} -Path $summaryPath

if (-not (Wait-ForFile -Path $pcapPath -TimeoutSeconds ([Math]::Min($TimeoutSeconds, 60)))) {
    throw "The packet capture artifact was not written to $pcapPath within the expected time."
}

if ($bootResult.state -ne "READY") {
    throw "The synthetic device did not reach READY. Last error: $($bootResult.last_error)"
}

Write-Host "Demo complete."
Write-Host "Device $DeviceId reached READY."
Write-Host "Timeline artifact: $timelinePath"
Write-Host "Summary artifact: $summaryPath"
Write-Host "Packet capture: $pcapPath"
