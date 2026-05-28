# Log in to Chroma CLI using CHROMA_CLI_API_KEY from .env
# Usage: .\scripts\chroma-login.ps1
#        .\scripts\chroma-login.ps1 -Profile my-team

param(
    [string]$Profile = "mutual-fund"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envFile = Join-Path $root ".env"

if (-not (Test-Path $envFile)) {
    Write-Error "Missing $envFile — copy .env.example to .env and set CHROMA_CLI_API_KEY."
}

function Get-EnvValue([string]$Name) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match "^\s*$Name=(.*)$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return ""
}

$key = Get-EnvValue "CHROMA_CLI_API_KEY"
if (-not $key) {
    $key = Get-EnvValue "CHROMA_API_KEY"
    if ($key) {
        Write-Host "CHROMA_CLI_API_KEY empty; using CHROMA_API_KEY."
    }
}

if (-not $key) {
    Write-Error "Set CHROMA_CLI_API_KEY (or CHROMA_API_KEY) in .env"
}

chroma login --profile $Profile --api-key $key
Write-Host "Done. Active profile: $Profile (credentials under `$HOME\.chroma\credentials)"
