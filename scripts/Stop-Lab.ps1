[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot "_Common.ps1")

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "PowerShell 7 or newer is required. Run this with pwsh."
}

Test-RequiredCommand -CommandName "docker" -DisplayName "Docker Desktop"

$repoRoot = Get-RepoRoot
Invoke-DockerCompose -RepoRoot $repoRoot -Arguments @("compose", "--profile", "extras", "down", "--remove-orphans")

Write-Host "day0-boot-sim has stopped."
Write-Host "Artifacts were preserved under logs, pcaps, reports, and data."
