#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd -- "${BACKEND_DIR}/.." && pwd)"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-1}"
KGQA_BACKEND_VENV="${KGQA_BACKEND_VENV:-$HOME/.venvs/kg-mvp-backend-py311}"

REQ_FILE="${BACKEND_DIR}/requirements.txt"
REQ_HASH_FILE="${KGQA_BACKEND_VENV}/.requirements.sha256"

log() {
  printf '[backend-stable] %s\n' "$*"
}

die() {
  printf '[backend-stable] ERROR: %s\n' "$*" >&2
  exit 1
}

detect_python() {
  if command -v python3.11 >/dev/null 2>&1; then
    echo "python3.11"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  die "python3.11 or python3 is required"
}

supports_dataless_check() {
  find "${BACKEND_DIR}" -flags +dataless -print -quit >/dev/null 2>&1
}

check_dataless_files() {
  if ! supports_dataless_check; then
    log "skip dataless check: current find does not support -flags +dataless"
    return
  fi

  local hit=""
  hit="$(find "${BACKEND_DIR}/app" -flags +dataless -print -quit 2>/dev/null || true)"
  if [[ -z "${hit}" && -f "${BACKEND_DIR}/.env" ]]; then
    hit="$(find "${BACKEND_DIR}/.env" -flags +dataless -print -quit 2>/dev/null || true)"
  fi

  if [[ -z "${hit}" ]]; then
    return
  fi

  die "dataless file found: ${hit}. In Finder, download this project directory first, then retry."
}

ensure_env_file() {
  if [[ -f "${BACKEND_DIR}/.env" ]]; then
    return
  fi
  cp "${BACKEND_DIR}/.env.example" "${BACKEND_DIR}/.env"
  log "created ${BACKEND_DIR}/.env from .env.example"
}

ensure_venv() {
  local py_bin="$1"
  if [[ -x "${KGQA_BACKEND_VENV}/bin/python" ]]; then
    return
  fi

  mkdir -p "$(dirname -- "${KGQA_BACKEND_VENV}")"
  log "creating venv at ${KGQA_BACKEND_VENV}"
  "${py_bin}" -m venv "${KGQA_BACKEND_VENV}"
}

sync_requirements() {
  local req_hash=""
  local old_hash=""

  req_hash="$(shasum -a 256 "${REQ_FILE}" | awk '{print $1}')"
  if [[ -f "${REQ_HASH_FILE}" ]]; then
    old_hash="$(cat "${REQ_HASH_FILE}")"
  fi

  if [[ "${req_hash}" == "${old_hash}" ]]; then
    log "requirements unchanged, skip install"
    return
  fi

  log "installing dependencies from ${REQ_FILE}"
  "${KGQA_BACKEND_VENV}/bin/pip" install --upgrade pip
  "${KGQA_BACKEND_VENV}/bin/pip" install -r "${REQ_FILE}"
  printf '%s\n' "${req_hash}" > "${REQ_HASH_FILE}"
}

clear_pycache() {
  find "${BACKEND_DIR}/app" -type d -name "__pycache__" -prune -exec rm -rf {} +
}

main() {
  local py_bin=""
  py_bin="$(detect_python)"

  check_dataless_files
  ensure_env_file
  ensure_venv "${py_bin}"
  sync_requirements
  clear_pycache

  cd "${BACKEND_DIR}"
  log "project root: ${PROJECT_ROOT}"
  log "starting backend on http://${HOST}:${PORT} (reload=${RELOAD})"

  local uvicorn_args=(
    app.main:app
    --host "${HOST}"
    --port "${PORT}"
  )

  case "${RELOAD}" in
    1|true|TRUE|yes|YES|on|ON)
      uvicorn_args+=(--reload)
      ;;
  esac

  exec env PYTHONPATH=. "${KGQA_BACKEND_VENV}/bin/uvicorn" "${uvicorn_args[@]}"
}

main "$@"
