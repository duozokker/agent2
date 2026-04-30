#!/usr/bin/env bash
set -euo pipefail

# Agent2 Installer — https://getagent2.dev
# Usage: curl -fsSL https://getagent2.dev/install.sh | bash

# ── Colors ────────────────────────────────────────────────────────────────────
BOLD='\033[1m'
RED='\033[38;2;255;59;48m'        # #FF3B30 — brand accent
GREEN='\033[38;2;52;199;89m'      # success
GRAY='\033[38;2;154;149;144m'     # #9A9590 — body text
DIM='\033[38;2;119;119;119m'      # #777 — muted
NC='\033[0m'

# ── UI helpers ────────────────────────────────────────────────────────────────
banner() {
  echo ""
  echo -e "${BOLD}      _                    _     __  ${NC}"
  echo -e "${BOLD}     / \\   __ _  ___ _ __ | |_  |_ ) ${NC}"
  echo -e "${BOLD}    / _ \\ / _\` |/ _ \\ '_ \\| __|  / /  ${NC}"
  echo -e "${BOLD}   / ___ \\ (_| |  __/ | | | |_  /___| ${NC}"
  echo -e "${BOLD}  /_/   \\_\\__, |\\___|_| |_|\\__|  ${RED}__${NC}  "
  echo -e "${BOLD}          |___/                 ${RED}(__)${NC} "
  echo ""
  echo -e "${RED}${BOLD}  ●  Agent2 Installer${NC}"
  echo -e "${GRAY}  Turn domain experts into production AI agents.${NC}"
  echo -e "${DIM}  https://getagent2.dev${NC}"
  echo ""
}

step() {
  STEP_N=$((STEP_N + 1))
  echo -e "${RED}${BOLD}[${STEP_N}/${STEP_TOTAL}]${NC} ${BOLD}$1${NC}"
}

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
info() { echo -e "  ${DIM}·${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1" >&2; }

STEP_N=0
STEP_TOTAL=4

# ── Parse args ────────────────────────────────────────────────────────────────
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
    --path)      INSTALL_PATH="$2"; shift 2 ;;
    --dry-run)   DRY_RUN=1; shift ;;
    --no-docker) NO_DOCKER=1; shift ;;
    --no-onboard) NO_ONBOARD=1; shift ;;
    --yes|-y)    YES=1; shift ;;
    *)           fail "Unknown option: $1"; exit 2 ;;
  esac
done

banner

# ── Step 1: Check prerequisites ──────────────────────────────────────────────
step "Checking prerequisites"

for bin in git python3; do
  if command -v "$bin" >/dev/null 2>&1; then
    ok "$bin found"
  else
    fail "$bin not found — please install it first"
    exit 1
  fi
done

if command -v uv >/dev/null 2>&1; then
  ok "uv found"
else
  if [[ "$DRY_RUN" -eq 1 ]]; then
    info "Would install uv from https://astral.sh/uv/install.sh"
  else
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    ok "uv installed"
  fi
fi

if [[ "$NO_DOCKER" -eq 0 ]]; then
  if command -v docker >/dev/null 2>&1; then
    ok "Docker found"
  else
    fail "Docker not found — install Docker Desktop or use --no-docker"
    exit 1
  fi
else
  info "Docker skipped (--no-docker)"
fi

echo ""

# ── Step 2: Clone or update repo ─────────────────────────────────────────────
step "Setting up Agent2"

if [[ -f "$INSTALL_PATH/pyproject.toml" && -d "$INSTALL_PATH/shared" ]]; then
  info "Agent2 found at $INSTALL_PATH"
  if [[ "$YES" -eq 1 ]]; then
    _UPDATE_CHOICE="update"
  elif [[ -r /dev/tty ]]; then
    echo -e "  ${BOLD}What would you like to do?${NC}"
    echo -e "    ${BOLD}1)${NC} Update to latest version ${DIM}(git pull + uv sync)${NC}"
    echo -e "    ${BOLD}2)${NC} Fresh install ${DIM}(delete and re-clone)${NC}"
    echo -e "    ${BOLD}3)${NC} Keep as-is ${DIM}(skip to setup)${NC}"
    printf "  Choice [1]: "
    read -r _UPDATE_CHOICE </dev/tty
    _UPDATE_CHOICE="${_UPDATE_CHOICE:-1}"
  else
    _UPDATE_CHOICE="update"
  fi
  case "$_UPDATE_CHOICE" in
    2|fresh)
      info "Removing old install..."
      rm -rf "$INSTALL_PATH"
      info "Cloning Agent2..."
      git clone --quiet "$REPO_URL" "$INSTALL_PATH"
      ok "Fresh install at $INSTALL_PATH"
      ;;
    3|keep)
      ok "Keeping existing install"
      ;;
    *)
      info "Updating..."
      (cd "$INSTALL_PATH" && git pull --quiet origin main 2>/dev/null || git pull --quiet)
      ok "Updated to latest version"
      ;;
  esac
