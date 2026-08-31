@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "DEFAULT_MODEL_FILE=Qwen3-1.7B-Q4_K_M.gguf"
set "DEFAULT_MODEL_URL=https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/resolve/daeb8e2d528a760970442092f6bf1e55c3b659eb/Qwen3-1.7B-Q4_K_M.gguf"
set "DEFAULT_MODEL_SHA256=d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5"

cd /d "%~dp0"
set "MODE=base"
if "%~1"=="" goto :parse_done
if /I "%~1"=="--local-ai" (
    set "MODE=local-ai"
    goto :parse_done
)
if /I "%~1"=="--cloud" (
    echo WARNING: --cloud is deprecated; use the default base deployment. 1>&2
    goto :parse_done
)
if /I "%~1"=="--help" goto :usage
if /I "%~1"=="-h" goto :usage
goto :usage

:parse_done
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
call :ensure_env
if errorlevel 1 exit /b 1
call :validate_env
if errorlevel 1 exit /b 1
if /I "%MODE%"=="local-ai" (
    call :validate_local_model_config
    if errorlevel 1 exit /b 1
)

if /I "%MODE%"=="local-ai" (
    set "LOCAL_AI_ENABLED=true"
) else (
    set "LOCAL_AI_ENABLED=false"
)

echo --^> Validating Docker Compose configuration...
if /I "%MODE%"=="local-ai" (
    %COMPOSE% --profile local-ai config --quiet
) else (
    %COMPOSE% config --quiet
)
if errorlevel 1 exit /b 1

if /I "%MODE%"=="base" (
    echo --^> Stopping an already running local model service...
    set "LOCAL_AI_ENABLED=true"
    %COMPOSE% --profile local-ai stop qwen-local >nul 2>&1
    set "LOCAL_AI_ENABLED=false"
) else (
    call :prepare_local_model
    if errorlevel 1 exit /b 1
)

echo --^> Building and starting containers without removing volumes...
%COMPOSE% up --help 2>&1 | findstr /C:"--wait" >nul
if errorlevel 1 goto :up_without_wait
if /I "%MODE%"=="local-ai" (
    %COMPOSE% --profile local-ai up --build --detach --remove-orphans --wait --wait-timeout %DEPLOY_WAIT_TIMEOUT_SECONDS%
) else (
    %COMPOSE% up --build --detach --remove-orphans --wait --wait-timeout %DEPLOY_WAIT_TIMEOUT_SECONDS%
)
if errorlevel 1 goto :deployment_failed
goto :wait_for_health

:up_without_wait
if /I "%MODE%"=="local-ai" (
    %COMPOSE% --profile local-ai up --build --detach --remove-orphans
) else (
    %COMPOSE% up --build --detach --remove-orphans
)
if errorlevel 1 goto :deployment_failed

:wait_for_health
echo --^> Waiting for required services to become healthy...
call :wait_for_services
if errorlevel 1 goto :deployment_failed

echo ==================================================
echo Deployment completed. Application: http://localhost:%APP_PORT%/
echo Existing .env, models, named volumes, and application data were preserved.
echo ==================================================
exit /b 0

:ensure_env
if exist ".env" goto :migrate_env
if not exist "env_example.txt" (
    echo ERROR: env_example.txt is missing. 1>&2
    exit /b 1
)
echo --^> Creating .env from env_example.txt with generated secrets...
powershell -NoProfile -Command "$t=[IO.File]::ReadAllText('env_example.txt'); $rng=[Security.Cryptography.RandomNumberGenerator]::Create(); try { $db=New-Object byte[] 24; $rng.GetBytes($db); $jwt=New-Object byte[] 48; $rng.GetBytes($jwt) } finally { $rng.Dispose() }; $dbValue=[BitConverter]::ToString($db).Replace('-','').ToLowerInvariant(); $jwtValue=[Convert]::ToBase64String($jwt); $t=[regex]::Replace($t,'(?m)^DB_PASSWORD=$','DB_PASSWORD='+$dbValue); $t=[regex]::Replace($t,'(?m)^JWT_SECRET=$','JWT_SECRET='+$jwtValue); [IO.File]::WriteAllText('.env',$t,(New-Object Text.UTF8Encoding($false)))"
if errorlevel 1 exit /b 1
exit /b 0

