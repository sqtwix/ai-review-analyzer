#!/usr/bin/env bash
set -Eeuo pipefail

readonly DEFAULT_MODEL_FILE="Qwen3-1.7B-Q4_K_M.gguf"
readonly DEFAULT_MODEL_URL="https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/resolve/daeb8e2d528a760970442092f6bf1e55c3b659eb/Qwen3-1.7B-Q4_K_M.gguf"
readonly DEFAULT_MODEL_SHA256="d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
    echo "Usage: ./deploy.sh [--local-ai|--cloud]"
    echo "  --local-ai  Download/verify Qwen and start the complete local stack (default)."
    echo "  --cloud     Start the application without the local model service."
}

MODE="local-ai"
case "${1:-}" in
    ""|--local-ai) ;;
    --cloud) MODE="cloud" ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac

if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
else
    echo "ERROR: Docker Compose is required (docker compose or docker-compose)." >&2
    exit 1
fi

echo "DEPLOYING AI REVIEW ANALYZER ($MODE)"

if [[ ! -f .env ]]; then
    command -v openssl >/dev/null 2>&1 || { echo "ERROR: openssl is required to generate installation secrets." >&2; exit 1; }
    [[ -f env_example.txt ]] || { echo "ERROR: env_example.txt is missing." >&2; exit 1; }
    echo "--> Creating .env from env_example.txt with generated secrets..."
    db_password="$(openssl rand -hex 24)"
    jwt_secret="$(openssl rand -base64 48 | tr -d '\n')"
    umask 077
    awk -v db_password="$db_password" -v jwt_secret="$jwt_secret" '
        $0 == "DB_PASSWORD=" { print "DB_PASSWORD=" db_password; next }
        $0 == "JWT_SECRET=" { print "JWT_SECRET=" jwt_secret; next }
        { print }
    ' env_example.txt > .env
    unset db_password jwt_secret
else
    echo "--> Existing .env preserved."
fi

read_env() {
    awk -F= -v key="$1" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' .env
}

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print tolower($1)}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print tolower($1)}'
    else
        echo "ERROR: sha256sum or shasum is required." >&2
        return 1
    fi
}

if [[ "$MODE" == "local-ai" ]]; then
    model_file="$(read_env QWEN_GGUF_MODEL_FILE)"
    model_file="${model_file:-$DEFAULT_MODEL_FILE}"
    model_url="$(read_env QWEN_GGUF_MODEL_URL)"
    model_sha256="$(read_env QWEN_GGUF_MODEL_SHA256)"

    if [[ "$model_file" == "$DEFAULT_MODEL_FILE" ]]; then
        model_url="${model_url:-$DEFAULT_MODEL_URL}"
        model_sha256="${model_sha256:-$DEFAULT_MODEL_SHA256}"
    fi

    if [[ ! "$model_sha256" =~ ^[[:xdigit:]]{64}$ ]]; then
        echo "ERROR: QWEN_GGUF_MODEL_SHA256 must be a 64-character SHA-256 digest." >&2
        exit 1
    fi
    model_sha256="$(printf '%s' "$model_sha256" | tr '[:upper:]' '[:lower:]')"
    if [[ -z "$model_file" || "$model_file" == .* || "$model_file" == *..* || "$model_file" == *[!A-Za-z0-9._-]* ]]; then
        echo "ERROR: QWEN_GGUF_MODEL_FILE must be a plain file name." >&2
        exit 1
    fi

    mkdir -p models
    model_path="models/$model_file"
    if [[ -f "$model_path" ]]; then
        echo "--> Verifying existing model $model_file..."
        actual_sha256="$(sha256_file "$model_path")"
        if [[ "$actual_sha256" != "$model_sha256" ]]; then
            echo "ERROR: Existing model checksum mismatch; file was left unchanged." >&2
            echo "Expected: $model_sha256" >&2
            echo "Actual:   $actual_sha256" >&2
            exit 1
        fi
    else
        [[ -n "$model_url" ]] || { echo "ERROR: QWEN_GGUF_MODEL_URL is required for a missing custom model." >&2; exit 1; }
        command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required to download the model." >&2; exit 1; }
        part_path="$model_path.part.$$"
        trap 'rm -f -- "${part_path:-}"' EXIT
        echo "--> Downloading $model_file to a temporary file..."
        curl --fail --location --retry 3 --output "$part_path" "$model_url"
        actual_sha256="$(sha256_file "$part_path")"
        if [[ "$actual_sha256" != "$model_sha256" ]]; then
            echo "ERROR: Downloaded model checksum mismatch." >&2
            exit 1
        fi
        mv "$part_path" "$model_path"
        trap - EXIT
        echo "--> Model downloaded and verified."
    fi
fi

compose() {
    if [[ "$MODE" == "local-ai" ]]; then
        "${COMPOSE[@]}" --profile local-ai "$@"
    else
        "${COMPOSE[@]}" "$@"
    fi
}

echo "--> Validating Docker Compose configuration..."
compose config --quiet

if [[ "$MODE" == "cloud" ]]; then
    echo "--> Stopping an already running local model service..."
    "${COMPOSE[@]}" --profile local-ai stop qwen-local
fi

echo "--> Building and starting containers without removing volumes..."
up_args=(up --build --detach --remove-orphans)
if compose up --help 2>&1 | grep -q -- '--wait'; then
    up_args+=(--wait --wait-timeout "${DEPLOY_WAIT_TIMEOUT_SECONDS:-600}")
fi
compose "${up_args[@]}"

echo "=================================================="
app_port="${APP_PORT:-$(read_env APP_PORT)}"
echo "Deployment completed. Application: http://localhost:${app_port:-80}/"
echo "Existing .env, models, named volumes, and application data were preserved."
echo "=================================================="
