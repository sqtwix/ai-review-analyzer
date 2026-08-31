@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "DEFAULT_MODEL_FILE=Qwen3-1.7B-Q4_K_M.gguf"
set "DEFAULT_MODEL_URL=https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/resolve/daeb8e2d528a760970442092f6bf1e55c3b659eb/Qwen3-1.7B-Q4_K_M.gguf"
set "DEFAULT_MODEL_SHA256=d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5"

cd /d "%~dp0"
set "MODE=local-ai"
if /I "%~1"=="cloud" set "MODE=cloud"
if /I "%~1"=="--cloud" set "MODE=cloud"
if /I "%~1"=="local-ai" set "MODE=local-ai"
if /I "%~1"=="--local-ai" set "MODE=local-ai"
if not "%~1"=="" if /I not "%~1"=="cloud" if /I not "%~1"=="--cloud" if /I not "%~1"=="local-ai" if /I not "%~1"=="--local-ai" goto :usage

docker compose version >nul 2>&1
if not errorlevel 1 (
    set "COMPOSE=docker compose"
) else (
    where docker-compose >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Docker Compose is required ^(docker compose or docker-compose^). 1>&2
        exit /b 1
    )
    set "COMPOSE=docker-compose"
)

echo DEPLOYING AI REVIEW ANALYZER ^(%MODE%^)

if not exist ".env" (
    if not exist "env_example.txt" (
        echo ERROR: env_example.txt is missing. 1>&2
        exit /b 1
    )
    echo --^> Creating .env from env_example.txt with generated secrets...
    for /f %%i in ('powershell -NoProfile -Command "$b=New-Object byte[] 24; $r=[Security.Cryptography.RandomNumberGenerator]::Create(); $r.GetBytes($b); $r.Dispose(); [BitConverter]::ToString($b).Replace('-','').ToLowerInvariant()"') do set "GENERATED_DB_PASSWORD=%%i"
    for /f %%i in ('powershell -NoProfile -Command "$b=New-Object byte[] 48; $r=[Security.Cryptography.RandomNumberGenerator]::Create(); $r.GetBytes($b); $r.Dispose(); [Convert]::ToBase64String($b)"') do set "GENERATED_JWT_SECRET=%%i"
    powershell -NoProfile -Command "$c=[IO.File]::ReadAllText('env_example.txt'); $c=$c -replace '(?m)^DB_PASSWORD=$','DB_PASSWORD=!GENERATED_DB_PASSWORD!' -replace '(?m)^JWT_SECRET=$','JWT_SECRET=!GENERATED_JWT_SECRET!'; [IO.File]::WriteAllText('.env',$c,(New-Object Text.UTF8Encoding($false)))"
    if errorlevel 1 exit /b 1
    set "GENERATED_DB_PASSWORD="
    set "GENERATED_JWT_SECRET="
) else (
    echo --^> Existing .env preserved.
)

if not defined APP_PORT for /f "usebackq tokens=1,* delims==" %%A in (`findstr /R /B /C:"APP_PORT=" ".env"`) do set "APP_PORT=%%B"

if /I "%MODE%"=="cloud" goto :compose