:migrate_env
if not exist "env_example.txt" (
    echo ERROR: env_example.txt is missing. 1>&2
    exit /b 1
)
powershell -NoProfile -Command "$existing=[IO.File]::ReadAllText('.env'); $present=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal); foreach($line in ($existing -split '\r?\n')) { if($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=') { [void]$present.Add($Matches[1]) } }; $secrets=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal); @('DB_PASSWORD','JWT_SECRET','DEEPSEEK_API_KEY','SBERGPT_API_KEY') | %% { [void]$secrets.Add($_) }; $missing=[Collections.Generic.List[string]]::new(); foreach($line in ([IO.File]::ReadAllLines('env_example.txt'))) { if($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=') { if(-not $present.Contains($Matches[1]) -and -not $secrets.Contains($Matches[1])) { $missing.Add($line.TrimEnd([char]13)) } } }; if($missing.Count -gt 0) { if($existing.Length -gt 0 -and -not ($existing.EndsWith("`n") -or $existing.EndsWith("`r"))) { [IO.File]::AppendAllText('.env',[Environment]::NewLine,(New-Object Text.UTF8Encoding($false))) }; [IO.File]::AppendAllLines('.env',$missing,(New-Object Text.UTF8Encoding($false))); exit 10 }"
if errorlevel 10 (
    echo --^> Added missing non-secret defaults from env_example.txt.
    exit /b 0
)
if errorlevel 1 exit /b 1
echo --^> Existing .env already contains all non-secret defaults.
exit /b 0

:validate_env
for /f "tokens=1,* delims==" %%A in ('findstr /R /B /C:"APP_PORT=" /C:"DB_PORT=" /C:"DEPLOY_WAIT_TIMEOUT_SECONDS=" ".env"') do set "%%A=%%B"
powershell -NoProfile -Command "$values=@{}; foreach($line in [IO.File]::ReadAllLines('.env')) { if($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { if(-not $values.ContainsKey($Matches[1])) { $values[$Matches[1]]=$Matches[2].TrimEnd([char]13) } } }; foreach($key in @('DB_PASSWORD','JWT_SECRET')) { if([string]::IsNullOrWhiteSpace($values[$key])) { throw ($key + ' must be set in .env.') } }; if([Text.Encoding]::UTF8.GetByteCount($values['JWT_SECRET']) -lt 32) { throw 'JWT_SECRET must contain at least 32 bytes.' }; foreach($key in @('APP_PORT','DB_PORT')) { $port=0; if(-not [int]::TryParse($values[$key],[ref]$port) -or $port -lt 1 -or $port -gt 65535) { throw ($key + ' must be an integer from 1 to 65535.') } }; foreach($key in @('JWT_EXPIRY_MINUTES','DEPLOY_WAIT_TIMEOUT_SECONDS')) { $number=0; if(-not [int]::TryParse($values[$key],[ref]$number) -or $number -lt 1) { throw ($key + ' must be a positive integer.') } }; foreach($key in @('LOCAL_AI_ENABLED','AI_DRIVER_FORCE_MODEL_FALLBACK','VITE_OFFLINE_MODE','VITE_ENABLE_DEMO_MODE')) { if($values[$key] -notin @('true','false')) { throw ($key + ' must be exactly true or false.') } }"
if errorlevel 1 exit /b 1
for /f "tokens=1,* delims==" %%A in ('findstr /R /B /C:"JWT_EXPIRY_MINUTES=" /C:"DEPLOY_WAIT_TIMEOUT_SECONDS=" ".env"') do set "%%A=%%B"
exit /b 0

:validate_local_model_config
powershell -NoProfile -Command "$values=@{}; foreach($line in [IO.File]::ReadAllLines('.env')) { if($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { if(-not $values.ContainsKey($Matches[1])) { $values[$Matches[1]]=$Matches[2].TrimEnd([char]13) } } }; $file=$values['QWEN_GGUF_MODEL_FILE']; $url=$values['QWEN_GGUF_MODEL_URL']; $hash=$values['QWEN_GGUF_MODEL_SHA256']; if($file -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$' -or $file.Contains('..')) { throw 'QWEN_GGUF_MODEL_FILE must be a plain file name.' }; if([string]::IsNullOrWhiteSpace($url)) { throw 'QWEN_GGUF_MODEL_URL is required for local AI.' }; if($hash -notmatch '^[0-9A-Fa-f]{64}$') { throw 'QWEN_GGUF_MODEL_SHA256 must be a 64-character SHA-256 digest.' }"
exit /b %errorlevel%

