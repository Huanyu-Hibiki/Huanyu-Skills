<#
.SYNOPSIS
    skill-master 一键安装脚本（Windows PowerShell）。

.DESCRIPTION
    自动完成：
    1. 检查/安装 uv（Python 包管理器）
    2. 创建 .venv 虚拟环境并安装依赖
    3. 运行健康检查

.PARAMETER Mirror
    使用国内镜像加速（清华 PyPI 镜像）。

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Mirror
#>
param(
    [switch]$Mirror
)

$ErrorActionPreference = 'Stop'
$SkillRoot = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  skill-master 一键安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ---------- Step 1: 检查/安装 uv ----------
Write-Host "[1/3] 检查 uv..." -ForegroundColor Yellow

$uvPath = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvPath) {
    Write-Host "  uv 未安装，正在安装..." -ForegroundColor Yellow
    irm https://astral.sh/uv/install.ps1 | iex

    # 刷新 PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")

    $uvPath = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uvPath) {
        Write-Host "  uv 安装失败，请关闭并重开 PowerShell 后重试。" -ForegroundColor Red
        exit 1
    }
}

$uvVersion = & uv --version 2>$null
Write-Host "  uv 已就绪：$uvVersion" -ForegroundColor Green

# ---------- Step 2: 创建环境并装依赖 ----------
Write-Host "[2/3] 创建虚拟环境并安装依赖..." -ForegroundColor Yellow

Push-Location $SkillRoot

# 创建 venv
if (-not (Test-Path ".venv")) {
    & uv venv .venv --python 3.12
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  创建虚拟环境失败。" -ForegroundColor Red
        Pop-Location
        exit 1
    }
}

# 安装依赖
$syncArgs = @("sync")
if ($Mirror) {
    $syncArgs += "--extra-index-url"
    $syncArgs += "https://pypi.tuna.tsinghua.edu.cn/simple"
}
& uv @syncArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "  安装依赖失败。" -ForegroundColor Red
    Pop-Location
    exit 1
}

Pop-Location
Write-Host "  依赖安装完成" -ForegroundColor Green

# ---------- Step 3: 健康检查 ----------
Write-Host "[3/3] 运行健康检查..." -ForegroundColor Yellow

Push-Location $SkillRoot

# Python 检查
$pythonCheck = & uv run python -c "import json; print('Python OK')" 2>&1
if ($pythonCheck -match "Python OK") {
    Write-Host "  Python 环境正常" -ForegroundColor Green
} else {
    Write-Host "  Python 环境异常：$pythonCheck" -ForegroundColor Red
}

# 脚本检查
foreach ($script in @("scanner.py", "inventory.py", "report.py")) {
    $result = & uv run python "scripts\$script" --help 2>&1
    if ($LASTEXITCODE -eq 0 -or $result) {
        Write-Host "  $script 可用" -ForegroundColor Green
    } else {
        Write-Host "  $script 异常" -ForegroundColor Yellow
    }
}

Pop-Location

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "重启 Agent 会话后即可使用。" -ForegroundColor Cyan
Write-Host "对 Agent 说「盘点我装了哪些 skill」开始体验。" -ForegroundColor Cyan
Write-Host ""
