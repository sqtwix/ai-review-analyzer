#!/usr/bin/env bash
set -Eeuo pipefail

readonly DEFAULT_MODEL_FILE="Qwen3-1.7B-Q4_K_M.gguf"
readonly DEFAULT_MODEL_URL="https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/resolve/daeb8e2d528a760970442092f6bf1e55c3b659eb/Qwen3-1.7B-Q4_K_M.gguf"
readonly DEFAULT_MODEL_SHA256="d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    echo "Usage: ./deploy.sh [--local-ai]"
    echo "  (no arguments) Start the base stack without a local model."
    echo "  --local-ai     Download/verify Qwen and start the local-ai profile."
}

read_env() {
    local env_file="$1"
    local key="$2"
    awk -F= -v key="$key" '
        $0 ~ "^[[:space:]]*" key "=" {
            sub(/^[^=]*=/, "")
            sub(/\r$/, "")
            print
            exit
        }
    ' "$env_file"
}

create_env() {
    local env_file="$1"
    local template_file="$2"
    local env_tmp db_password jwt_secret

    command -v openssl >/dev/null 2>&1 || { echo "ERROR: openssl is required to generate installation secrets." >&2; return 1; }
    [[ -f "$template_file" ]] || { echo "ERROR: $template_file is missing." >&2; return 1; }

    echo "--> Creating .env from env_example.txt with generated secrets..."
    db_password="$(openssl rand -hex 24)"
    jwt_secret="$(openssl rand -base64 48 | tr -d '\n')"
    env_tmp="$(mktemp "${env_file}.tmp.XXXXXX")"
    trap 'rm -f -- "${env_tmp:-}"' RETURN
    umask 077
    DB_PASSWORD="$db_password" JWT_SECRET="$jwt_secret" awk '
        $0 == "DB_PASSWORD=" { print "DB_PASSWORD=" ENVIRON["DB_PASSWORD"]; next }
        $0 == "JWT_SECRET=" { print "JWT_SECRET=" ENVIRON["JWT_SECRET"]; next }
        { print }
    ' "$template_file" > "$env_tmp"
    chmod 600 "$env_tmp"
    mv "$env_tmp" "$env_file"
    unset db_password jwt_secret env_tmp
    trap - RETURN
}

migrate_env() {
    local env_file="$1"
    local template_file="$2"
    local missing_tmp

    [[ -f "$template_file" ]] || { echo "ERROR: $template_file is missing." >&2; return 1; }
    missing_tmp="$(mktemp "${env_file}.missing.XXXXXX")"
    trap 'rm -f -- "${missing_tmp:-}"' RETURN

    awk -F= '
        FNR == NR {
            line = $0
            sub(/\r$/, "", line)
            if (line ~ /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=/) {
                sub(/^[[:space:]]*/, "", line)
                sub(/=.*/, "", line)
                present[line] = 1
            }
            next
        }
        {
            line = $0
            sub(/\r$/, "", line)
            if (line !~ /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=/) next
            key = line
            sub(/^[[:space:]]*/, "", key)
            sub(/=.*/, "", key)
            if (!present[key] && key != "DB_PASSWORD" && key != "JWT_SECRET" && key != "DEEPSEEK_API_KEY" && key != "SBERGPT_API_KEY") {
                print line
            }
        }
    ' "$env_file" "$template_file" > "$missing_tmp"

    if [[ -s "$missing_tmp" ]]; then
        if [[ -s "$env_file" && "$(tail -c 1 "$env_file")" != $'\n' ]]; then
            printf '\n' >> "$env_file"
        fi
        awk '{ print }' "$missing_tmp" >> "$env_file"
        echo "--> Added missing non-secret defaults from env_example.txt."
    else
        echo "--> Existing .env already contains all non-secret defaults."
    fi
    rm -f -- "$missing_tmp"
    unset missing_tmp
    trap - RETURN
}

ensure_env() {
    local env_file="$1"
    local template_file="$2"
    if [[ -f "$env_file" ]]; then
        migrate_env "$env_file" "$template_file"
    else
        create_env "$env_file" "$template_file"
    fi
}

require_nonempty() {
    local env_file="$1"
    local key="$2"
    local value
    value="$(read_env "$env_file" "$key")"
    [[ -n "$value" ]] || { echo "ERROR: $key must be set in .env." >&2; return 1; }
}