else
  if [[ -e "$INSTALL_PATH" && -n "$(find "$INSTALL_PATH" -mindepth 1 -maxdepth 1 2>/dev/null)" ]]; then
    fail "$INSTALL_PATH exists but is not an Agent2 repo. Use --path to pick a different location."
    exit 1
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    info "Would clone $REPO_URL → $INSTALL_PATH"
  else
    info "Cloning Agent2..."
    git clone --quiet "$REPO_URL" "$INSTALL_PATH"
    ok "Cloned to $INSTALL_PATH"
  fi
fi

echo ""

# ── Step 3: Install dependencies ─────────────────────────────────────────────
step "Installing dependencies"

cd "$INSTALL_PATH"

if [[ "$DRY_RUN" -eq 1 ]]; then
  info "Would run: uv sync --extra dev"
else
  info "Running uv sync (this may take a moment)..."
  uv sync --extra dev --quiet 2>/dev/null || uv sync --extra dev
  ok "Dependencies installed"
fi

echo ""

# ── Step 4: Configure Agent2 ─────────────────────────────────────────────────
step "Configuring Agent2"

if [[ "$DRY_RUN" -eq 1 ]]; then
  info "Would run: uv run agent2 setup --yes"
elif [[ -t 0 ]]; then
  # Direct terminal — run the full interactive wizard
  echo ""
  SETUP_ARGS=()
  if [[ "$NO_DOCKER" -eq 1 ]]; then SETUP_ARGS+=(--no-docker); fi
  if [[ "$NO_ONBOARD" -eq 1 ]]; then SETUP_ARGS+=(--no-onboard); fi
  if [[ "$YES" -eq 1 ]]; then SETUP_ARGS+=(--yes); fi
  uv run agent2 setup ${SETUP_ARGS[@]+"${SETUP_ARGS[@]}"}
else
  # Piped mode (curl | bash) — collect key via read, then run non-interactive
  _OR_KEY=""
  if (exec </dev/tty) 2>/dev/null; then
    echo ""
    printf "  ${BOLD}OpenRouter API key${NC} ${DIM}(openrouter.ai/keys, Enter to skip):${NC} " >/dev/tty
    read -r -s _OR_KEY </dev/tty 2>/dev/null || _OR_KEY=""
    echo "" >/dev/tty
    if [[ -n "$_OR_KEY" ]]; then
      ok "Key set (${_OR_KEY:0:12}...)"
    else
      info "Skipped — you can add it later with: agent2 setup"
    fi
  else
    info "No terminal detected — skipping API key prompt"
    info "Run 'agent2 setup' after install to configure interactively"
  fi
  SETUP_ARGS=(--yes)
  if [[ -n "$_OR_KEY" ]]; then SETUP_ARGS+=(--openrouter-key "$_OR_KEY"); fi
  if [[ "$NO_DOCKER" -eq 1 ]]; then SETUP_ARGS+=(--no-docker); fi
  if [[ "$NO_ONBOARD" -eq 1 ]]; then SETUP_ARGS+=(--no-onboard); fi
  uv run agent2 setup "${SETUP_ARGS[@]}"
fi

echo ""

# ── Done ──────────────────────────────────────────────────────────────────────
echo -e "${GREEN}${BOLD}  ✓  Agent2 is ready!${NC}"
echo ""
echo -e "${GRAY}  Get started:${NC}"
echo -e "    ${BOLD}cd $INSTALL_PATH${NC}"
echo -e "    uv run agent2 setup       ${DIM}# full interactive wizard${NC}"
echo -e "    uv run agent2 onboard     ${DIM}# create a Brain Clone agent${NC}"
echo ""
echo -e "${GRAY}  Other commands:${NC}"
echo -e "    uv run agent2 doctor      ${DIM}# check your setup${NC}"
echo -e "    uv run agent2 list        ${DIM}# see available agents${NC}"
echo -e "    uv run agent2 serve <name> ${DIM}# run an agent locally${NC}"
echo ""
