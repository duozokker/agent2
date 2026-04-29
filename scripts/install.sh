#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${AGENT2_REPO_URL:-https://github.com/duozokker/agent2.git}"
if [[ -f "pyproject.toml" && -d "shared" ]]; then
  DEFAULT_INSTALL_PATH="$PWD"
else
  DEFAULT_INSTALL_PATH="$HOME/agent2"
fi
INSTALL_PATH="${AGENT2_INSTALL_PATH:-$DEFAULT_INSTALL_PATH}"
DRY_RUN=0
NO_DOCKER=0
NO_ONBOARD=0
YES=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --path)
      INSTALL_PATH="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --no-docker)
      NO_DOCKER=1
      shift
      ;;
    --no-onboard)
      NO_ONBOARD=1
      shift
      ;;
    --yes|-y)
      YES=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

echo "Agent2 installer"
echo "Install path: $INSTALL_PATH"

for bin in git python3; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "Missing required command: $bin" >&2
    exit 1
  fi
done

if ! command -v uv >/dev/null 2>&1; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "Would install uv from https://astral.sh/uv/install.sh"
  else
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  fi
fi

if [[ "$NO_DOCKER" -eq 0 ]] && ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required unless --no-docker is used." >&2
  exit 1
fi

if [[ ! -f "$INSTALL_PATH/pyproject.toml" || ! -d "$INSTALL_PATH/shared" ]]; then
  if [[ -e "$INSTALL_PATH" && -n "$(find "$INSTALL_PATH" -mindepth 1 -maxdepth 1 2>/dev/null)" ]]; then
    echo "$INSTALL_PATH exists but does not look like an Agent2 repo. Use --path for a clean target." >&2
    exit 1
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    DRY_ARGS=(--dry-run)
    if [[ "$NO_DOCKER" -eq 1 ]]; then DRY_ARGS+=(--no-docker); fi
    if [[ "$NO_ONBOARD" -eq 1 ]]; then DRY_ARGS+=(--no-onboard); fi
    if [[ "$YES" -eq 1 ]]; then DRY_ARGS+=(--yes); fi
    echo "Would clone $REPO_URL into $INSTALL_PATH"
    echo "Would run: cd $INSTALL_PATH"
    echo "Would run: uv sync --extra dev"
    echo "Would run: uv run agent2 setup ${DRY_ARGS[*]}"
    exit 0
  else
    git clone "$REPO_URL" "$INSTALL_PATH"
  fi
fi

cd "$INSTALL_PATH"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Would run: uv sync --extra dev"
else
  uv sync --extra dev
fi

ARGS=()
if [[ "$DRY_RUN" -eq 1 ]]; then ARGS+=(--dry-run); fi
if [[ "$NO_DOCKER" -eq 1 ]]; then ARGS+=(--no-docker); fi
if [[ "$NO_ONBOARD" -eq 1 ]]; then ARGS+=(--no-onboard); fi
if [[ "$YES" -eq 1 ]]; then ARGS+=(--yes); fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Would run: uv run agent2 setup ${ARGS[*]}"
else
  uv run agent2 setup "${ARGS[@]}"
fi

if [[ "$NO_ONBOARD" -eq 0 && "$DRY_RUN" -eq 0 ]]; then
  echo
  echo "Create your first Brain Clone with:"
  echo "  uv run agent2 onboard"
fi
