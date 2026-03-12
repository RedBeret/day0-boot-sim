Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Test-RequiredCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandName,
        [string]$DisplayName = $CommandName
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $DisplayName"
    }
}

function Ensure-ArtifactDirectories {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    foreach ($name in @("logs", "pcaps", "reports", "data")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot $name) | Out-Null
    }
}

function Invoke-DockerCompose {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    Push-Location $RepoRoot
    try {
        & docker @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Docker command failed: docker $($Arguments -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Wait-Day0Health {
    param(
        [string]$Uri = "http://localhost:8000/health",
        [int]$TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $attempt = 0

    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-RestMethod -Uri $Uri -Method Get -TimeoutSec 5
            if ($response.status -eq "ok" -and $response.dependencies.dhcp -eq "ok" -and $response.dependencies.http_files -eq "ok") {
                return $response
            }
        }
        catch {
        }

        $delay = [Math]::Min([Math]::Pow(2, $attempt), 5)
        Start-Sleep -Seconds $delay
        $attempt += 1
    }

    throw "Timed out waiting for the synthetic lab to become healthy at $Uri."
}

function Wait-ForFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ((Test-Path $Path) -and (Get-Item $Path).Length -gt 0) {
            return $true
        }
        Start-Sleep -Seconds 1
    }

    return $false
}

function Write-JsonArtifact {
    param(
        [Parameter(Mandatory = $true)]
        $InputObject,
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $directory = Split-Path -Parent $Path
    if ($directory) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }

    $InputObject | ConvertTo-Json -Depth 10 | Set-Content -Path $Path -Encoding utf8
}