validate_boolean() {
    local env_file="$1"
    local key="$2"
    local value
    value="$(read_env "$env_file" "$key")"
    [[ "$value" == "true" || "$value" == "false" ]] || {
        echo "ERROR: $key must be exactly true or false." >&2
        return 1
    }
}

validate_port() {
    local env_file="$1"
    local key="$2"
    local value
    value="$(read_env "$env_file" "$key")"
    [[ "$value" =~ ^[0-9]+$ ]] && (( value >= 1 && value <= 65535 )) || {
        echo "ERROR: $key must be an integer from 1 to 65535." >&2
        return 1
    }
}

validate_positive_integer() {
    local env_file="$1"
    local key="$2"
    local value
    value="$(read_env "$env_file" "$key")"
    [[ "$value" =~ ^[0-9]+$ ]] && (( value >= 1 )) || {
        echo "ERROR: $key must be a positive integer." >&2
        return 1
    }
}

validate_env() {
    local env_file="$1"
    local jwt_secret

    require_nonempty "$env_file" DB_PASSWORD
    require_nonempty "$env_file" JWT_SECRET
    jwt_secret="$(read_env "$env_file" JWT_SECRET)"
    (( $(LC_ALL=C printf '%s' "$jwt_secret" | wc -c | tr -d ' ') >= 32 )) || {
        echo "ERROR: JWT_SECRET must contain at least 32 bytes." >&2
        return 1
    }
    validate_port "$env_file" APP_PORT
    validate_port "$env_file" DB_PORT
    validate_positive_integer "$env_file" JWT_EXPIRY_MINUTES
    validate_positive_integer "$env_file" DEPLOY_WAIT_TIMEOUT_SECONDS
    validate_boolean "$env_file" LOCAL_AI_ENABLED
    validate_boolean "$env_file" AI_DRIVER_FORCE_MODEL_FALLBACK
    validate_boolean "$env_file" VITE_OFFLINE_MODE
    validate_boolean "$env_file" VITE_ENABLE_DEMO_MODE
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

validate_local_model_config() {
    local env_file="$1"
    local model_file model_url model_sha256
    model_file="$(read_env "$env_file" QWEN_GGUF_MODEL_FILE)"
    model_url="$(read_env "$env_file" QWEN_GGUF_MODEL_URL)"
    model_sha256="$(read_env "$env_file" QWEN_GGUF_MODEL_SHA256)"
    model_file="${model_file:-$DEFAULT_MODEL_FILE}"

    if [[ "$model_file" == "$DEFAULT_MODEL_FILE" ]]; then
        model_url="${model_url:-$DEFAULT_MODEL_URL}"
        model_sha256="${model_sha256:-$DEFAULT_MODEL_SHA256}"
    fi
    [[ "$model_file" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ && "$model_file" != *..* ]] || {
        echo "ERROR: QWEN_GGUF_MODEL_FILE must be a plain file name." >&2
        return 1
    }
    [[ -n "$model_url" ]] || { echo "ERROR: QWEN_GGUF_MODEL_URL is required for local AI." >&2; return 1; }
    [[ "$model_sha256" =~ ^[[:xdigit:]]{64}$ ]] || {
        echo "ERROR: QWEN_GGUF_MODEL_SHA256 must be a 64-character SHA-256 digest." >&2
        return 1
    }
}

prepare_local_model() {
    local env_file="$1"
    local model_file model_url model_sha256 model_path actual_sha256 part_path
    model_file="$(read_env "$env_file" QWEN_GGUF_MODEL_FILE)"
    model_url="$(read_env "$env_file" QWEN_GGUF_MODEL_URL)"
    model_sha256="$(read_env "$env_file" QWEN_GGUF_MODEL_SHA256)"
    model_file="${model_file:-$DEFAULT_MODEL_FILE}"
    if [[ "$model_file" == "$DEFAULT_MODEL_FILE" ]]; then
        model_url="${model_url:-$DEFAULT_MODEL_URL}"
        model_sha256="${model_sha256:-$DEFAULT_MODEL_SHA256}"
    fi
    model_sha256="$(printf '%s' "$model_sha256" | tr '[:upper:]' '[:lower:]')"

    mkdir -p models
    model_path="models/$model_file"
    if [[ -f "$model_path" ]]; then
        echo "--> Verifying existing model $model_file..."
        actual_sha256="$(sha256_file "$model_path")"
        if [[ "$actual_sha256" != "$model_sha256" ]]; then
            echo "ERROR: Existing model checksum mismatch; file was left unchanged." >&2
            echo "Expected: $model_sha256" >&2
            echo "Actual:   $actual_sha256" >&2
            return 1
        fi
        return 0
    fi

    command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required to download the model." >&2; return 1; }
    part_path="$model_path.part.$$"
    trap 'rm -f -- "${part_path:-}"' RETURN
    echo "--> Downloading $model_file to a temporary file..."
    curl --fail --location --retry 3 --output "$part_path" "$model_url"
    actual_sha256="$(sha256_file "$part_path")"
    if [[ "$actual_sha256" != "$model_sha256" ]]; then
        echo "ERROR: Downloaded model checksum mismatch." >&2
        return 1
    fi
    mv "$part_path" "$model_path"
    unset part_path
    trap - RETURN
    echo "--> Model downloaded and verified."
}

show_diagnostics() {
    local -a services=(postgres ai-driver api-core frontend)
    [[ "${MODE:-base}" == "local-ai" ]] && services+=(qwen-local)
    echo "ERROR: Deployment did not reach the required healthy state. Diagnostics follow." >&2
    compose ps || true
    compose logs --tail=100 "${services[@]}" || true
}

wait_for_services() {
    local timeout="$1"
    local started_at now service container_id state all_ready
    local -a services=(postgres ai-driver api-core frontend)
    [[ "$MODE" == "local-ai" ]] && services+=(qwen-local)
    started_at="$(date +%s)"

    while true; do
        all_ready=true
        for service in "${services[@]}"; do
            container_id="$(compose ps -q "$service" 2>/dev/null || true)"
            if [[ -z "$container_id" ]]; then
                all_ready=false
                break
            fi
            state="$(docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id" 2>/dev/null || true)"
            if [[ "$state" != "running healthy" ]]; then
                all_ready=false
                break
            fi
        done
        "$all_ready" && return 0

        now="$(date +%s)"
        if (( now - started_at >= timeout )); then
            return 1
        fi
        sleep 2
    done
}

