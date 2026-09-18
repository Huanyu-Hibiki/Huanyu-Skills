<#
.SYNOPSIS
    oracle-bone 一键安装脚本（Windows PowerShell）。

.DESCRIPTION
    将 26 个 canonical oracle-* 子 skill 与 3 个兼容别名链接或复制到目标 skills 目录。
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
$RepoRoot = $PSScriptRoot
$SkillRoot = Join-Path $RepoRoot "skills"
$SkillName = "oracle-bone"

# 升级时仅移除指向 oracle-bone 的旧生产 skill Junction；普通目录保留人工复核（manual review）。
$retired = Join-Path $Target "oracle-edit-plan"
if (Test-Path -LiteralPath $retired) {
    $retiredItem = Get-Item -LiteralPath $retired -Force
    if ($retiredItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        # PowerShell 5.1 may not expose a junction target. If it is unavailable,
        # leave the entry for manual review rather than deleting a foreign link.
        $retiredTarget = $null
        if ($retiredItem.PSObject.Properties.Name -contains 'Target') {
            $retiredTarget = @($retiredItem.Target)[0]
        }
        $expectedRetired = [System.IO.Path]::GetFullPath((Join-Path $SkillRoot "oracle-edit-plan"))
        $resolvedRetired = $null
        if ($retiredTarget) {
            try { $resolvedRetired = [System.IO.Path]::GetFullPath([string]$retiredTarget) } catch { $resolvedRetired = $null }
        }
        if ($resolvedRetired -eq $expectedRetired) {
            [System.IO.Directory]::Delete($retired, $false)
            Write-Host "  已停用旧入口：oracle-edit-plan" -ForegroundColor Yellow
        } else {
            Write-Warning "旧入口 oracle-edit-plan 的目标无法确认，保留人工复核（manual review）。"
        }
    } else {
        Write-Warning "检测到旧目录 oracle-edit-plan，请人工确认后移除（manual review）。"
    }
}

# 只从 skills/ 收集 canonical skill 与兼容别名；仓库根目录不是子 skill 集合。
$SubSkills = Get-ChildItem -Path $SkillRoot -Directory | Where-Object { $_.Name -match '^oracle-' } | Select-Object -ExpandProperty Name

if ($SubSkills.Count -eq 0) {
    Write-Host "[$SkillName] 未找到 oracle-* 子 skill 目录。" -ForegroundColor Red
    exit 1
}

