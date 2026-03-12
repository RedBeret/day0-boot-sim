[CmdletBinding()]
param(
    [switch]$WithTftp,
    [int]$StartupTimeoutSeconds = 120
)

. (Join-Path $PSScriptRoot "_Common.ps1")

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "PowerShell 7 or newer is required. Run this with pwsh."
}

Test-RequiredCommand -CommandName "docker" -DisplayName "Docker Desktop"

$repoRoot = Get-RepoRoot
Ensure-ArtifactDirectories -RepoRoot $repoRoot

Push-Location $repoRoot
try {
    & docker compose version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose is not available from the docker CLI."
    }
}
finally {
    Pop-Location
}

$composeArgs = @("compose")
if ($WithTftp) {
    $composeArgs += @("--profile", "extras")
}
$composeArgs += @("up", "-d", "--build")

Invoke-DockerCompose -RepoRoot $repoRoot -Arguments $composeArgs
$health = Wait-Day0Health -TimeoutSeconds $StartupTimeoutSeconds

Write-Host "day0-boot-sim is ready."
Write-Host "API: http://localhost:8000"
Write-Host "Dependencies: dhcp=$($health.dependencies.dhcp) http_files=$($health.dependencies.http_files)"