:prepare_local_model
setlocal EnableDelayedExpansion
set "QWEN_GGUF_MODEL_FILE=" & set "QWEN_GGUF_MODEL_URL=" & set "QWEN_GGUF_MODEL_SHA256="
for /f "tokens=1,* delims==" %%A in ('findstr /R /B /C:"QWEN_GGUF_MODEL_FILE=" /C:"QWEN_GGUF_MODEL_URL=" /C:"QWEN_GGUF_MODEL_SHA256=" ".env"') do set "%%A=%%B"
if not exist "models" mkdir "models"
set "MODEL_PATH=models\!QWEN_GGUF_MODEL_FILE!"
if exist "!MODEL_PATH!" goto :verify_model
echo --^> Downloading !QWEN_GGUF_MODEL_FILE! to a temporary file...
set "PART_PATH=!MODEL_PATH!.part.!RANDOM!"
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri $env:QWEN_GGUF_MODEL_URL -OutFile $env:PART_PATH"
if errorlevel 1 goto :model_download_failed
for /f %%H in ('powershell -NoProfile -Command "(Get-FileHash -LiteralPath $env:PART_PATH -Algorithm SHA256).Hash.ToLowerInvariant()"') do set "ACTUAL_SHA256=%%H"
if /I not "!ACTUAL_SHA256!"=="!QWEN_GGUF_MODEL_SHA256!" goto :model_checksum_failed
move /y "!PART_PATH!" "!MODEL_PATH!" >nul
echo --^> Model downloaded and verified.
endlocal & exit /b 0

:verify_model
echo --^> Verifying existing model !QWEN_GGUF_MODEL_FILE!...
for /f %%H in ('powershell -NoProfile -Command "(Get-FileHash -LiteralPath $env:MODEL_PATH -Algorithm SHA256).Hash.ToLowerInvariant()"') do set "ACTUAL_SHA256=%%H"
if /I "!ACTUAL_SHA256!"=="!QWEN_GGUF_MODEL_SHA256!" (
    endlocal
    exit /b 0
)

:model_checksum_failed
if defined PART_PATH del /q "!PART_PATH!" >nul 2>&1
echo ERROR: Model checksum mismatch; target model file was left unchanged. 1>&2
endlocal & exit /b 1

:model_download_failed
if defined PART_PATH del /q "!PART_PATH!" >nul 2>&1
echo ERROR: Model download failed; no target model file was created. 1>&2
endlocal & exit /b 1

:wait_for_services
setlocal EnableDelayedExpansion
set /a "deadline=%DEPLOY_WAIT_TIMEOUT_SECONDS% + 1"
:wait_loop
set "ALL_HEALTHY=true"
for %%S in (postgres ai-driver api-core frontend) do call :check_service %%S
if /I "%MODE%"=="local-ai" call :check_service qwen-local
if /I "!ALL_HEALTHY!"=="true" (
    endlocal
    exit /b 0
)
set /a "deadline-=2"
if !deadline! LEQ 0 (
    endlocal
    exit /b 1
)
timeout /t 2 /nobreak >nul
goto :wait_loop

:check_service
set "CONTAINER_ID="
for /f %%I in ('%COMPOSE% ps -q %1 2^>nul') do set "CONTAINER_ID=%%I"
if not defined CONTAINER_ID (
    set "ALL_HEALTHY=false"
    exit /b 0
)
set "CONTAINER_STATE="
for /f "tokens=1,2" %%A in ('docker inspect --format "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" !CONTAINER_ID! 2^>nul') do set "CONTAINER_STATE=%%A %%B"
if /I not "!CONTAINER_STATE!"=="running healthy" set "ALL_HEALTHY=false"
exit /b 0

:deployment_failed
echo ERROR: Deployment did not reach the required healthy state. Diagnostics follow. 1>&2
if /I "%MODE%"=="local-ai" (
    %COMPOSE% --profile local-ai ps
    %COMPOSE% --profile local-ai logs --tail=100 postgres ai-driver api-core frontend qwen-local
) else (
    %COMPOSE% ps
    %COMPOSE% logs --tail=100 postgres ai-driver api-core frontend
)
exit /b 1

:usage
echo Usage: deploy.bat [--local-ai] 1>&2
echo   no arguments starts the base stack without a local model. 1>&2
exit /b 2
