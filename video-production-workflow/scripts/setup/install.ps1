# ============================================================================
# video-production-workflow 一键依赖安装脚本（Windows）
# 适用：PowerShell 5.1+。小白直接右键"使用 PowerShell 运行"，或在 PowerShell 中：
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#
# 可选参数：
#   -Mirror       使用国内镜像（清华 PyPI + modelscope）加速下载
#   -SkipModels   只装依赖，不下载 AI 模型（模型也可稍后单独下载）
#   -AutoInstall  静默模式：FFmpeg/Node 缺失时自动 winget 安装、模型自动下载（无人值守/CI 用）
#   -ModelSource  模型下载源：auto（自动判断）/ modelscope（国内魔搭）/ huggingface（国外）
# 用法示例：
#   .\install.ps1 -Mirror
#   .\install.ps1 -Mirror -ModelSource modelscope -SkipModels
#   .\install.ps1 -ModelSource huggingface
#   .\install.ps1 -AutoInstall -Mirror    # 全自动无人值守
# ============================================================================
param(
    [switch]$Mirror,
    [switch]$SkipModels,
    [switch]$AutoInstall,
    [string]$ModelSource = "auto"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$SkillRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $SkillRoot

function Write-Step($msg)  { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "    [!]  $msg" -ForegroundColor Yellow }
function Write-Fail($msg)  { Write-Host "    [X]  $msg" -ForegroundColor Red }

Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "  video-production-workflow 依赖一键安装" -ForegroundColor Magenta
Write-Host "  安装目录: $SkillRoot" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta

# ---------------------------------------------------------------------------
# 1. uv（Python 包管理器，本 Skill 唯一的 Python 环境入口）
# ---------------------------------------------------------------------------
Write-Step "检查 uv（Python 包管理器）"

$hasUv = $false
try { uv --version 2>$null | Out-Null; $hasUv = $true } catch { }

if ($hasUv) {
    Write-Ok "uv 已安装: $(uv --version)"
} else {
    Write-Warn2 "未检测到 uv，开始自动安装（约 20 秒）..."
    try {
        powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    } catch {
        Write-Fail "uv 自动安装失败，请手动执行：irm https://astral.sh/uv/install.ps1 | iex"
        Write-Fail "安装完成后【关闭并重开 PowerShell】再运行本脚本"
        exit 1
    }
    # 刷新当前会话的 PATH
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    try { uv --version | Out-Null; Write-Ok "uv 安装成功: $(uv --version)" }
    catch {
        Write-Fail "uv 已安装但当前窗口找不到命令"
        Write-Fail "请【关闭并重开 PowerShell】，再运行一次：powershell -ExecutionPolicy Bypass -File .\scripts\setup\install.ps1"
        exit 1
    }
}

# 国内镜像：加速 Python 包下载（PyTorch GPU 源已在 pyproject.toml 固定，不受影响）
if ($Mirror) {
    $env:UV_DEFAULT_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"
    Write-Ok "已启用清华 PyPI 镜像"
}

# ---------------------------------------------------------------------------
# 2. FFmpeg（视频处理核心，粗剪/合成/抽帧都要用）
# ---------------------------------------------------------------------------
Write-Step "检查 FFmpeg"

$hasFfmpeg = $false
try { ffmpeg -version 2>$null | Select-Object -First 1 | Out-Null; $hasFfmpeg = $true } catch { }

if ($hasFfmpeg) {
    Write-Ok "FFmpeg 已安装"
} else {
    $wingetOk = $false
    try { winget --version 2>$null | Out-Null; $wingetOk = $true } catch { }
    if ($wingetOk) {
        $answer = "y"
        if (-not $AutoInstall) { $answer = Read-Host "    未检测到 FFmpeg。现在用 winget 自动安装吗？(y/n)" }
        if ($answer -eq "y" -or $answer -eq "Y") {
            winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
            Write-Warn2 "winget 安装后需要【重开 PowerShell】才能识别 ffmpeg 命令"
        } else {
            Write-Warn2 "跳过。请自行安装后重开 PowerShell：winget install Gyan.FFmpeg"
            Write-Warn2 "或到 https://www.gyan.dev/ffmpeg/builds/ 下载并加入 PATH"
        }
    } else {
        Write-Warn2 "未检测到 FFmpeg 和 winget。请到 https://www.gyan.dev/ffmpeg/builds/ 下载"
        Write-Warn2 "解压后把 bin 目录加入系统 PATH 环境变量（可搜索：Windows FFmpeg 安装教程）"
    }
}

# ---------------------------------------------------------------------------
# 3. Node.js 18+（Remotion 动效 / HyperFrames 检查脚本需要）
# ---------------------------------------------------------------------------
Write-Step "检查 Node.js（Remotion / HyperFrames 需要，18 以上版本）"

$hasNode = $false
$nodeVer = ""
try { $nodeVer = (node --version 2>$null); if ($nodeVer) { $hasNode = $true } } catch { }

if ($hasNode) {
    Write-Ok "Node.js 已安装: $nodeVer"
} else {
    $wingetOk = $false
    try { winget --version 2>$null | Out-Null; $wingetOk = $true } catch { }
    if ($wingetOk) {
        $answer = "y"
        if (-not $AutoInstall) { $answer = Read-Host "    未检测到 Node.js。现在用 winget 自动安装 LTS 版吗？(y/n)" }
        if ($answer -eq "y" -or $answer -eq "Y") {
            winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
            Write-Warn2 "安装后需要【重开 PowerShell】才能识别 node 命令"
        } else {
            Write-Warn2 "跳过。不做 Remotion 动效可以暂时不装；需要时运行：winget install OpenJS.NodeJS.LTS"
        }
    } else {
        Write-Warn2 "未检测到 Node.js。请到 https://nodejs.org/ 下载 LTS 版安装"
        Write-Warn2 "不做 Remotion 动效可以暂时不装"
    }
}

# ---------------------------------------------------------------------------
# 4. Python 虚拟环境（uv 自动管理 Python 3.11，无需预先安装 Python）
# ---------------------------------------------------------------------------
Write-Step "创建 Python 虚拟环境并安装依赖（首次约 5-15 分钟，含 PyTorch GPU 版约 3GB）"

uv venv .venv --python 3.11
if ($LASTEXITCODE -ne 0) { Write-Fail "创建虚拟环境失败"; exit 1 }

uv sync
if ($LASTEXITCODE -ne 0) {
    Write-Fail "依赖安装失败。若因网络超时，可加 -Mirror 参数用国内镜像重试："
    Write-Fail "    powershell -ExecutionPolicy Bypass -File .\scripts\setup\install.ps1 -Mirror"
    exit 1
}
Write-Ok "Python 环境就绪: .venv"

# ---------------------------------------------------------------------------
# 5. 自检
# ---------------------------------------------------------------------------
Write-Step "环境自检"

uv run python -c "import torch; print('    torch', torch.__version__, '| CUDA 可用:', torch.cuda.is_available())"
if ($LASTEXITCODE -ne 0) { Write-Fail "torch 导入失败"; exit 1 }

Write-Ok "依赖安装完成"

# ---------------------------------------------------------------------------
# 6. AI 模型下载（本地转录模型，默认下载到 Skill 目录下的 models\）
# ---------------------------------------------------------------------------
if ($SkipModels) {
    Write-Step "按参数跳过模型下载。稍后可随时运行："
    Write-Host "    uv run python scripts\setup\download_models.py --source auto" -ForegroundColor White
} else {
    Write-Step "下载 AI 转录模型 faster-whisper large-v3（约 3GB，默认引擎，Windows 友好）"
    Write-Host "    国内网络自动使用魔搭 ModelScope，国外自动使用 HuggingFace"
    $answer = "y"
    if (-not $AutoInstall) { $answer = Read-Host "    现在下载吗？(y=下载 / n=跳过，稍后手动下载)" }
    if ($answer -eq "y" -or $answer -eq "Y") {
        uv run python scripts\setup\download_models.py --source $ModelSource
        if ($LASTEXITCODE -ne 0) {
            Write-Warn2 "模型下载未完成。可稍后手动重试："
            Write-Host "    uv run python scripts\setup\download_models.py --source modelscope" -ForegroundColor White
            Write-Host "    uv run python scripts\setup\download_models.py --source huggingface" -ForegroundColor White
        }
    } else {
        Write-Warn2 "跳过模型下载。粗剪前需要先运行："
        Write-Host "    uv run python scripts\setup\download_models.py --source auto" -ForegroundColor White
    }
}

# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "  安装流程结束" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "下一步：" -ForegroundColor Magenta
Write-Host "  1. 复制 .env.example 为 .env，按需填写 API Key（本地转录不需要任何 Key）"
Write-Host "  2. 在 Agent（Claude Code / OpenCode 等）中对该视频项目说：初始化视频制作管线"
Write-Host "  详细教程见 README.md「第一次使用」章节"
