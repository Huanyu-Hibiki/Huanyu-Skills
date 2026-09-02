# ============================================================================
# run_transcribe.ps1 — Windows 原生转录入口（对应 run_transcribe.sh）
#
# 用法:
#   powershell -ExecutionPolicy Bypass -File .\run_transcribe.ps1 <video.mp4> [base_output_dir] [--local|--flash|--v3-standard|--auto]
#
# 引擎选项（默认 local）:
#   --local       使用本地 faster-whisper（备选 whisper），不需要 VOLCENGINE_API_KEY
#   --flash / --v3-standard / --auto
#                 云端火山引擎引擎：需要 Git Bash（脚本委托 run_transcribe.sh 执行）
#
# 输出: base_output_dir/1_转录/
#   ├── audio.mp3
#   ├── local_transcript.json（本地引擎）或 volcengine_v3_result.json（云端引擎）
#   └── subtitles_words.json
# ============================================================================
param(
    [Parameter(Position = 0)][string]$VideoPath,
    [Parameter(Position = 1)][string]$BaseDir = ".",
    [Parameter(Position = 2)][string]$Engine = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

# 引擎 flag 兼容（--local 等作为任意位置参数传入时）
foreach ($arg in $args) {
    switch -Regex ($arg) {
        '^--local$|^--whisper$' { $Engine = "local" }
        '^--v3-standard$' { $Engine = "v3-standard" }
        '^--flash$' { $Engine = "flash" }
        '^--auto$' { $Engine = "auto" }
        '^--engine=(.+)$' { $Engine = $Matches[1] }
    }
}

if (-not $VideoPath) {
    Write-Host "用法: .\run_transcribe.ps1 <video.mp4> [base_output_dir] [--local|--flash|--v3-standard|--auto]"
    exit 1
}
if (-not (Test-Path -LiteralPath $VideoPath)) {
    Write-Host "[X] 视频文件不存在: $VideoPath"
    exit 1
}

# 合集根 = 本脚本向上两级（scripts/video-caption-correct/ -> 合集根）
$WorkflowDir = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

# 读 .env 的 TRANSCRIPTION_ENGINE 作为默认引擎
if (-not $Engine) {
    $Engine = "local"
    $envFile = Join-Path $WorkflowDir ".env"
    if (Test-Path -LiteralPath $envFile) {
        foreach ($line in Get-Content -LiteralPath $envFile -Encoding UTF8) {
            if ($line -match '^\s*TRANSCRIPTION_ENGINE\s*=\s*(\S+)') { $Engine = $Matches[1] }
        }
    }
}

# 虚拟环境 Python（不回退系统 Python / Anaconda）
$PythonBin = Join-Path $WorkflowDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonBin)) {
    Write-Host "[X] 找不到 Skill 虚拟环境: $PythonBin"
    Write-Host "    请先在 $WorkflowDir 执行: powershell -ExecutionPolicy Bypass -File .\scripts\setup\install.ps1"
    exit 1
}

if ($Engine -ne "local") {
    # 云端引擎走 bash 版脚本（依赖 curl/openssl 组合逻辑）
    $bash = Get-Command bash -ErrorAction SilentlyContinue
    if ($bash) {
        & bash (Join-Path $PSScriptRoot "run_transcribe.sh") $VideoPath $BaseDir "--engine=$Engine"
        exit $LASTEXITCODE
    }
    Write-Host "[X] 云端引擎 ($Engine) 需要 Git Bash；或先安装: https://git-scm.com/download/win"
    Write-Host "    本地转录不需要 Bash：加 --local 即可"
    exit 1
}

foreach ($cmd in @("ffmpeg")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "[X] 缺少依赖: $cmd (winget install Gyan.FFmpeg 后重开 PowerShell)"
        exit 1
    }
}

$env:PYTHONUTF8 = "1"

$TranscribeDir = Join-Path $BaseDir "1_转录"
New-Item -ItemType Directory -Force -Path $TranscribeDir | Out-Null

# ── 步骤 1: 提取音频 ────────────────────────────────────
Write-Host "[1/3] 提取音频..."
& ffmpeg -i "file:$VideoPath" -vn -acodec libmp3lame -y (Join-Path $TranscribeDir "audio.mp3") 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "[X] 音频提取失败"; exit 1 }
Write-Host "[OK] 音频已保存: $TranscribeDir\audio.mp3"

# ── 步骤 2+3: 本地 faster-whisper 转录 ─────────────────
Write-Host "[2/3] 本地 faster-whisper 转录..."
$LocalEditDir = Join-Path $TranscribeDir "local"
& $PythonBin (Join-Path $WorkflowDir "scripts\video-rough-cut\transcribe.py") $VideoPath --edit-dir $LocalEditDir
if ($LASTEXITCODE -ne 0) { Write-Host "[X] 转录失败"; exit 1 }

$VideoStem = [System.IO.Path]::GetFileNameWithoutExtension($VideoPath)
$LocalResult = Join-Path $LocalEditDir "transcripts\$VideoStem.json"
if (-not (Test-Path -LiteralPath $LocalResult)) {
    Write-Host "[X] 本地转录没有生成结果: $LocalResult"
    exit 1
}
Copy-Item -LiteralPath $LocalResult -Destination (Join-Path $TranscribeDir "local_transcript.json") -Force

# ── 步骤 4: 词级字幕 ───────────────────────────────────
Write-Host "[3/3] 生成词级字幕..."
& $PythonBin (Join-Path $WorkflowDir "scripts\video-rough-cut\whisper_to_subtitles_words.py") $LocalResult (Join-Path $TranscribeDir "subtitles_words.json")
if ($LASTEXITCODE -ne 0) { Write-Host "[X] 字幕生成失败"; exit 1 }

Write-Host ""
Write-Host "[OK] 流水线完成！输出目录: $TranscribeDir"
Get-ChildItem -LiteralPath $TranscribeDir -File | ForEach-Object { Write-Host ("     {0}  {1:N1} KB" -f $_.Name, ($_.Length / 1KB)) }