set "QWEN_GGUF_MODEL_FILE="
set "QWEN_GGUF_MODEL_URL="
set "QWEN_GGUF_MODEL_SHA256="
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /R /B /C:"QWEN_GGUF_MODEL_FILE=" /C:"QWEN_GGUF_MODEL_URL=" /C:"QWEN_GGUF_MODEL_SHA256=" ".env"`) do set "%%A=%%B"
if not defined QWEN_GGUF_MODEL_FILE set "QWEN_GGUF_MODEL_FILE=%DEFAULT_MODEL_FILE%"
if /I "%QWEN_GGUF_MODEL_FILE%"=="%DEFAULT_MODEL_FILE%" (
    if not defined QWEN_GGUF_MODEL_URL set "QWEN_GGUF_MODEL_URL=%DEFAULT_MODEL_URL%"
    if not defined QWEN_GGUF_MODEL_SHA256 set "QWEN_GGUF_MODEL_SHA256=%DEFAULT_MODEL_SHA256%"
)

powershell -NoProfile -Command "if ($env:QWEN_GGUF_MODEL_FILE -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$' -or $env:QWEN_GGUF_MODEL_FILE.Contains('..')) { exit 1 }; if ($env:QWEN_GGUF_MODEL_SHA256 -notmatch '^[0-9A-Fa-f]{64}$') { exit 2 }"
if errorlevel 2 (
    echo ERROR: QWEN_GGUF_MODEL_SHA256 must be a 64-character SHA-256 digest. 1>&2
    exit /b 1
)
if errorlevel 1 (
    echo ERROR: QWEN_GGUF_MODEL_FILE must be a plain file name. 1>&2
    exit /b 1
)

if not exist "models" mkdir "models"
set "MODEL_PATH=models\%QWEN_GGUF_MODEL_FILE%"
if exist "%MODEL_PATH%" (
    echo --^> Verifying existing model %QWEN_GGUF_MODEL_FILE%...
    for /f %%H in ('powershell -NoProfile -Command "(Get-FileHash -LiteralPath $env:MODEL_PATH -Algorithm SHA256).Hash.ToLowerInvariant()"') do set "ACTUAL_SHA256=%%H"
    if /I not "!ACTUAL_SHA256!"=="%QWEN_GGUF_MODEL_SHA256%" (
        echo ERROR: Existing model checksum mismatch; file was left unchanged. 1>&2
        echo Expected: %QWEN_GGUF_MODEL_SHA256% 1>&2
        echo Actual:   !ACTUAL_SHA256! 1>&2
        exit /b 1
    )
) else (
    if not defined QWEN_GGUF_MODEL_URL (
        echo ERROR: QWEN_GGUF_MODEL_URL is required for a missing custom model. 1>&2
        exit /b 1
    )
    set "PART_PATH=%MODEL_PATH%.part.%RANDOM%"
    echo --^> Downloading %QWEN_GGUF_MODEL_FILE% to a temporary file...
    powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri $env:QWEN_GGUF_MODEL_URL -OutFile $env:PART_PATH"
    if errorlevel 1 goto :download_failed
    for /f %%H in ('powershell -NoProfile -Command "(Get-FileHash -LiteralPath $env:PART_PATH -Algorithm SHA256).Hash.ToLowerInvariant()"') do set "ACTUAL_SHA256=%%H"
    if /I not "!ACTUAL_SHA256!"=="%QWEN_GGUF_MODEL_SHA256%" (
        echo ERROR: Downloaded model checksum mismatch. 1>&2
        del /q "!PART_PATH!" >nul 2>&1
        exit /b 1
    )
    move /y "!PART_PATH!" "%MODEL_PATH%" >nul
    echo --^> Model downloaded and verified.
)

:compose
echo --^> Validating Docker Compose configuration...
if /I "%MODE%"=="local-ai" (
    %COMPOSE% --profile local-ai config --quiet
) else (
    %COMPOSE% config --quiet
)
if errorlevel 1 exit /b 1

if /I "%MODE%"=="cloud" (
    echo --^> Stopping an already running local model service...
    %COMPOSE% --profile local-ai stop qwen-local
    if errorlevel 1 exit /b 1
)

echo --^> Building and starting containers without removing volumes...
%COMPOSE% up --help 2>&1 | findstr /C:"--wait" >nul
if errorlevel 1 (
    if /I "%MODE%"=="local-ai" (
        %COMPOSE% --profile local-ai up --build --detach --remove-orphans
    ) else (
        %COMPOSE% up --build --detach --remove-orphans
    )
) else (
    if not defined DEPLOY_WAIT_TIMEOUT_SECONDS set "DEPLOY_WAIT_TIMEOUT_SECONDS=600"
    if /I "%MODE%"=="local-ai" (
        %COMPOSE% --profile local-ai up --build --detach --remove-orphans --wait --wait-timeout !DEPLOY_WAIT_TIMEOUT_SECONDS!
    ) else (
        %COMPOSE% up --build --detach --remove-orphans --wait --wait-timeout !DEPLOY_WAIT_TIMEOUT_SECONDS!
    )
)
if errorlevel 1 exit /b 1

if not defined APP_PORT set "APP_PORT=80"
echo ==================================================
echo Deployment completed. Application: http://localhost:!APP_PORT!/
echo Existing .env, models, named volumes, and application data were preserved.
echo ==================================================
exit /b 0

:download_failed
if defined PART_PATH del /q "!PART_PATH!" >nul 2>&1
echo ERROR: Model download failed; no target model file was created. 1>&2
exit /b 1

:usage
echo Usage: deploy.bat [local-ai^|cloud] 1>&2
exit /b 2