function Test-OwnedReparsePoint {
    param(
        [System.IO.FileSystemInfo]$Item,
        [string]$ExpectedPath
    )
    if (-not ($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        return $false
    }
    if (-not ($Item.PSObject.Properties.Name -contains 'Target')) {
        return $false
    }
    $target = @($Item.Target)[0]
    if (-not $target) {
        return $false
    }
    try {
        return ([System.IO.Path]::GetFullPath([string]$target) -eq [System.IO.Path]::GetFullPath($ExpectedPath))
    } catch {
        return $false
    }
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
            $expected = Join-Path $SkillRoot $sub
            if (Test-OwnedReparsePoint -Item $item -ExpectedPath $expected) {
                [System.IO.Directory]::Delete($link, $false)
                Write-Host "  已移除：$sub" -ForegroundColor Yellow
                $removed++
            } else {
                Write-Host "  跳过（非本工具链接或目标无法确认）：$sub" -ForegroundColor Gray
            }
        }
    }
    # 移除主目录链接
    $mainLink = Join-Path $Target $SkillName
    if (Test-Path -LiteralPath $mainLink) {
        $item = Get-Item -LiteralPath $mainLink -Force
        if (Test-OwnedReparsePoint -Item $item -ExpectedPath $RepoRoot) {
            [System.IO.Directory]::Delete($mainLink, $false)
            Write-Host "  已移除：$SkillName" -ForegroundColor Yellow
            $removed++
        } else {
            Write-Host "  跳过（非本工具链接或目标无法确认）：$SkillName" -ForegroundColor Gray
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
$packageRootOwned = $false

foreach ($sub in $SubSkills) {
    $source = Join-Path $SkillRoot $sub
    $link = Join-Path $Target $sub

    if (Test-Path -LiteralPath $link) {
        if ($Copy) {
            Write-Warning "已存在目录跳过：$sub（可能是旧的复制版本；如需升级请先移除该目录或使用新的 Target）"
        }
        $skipped++
        continue
    }

    if ($Copy) {
        Copy-Item -LiteralPath $source -Destination $link -Recurse -Force
        New-Item -ItemType File -Path (Join-Path $link ".oracle-bone-copy") -Force | Out-Null
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

# 复制模式必须携带共享协议树；SKILL.md 中的相对路径会读取这些目录。
# 已存在的顶层目录不覆盖，避免影响其他 skill 包。
if ($Copy) {
    $runtimeDirs = @('references', 'shared-references', 'templates', 'starter-rubrics', 'tools', 'adapters', 'hooks', 'examples')
    # Canonical SKILL.md files retain repository-relative links such as
    # ../../shared-references. With direct copies in <skills-dir>/oracle-*,
    # those links resolve from the parent of <skills-dir>; keep a package-local
    # copy beside the root entry as well so both direct and root routes work.
    $resourceRoot = Split-Path -Parent $Target
    $packageRoot = Join-Path $Target $SkillName
    if (-not (Test-Path -LiteralPath $packageRoot)) {
        New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
        $packageRootOwned = $true
    } elseif (Test-Path -LiteralPath (Join-Path $packageRoot ".oracle-bone-copy")) {
        $packageRootOwned = $true
    }
    $resourceConflicts = @()
    foreach ($dir in $runtimeDirs) {
        $resourceCandidates = @((Join-Path $resourceRoot $dir))
        if ($packageRootOwned) {
            $resourceCandidates += (Join-Path $packageRoot $dir)
        }
        foreach ($candidate in $resourceCandidates) {
            if ((Test-Path -LiteralPath $candidate) -and -not (Test-Path -LiteralPath (Join-Path $candidate ".oracle-bone-resource"))) {
                $resourceConflicts += $candidate
            }
        }
    }
    if ($resourceConflicts.Count -gt 0) {
        throw "复制安装中止：共享资源目录缺少 oracle-bone ownership marker：$($resourceConflicts -join ', ')。请使用干净 Target 或人工复核。"
    }
    foreach ($dir in $runtimeDirs) {
        $source = Join-Path $RepoRoot $dir
        $destinations = @((Join-Path $resourceRoot $dir))
        if ($packageRootOwned) {
            $destinations += (Join-Path $packageRoot $dir)
        }
        foreach ($destination in $destinations) {
            if (Test-Path -LiteralPath $destination) {
                Write-Warning "共享资源已存在，跳过：$destination"
            } else {
                Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
                New-Item -ItemType File -Path (Join-Path $destination ".oracle-bone-resource") -Force | Out-Null
                Write-Host "  已复制共享资源：$destination" -ForegroundColor Gray
            }
        }
    }
}

# 链接主目录（SKILL.md 所在目录）
$mainSource = $RepoRoot
$mainLink = Join-Path $Target $SkillName
if ($Copy) {
    if ($packageRootOwned) {
        # 复制模式下只复制根入口（子 skill 已单独复制）；不复制用户项目资料。
        if (-not (Test-Path -LiteralPath (Join-Path $mainLink "SKILL.md"))) {
            Copy-Item -LiteralPath (Join-Path $RepoRoot "SKILL.md") -Destination (Join-Path $mainLink "SKILL.md") -Force
        }
        foreach ($doc in @('DESIGN.md', 'MAINTENANCE.md', 'README.md', 'CHANGELOG.md', 'LICENSE')) {
            $docSource = Join-Path $RepoRoot $doc
            $docDestination = Join-Path $mainLink $doc
            if ((Test-Path -LiteralPath $docSource) -and -not (Test-Path -LiteralPath $docDestination)) {
                Copy-Item -LiteralPath $docSource -Destination $docDestination -Force
            }
        }
        New-Item -ItemType File -Path (Join-Path $mainLink ".oracle-bone-copy") -Force | Out-Null
    } else {
        Write-Warning "根目录已存在且不是本工具复制版本，跳过：oracle-bone"
    }
} elseif (-not (Test-Path -LiteralPath $mainLink)) {
        try {
            New-Item -ItemType Junction -Path $mainLink -Value $mainSource -ErrorAction Stop | Out-Null
        } catch {
            Write-Warning "主目录 Junction 失败，跳过。"
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
if ($Copy) {
    Write-Host "复制模式不会覆盖已有目录；升级请使用新的 Target 或先移除旧副本。" -ForegroundColor Gray
}
Write-Host "对 Agent 说「初始化 oracle-bone」开始体验。" -ForegroundColor Cyan
Write-Host ""