compose() {
    if [[ "$MODE" == "local-ai" ]]; then
        LOCAL_AI_ENABLED=true "${COMPOSE[@]}" --profile local-ai "$@"
    else
        LOCAL_AI_ENABLED=false "${COMPOSE[@]}" "$@"
    fi
}

main() {
    MODE="base"
    case "${1:-}" in
        "") ;;
        --local-ai) MODE="local-ai" ;;
        --cloud) echo "WARNING: --cloud is deprecated; use the default base deployment." >&2 ;;
        -h|--help) usage; return 0 ;;
        *) usage >&2; return 2 ;;
    esac

    cd "$SCRIPT_DIR"
    if docker compose version >/dev/null 2>&1; then
        COMPOSE=(docker compose)
    elif command -v docker-compose >/dev/null 2>&1; then
        COMPOSE=(docker-compose)
    else
        echo "ERROR: Docker Compose is required (docker compose or docker-compose)." >&2
        return 1
    fi

    echo "DEPLOYING AI REVIEW ANALYZER ($MODE)"
    ensure_env .env env_example.txt
    validate_env .env
    [[ "$MODE" == "local-ai" ]] && validate_local_model_config .env

    echo "--> Validating Docker Compose configuration..."
    compose config --quiet

    if [[ "$MODE" == "base" ]]; then
        echo "--> Stopping an already running local model service..."
        LOCAL_AI_ENABLED=true "${COMPOSE[@]}" --profile local-ai stop qwen-local || true
    else
        prepare_local_model .env
    fi

    echo "--> Building and starting containers without removing volumes..."
    up_args=(up --build --detach --remove-orphans)
    if compose up --help 2>&1 | grep -q -- '--wait'; then
        up_args+=(--wait --wait-timeout "$(read_env .env DEPLOY_WAIT_TIMEOUT_SECONDS)")
    fi
    if ! compose "${up_args[@]}"; then
        show_diagnostics
        return 1
    fi

    echo "--> Waiting for required services to become healthy..."
    if ! wait_for_services "$(read_env .env DEPLOY_WAIT_TIMEOUT_SECONDS)"; then
        show_diagnostics
        return 1
    fi

    echo "=================================================="
    echo "Deployment completed. Application: http://localhost:$(read_env .env APP_PORT)/"
    echo "Existing .env, models, named volumes, and application data were preserved."
    echo "=================================================="
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
