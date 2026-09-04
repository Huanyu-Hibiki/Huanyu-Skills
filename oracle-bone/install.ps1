<#
.SYNOPSIS
    oracle-bone 一键安装脚本（Windows PowerShell）。

.DESCRIPTION
    将 26 个 oracle-* 子 skill 链接或复制到目标 skills 目录。
    默认使用 Junction（目录联接）方式，仓库更新自动生效。

.PARAMETER Target
    目标 skills 目录。默认 "$env:USERPROFILE\.claude\skills"。

.PARAMETER Copy
    冻结模式：复制而非链接（仓库更新后需重新运行）。

.PARAMETER Remove
    卸载模式：移除已安装的链接（不动内容数据）。

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Target D:\my-skills
    .\install.ps1 -Copy
    .\install.ps1 -Remove
#>
param(
    [string]$Target = "$env:USERPROFILE\.claude\skills",
    [switch]$Copy,
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$SkillRoot = $PSScriptRoot
$SkillName = "oracle-bone"

# 收集所有 oracle-* 子目录
$SubSkills = Get-ChildItem -Path $SkillRoot -Directory | Where-Object { $_.Name -match '^oracle-' } | Select-Object -ExpandProperty Name

if ($SubSkills.Count -eq 0) {
    Write-Host "[$SkillName] 未找到 oracle-* 子 skill 目录。" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  oracle-bone 安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ---------- 移除模式 ----------
if ($Remove) {
    $removed = 0
    foreach ($sub in $SubSkills) {
        $link = Join-Path $Target $sub
        if (Test-Path -LiteralPath $link) {
            $item = Get-Item -LiteralPath $link -Force
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                [System.IO.Directory]::Delete($link, $false)
                Write-Host "  已移除：$sub" -ForegroundColor Yellow
                $removed++
            } else {
                Write-Host "  跳过（非链接）：$sub" -ForegroundColor Gray
            }
        }
    }
    # 移除主目录链接
    $mainLink = Join-Path $Target $SkillName
    if (Test-Path -LiteralPath $mainLink) {
        $item = Get-Item -LiteralPath $mainLink -Force
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            [System.IO.Directory]::Delete($mainLink, $false)
            Write-Host "  已移除：$SkillName" -ForegroundColor Yellow
            $removed++
        }
    }
    Write-Host ""
    Write-Host "已移除 $removed 个链接。重启 Agent 会话后生效。" -ForegroundColor Green
    exit 0
}

# ---------- 安装模式 ----------
if (-not (Test-Path -LiteralPath $Target)) {
    New-Item -ItemType Directory -Path $Target -Force | Out-Null
    Write-Host "  已创建目录：$Target" -ForegroundColor Gray
}

$installed = 0
$skipped = 0

foreach ($sub in $SubSkills) {
    $source = Join-Path $SkillRoot $sub
    $link = Join-Path $Target $sub

    if (Test-Path -LiteralPath $link) {
        $skipped++
        continue
    }

    if ($Copy) {
        Copy-Item -LiteralPath $source -Destination $link -Recurse -Force
    } else {
        try {
            New-Item -ItemType Junction -Path $link -Value $source -ErrorAction Stop | Out-Null
        } catch {
            Write-Warning "Junction 失败：$sub，降级为复制模式。"
            Copy-Item -LiteralPath $source -Destination $link -Recurse -Force
        }
    }
    $installed++
}

# 链接主目录（SKILL.md 所在目录）
$mainSource = $SkillRoot
$mainLink = Join-Path $Target $SkillName
if (-not (Test-Path -LiteralPath $mainLink)) {
    if ($Copy) {
        # 复制模式下只复制 SKILL.md 等根文件（子目录已单独复制）
        Copy-Item -LiteralPath (Join-Path $SkillRoot "SKILL.md") -Destination (Join-Path $Target $SkillName "\SKILL.md") -Force -ErrorAction SilentlyContinue
    } else {
        try {
            New-Item -ItemType Junction -Path $mainLink -Value $mainSource -ErrorAction Stop | Out-Null
        } catch {
            Write-Warning "主目录 Junction 失败，跳过。"
        }
    }
}

$mode = if ($Copy) { "复制" } else { "Junction" }
Write-Host ""
Write-Host "安装完成（$mode 模式）：" -ForegroundColor Green
Write-Host "  新安装：$installed 个子 skill" -ForegroundColor Green
if ($skipped -gt 0) {
    Write-Host "  已存在：$skipped 个（跳过）" -ForegroundColor Gray
}
Write-Host ""
Write-Host "重启 Agent 会话后即可使用。" -ForegroundColor Cyan
Write-Host "对 Agent 说「初始化 oracle-bone」开始体验。" -ForegroundColor Cyan
Write-Host ""
