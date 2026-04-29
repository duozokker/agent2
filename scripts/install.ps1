param(
    [string]$Path = "",
    [switch]$DryRun,
    [switch]$NoDocker,
    [switch]$NoOnboard,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
$RepoUrl = if ($env:AGENT2_REPO_URL) { $env:AGENT2_REPO_URL } else { "https://github.com/duozokker/agent2.git" }
if (-not $Path) {
    if ((Test-Path "pyproject.toml") -and (Test-Path "shared")) {
        $Path = (Get-Location).Path
    } elseif ($env:AGENT2_INSTALL_PATH) {
        $Path = $env:AGENT2_INSTALL_PATH
    } else {
        $Path = Join-Path $HOME "agent2"
    }
}
Write-Host "Agent2 installer"
Write-Host "Install path: $Path"

foreach ($bin in @("git", "python")) {
    if (-not (Get-Command $bin -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $bin"
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    if ($DryRun) {
        Write-Host "Would install uv from https://astral.sh/uv/install.ps1"
    } else {
        Write-Host "Installing uv..."
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    }
}

if (-not $NoDocker -and -not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is required unless -NoDocker is used."
}

if (-not ((Test-Path (Join-Path $Path "pyproject.toml")) -and (Test-Path (Join-Path $Path "shared")))) {
    if ((Test-Path $Path) -and ((Get-ChildItem $Path -Force | Select-Object -First 1) -ne $null)) {
        throw "$Path exists but does not look like an Agent2 repo. Use -Path for a clean target."
    }
    if ($DryRun) {
        $dryArgsList = @("--dry-run")
        if ($NoDocker) { $dryArgsList += "--no-docker" }
        if ($NoOnboard) { $dryArgsList += "--no-onboard" }
        if ($Yes) { $dryArgsList += "--yes" }
        Write-Host "Would clone $RepoUrl into $Path"
        Write-Host "Would run: cd $Path"
        Write-Host "Would run: uv sync --extra dev"
        Write-Host "Would run: uv run agent2 setup $dryArgsList"
        exit 0
    } else {
        git clone $RepoUrl $Path
    }
}

Set-Location $Path
if ($DryRun) {
    Write-Host "Would run: uv sync --extra dev"
} else {
    uv sync --extra dev
}

$argsList = @()
if ($DryRun) { $argsList += "--dry-run" }
if ($NoDocker) { $argsList += "--no-docker" }
if ($NoOnboard) { $argsList += "--no-onboard" }
if ($Yes) { $argsList += "--yes" }

if ($DryRun) {
    Write-Host "Would run: uv run agent2 setup $argsList"
} else {
    uv run agent2 setup @argsList
}

if (-not $NoOnboard -and -not $DryRun) {
    Write-Host ""
    Write-Host "Create your first Brain Clone with:"
    Write-Host "  uv run agent2 onboard"
}
