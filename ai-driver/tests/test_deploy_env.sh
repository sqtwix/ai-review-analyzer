#!/usr/bin/env bash
set -Eeuo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
test_dir="$(mktemp -d)"
trap 'rm -rf -- "$test_dir"' EXIT

source "$repo_dir/deploy.sh"

# CMD uses the outer double quotes to delimit PowerShell's -Command value.
# Any additional unescaped double quote is stripped by cmd.exe and can turn
# PowerShell escapes such as `n into parser errors on Windows PowerShell 5.1.
awk '
    /^[[:space:]]*powershell -NoProfile -Command/ {
        line = $0
        quote_count = gsub(/"/, "", line)
        if (quote_count != 2) {
            print "unsafe nested double quote in deploy.bat PowerShell command at line " FNR > "/dev/stderr"
            failed = 1
        }
    }
    END { exit failed }
' "$repo_dir/deploy.bat"

template="$test_dir/template.env"
env_file="$test_dir/.env"
printf '%s\n' \
  'APP_PORT=80' \
  'DB_PORT=5432' \
  'DB_PASSWORD=' \
  'JWT_SECRET=' \
  'LOCAL_AI_ENABLED=false' \
  'AI_DRIVER_FORCE_MODEL_FALLBACK=false' \
  'VITE_OFFLINE_MODE=false' \
  'VITE_ENABLE_DEMO_MODE=false' \
  'JWT_EXPIRY_MINUTES=1440' \
  'DEPLOY_WAIT_TIMEOUT_SECONDS=600' \
  'NEW_DEFAULT=present' \
  'DEEPSEEK_API_KEY=' > "$template"

printf '%s' 'DB_PASSWORD=keep-db-secret
JWT_SECRET=keep-jwt-secret-with-at-least-32-bytes
APP_PORT=8088' > "$env_file"
migrate_env "$env_file" "$template" >/dev/null

[[ "$(read_env "$env_file" DB_PASSWORD)" == "keep-db-secret" ]]
[[ "$(read_env "$env_file" JWT_SECRET)" == "keep-jwt-secret-with-at-least-32-bytes" ]]
[[ "$(read_env "$env_file" APP_PORT)" == "8088" ]]
[[ "$(read_env "$env_file" NEW_DEFAULT)" == "present" ]]
[[ -z "$(read_env "$env_file" DEEPSEEK_API_KEY)" ]]
! grep -q '^DEEPSEEK_API_KEY=' "$env_file"

validate_env "$env_file"

printf '%s\n' 'APP_PORT=invalid' > "$test_dir/invalid-port.env"
if validate_port "$test_dir/invalid-port.env" APP_PORT >/dev/null 2>&1; then
  echo "invalid port unexpectedly passed" >&2
  exit 1
fi

printf '%s\n' 'LOCAL_AI_ENABLED=yes' > "$test_dir/invalid-boolean.env"
if validate_boolean "$test_dir/invalid-boolean.env" LOCAL_AI_ENABLED >/dev/null 2>&1; then
  echo "invalid boolean unexpectedly passed" >&2
  exit 1
fi

printf '%s\n' 'QWEN_GGUF_MODEL_FILE=../unsafe.gguf' 'QWEN_GGUF_MODEL_URL=https://example.invalid/model' 'QWEN_GGUF_MODEL_SHA256=not-a-checksum' > "$test_dir/invalid-model.env"
if validate_local_model_config "$test_dir/invalid-model.env" >/dev/null 2>&1; then
  echo "invalid model configuration unexpectedly passed" >&2
  exit 1
fi

# Windows entrypoint cannot be executed on Unix CI, but its supported modes and
# safety invariants must stay in parity with deploy.sh.
for expected in \
  '--local-ai' \
  '--cloud' \
  'docker compose' \
  'docker-compose' \
  'config --quiet' \
  'stop qwen-local' \
  'DEPLOY_WAIT_TIMEOUT_SECONDS' \
  'QWEN_GGUF_MODEL_SHA256' \
  'Existing .env, models, named volumes, and application data were preserved.'
do
  grep -Fq -- "$expected" "$repo_dir/deploy.bat" || {
    echo "deploy.bat is missing required behavior: $expected" >&2
    exit 1
  }
done

if grep -Eiq '(^|[[:space:]])down([[:space:]]|$)|down[[:space:]]+-v' "$repo_dir/deploy.bat"; then
  echo "deploy.bat must not tear down the stack or named volumes" >&2
  exit 1
fi

echo "deploy env migration and validation tests passed"
