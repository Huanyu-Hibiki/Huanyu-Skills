<#
.SYNOPSIS
    将 skill-master 安装到 opencode 全局 skill 目录（或移除）。

.DESCRIPTION
    首选 Junction（目录联接）方式：在目标目录创建指向本仓库的链接，
    仓库后续更新无需重新安装。Junction 创建失败时降级为复制模式
    （此时仓库更新后需重新运行本脚本）。
    幂等：重复运行不会报错，也不会重复安装。

.PARAMETER Target
    opencode 全局 skill 目录。默认 "$env:USERPROFILE\.config\opencode\skills"。

.PARAMETER Name
    安装后的 skill 目录名。默认 "skill-master"。

.PARAMETER Remove
    移除模式：仅删除链接本身（绝不递归删除源目录内容）。
    复制模式的安装不会被自动删除，会提示手动处理。

.PARAMETER WhatIf
    干跑模式：只打印将要执行的操作，不实际执行（自行实现，不依赖 -WhatIf 流）。

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Target D:\my-skills -Name skill-master
    .\install.ps1 -Remove
    .\install.ps1 -WhatIf
#>
param(
    [string]$Target = "$env:USERPROFILE\.config\opencode\skills",
    [string]$Name = "skill-master",
    [switch]$Remove,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'

$Source = $PSScriptRoot
$Link   = Join-Path $Target $Name

function Test-IsJunction {
    param([string]$Path)
    $item = Get-Item -LiteralPath $Path -Force
    return [bool]($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)
}

# ---------- 移除模式 ----------
if ($Remove) {
    if (-not (Test-Path -LiteralPath $Link)) {
        Write-Host "[skill-master] $Link 不存在，无需移除。"
        exit 0
    }
    if (Test-IsJunction -Path $Link) {
        if ($WhatIf) {
            Write-Host "[WhatIf] 将删除 junction：$Link（源目录不受影响）"
            exit 0
        }
        try {
            # 只删除重解析点本身，绝不递归进源目录内容
            [System.IO.Directory]::Delete($Link, $false)
        }
        catch {
            Write-Host "[skill-master] 错误：删除 junction 失败：$($_.Exception.Message)"
            exit 1
        }
        Write-Host "[skill-master] 已移除 junction：$Link"
        Write-Host "[skill-master] 重启 Agent 会话后生效"
        exit 0
    }
    Write-Host "[skill-master] $Link 不是 junction（复制模式安装），不会自动删除。"
    Write-Host "[skill-master] 请手动执行：Remove-Item -LiteralPath `"$Link`" -Recurse -Force"
    exit 0
}

# ---------- 安装模式（默认） ----------
if (Test-Path -LiteralPath $Link) {
    $item = Get-Item -LiteralPath $Link -Force
    if ($item.PSIsContainer) {
        $mode = if (Test-IsJunction -Path $Link) { 'junction 模式' } else { '复制模式' }
        Write-Host "[skill-master] 已安装于 $Link（$mode），无需重复安装。"
        exit 0
    }
    Write-Host "[skill-master] 错误：$Link 已存在且不是目录，请先手动处理。"
    exit 1
}

if ($WhatIf) {
    Write-Host "[WhatIf] 源仓库     ：$Source"
    Write-Host "[WhatIf] skill 目录 ：$Target（不存在则创建）"
    Write-Host "[WhatIf] 将创建 junction：$Link -> $Source"
    Write-Host "[WhatIf] （junction 失败时降级为递归复制模式）"
    exit 0
}

if (-not (Test-Path -LiteralPath $Target)) {
    New-Item -ItemType Directory -Path $Target -Force | Out-Null
    Write-Host "[skill-master] 已创建 skill 目录：$Target"
}

try {
    New-Item -ItemType Junction -Path $Link -Value $Source -ErrorAction Stop | Out-Null
    Write-Host "[skill-master] 安装成功（junction）：$Link -> $Source"
}
catch {
    Write-Warning "[skill-master] junction 创建失败：$($_.Exception.Message)，降级为复制模式。"
    Copy-Item -LiteralPath $Source -Destination $Link -Recurse -Force
    Write-Host "[skill-master] 安装成功（复制）：$Link"
    Write-Host "[skill-master] 复制模式提示：仓库后续更新需重新运行 install.ps1。"
}
Write-Host "[skill-master] 重启 Agent 会话后生效"
exit 0
