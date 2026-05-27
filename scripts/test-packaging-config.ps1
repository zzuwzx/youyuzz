<#
.SYNOPSIS
    测试打包配置
.DESCRIPTION
    验证打包所需的文件和配置是否正确
#>

param(
    [string]$RootDir = "C:\Users\wzxxx\Documents\switch 双系统自动化"
)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  鱿郁仔仔 - 打包配置测试" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

# 测试函数
function Test-Item {
    param(
        [string]$Path,
        [string]$Description,
        [switch]$IsDirectory
    )
    
    $fullPath = Join-Path $RootDir $Path
    
    if ($IsDirectory) {
        $exists = Test-Path $fullPath -PathType Container
    } else {
        $exists = Test-Path $fullPath -PathType Leaf
    }
    
    if ($exists) {
        Write-Host "✓ $Description" -ForegroundColor Green
        Write-Host "  $Path" -ForegroundColor Gray
        return $true
    } else {
        Write-Host "✗ $Description" -ForegroundColor Red
        Write-Host "  $Path" -ForegroundColor Gray
        return $false
    }
}

Write-Host "检查项目结构..." -ForegroundColor Yellow
Write-Host ""

# 后端文件
Write-Host "Python 后端:" -ForegroundColor Cyan
$allPassed = (Test-Item "pc-client\backend\main.py" "主入口文件") -and $allPassed
$allPassed = (Test-Item "pc-client\backend\requirements.txt" "依赖文件") -and $allPassed
$allPassed = (Test-Item "pc-client\backend\build.spec" "PyInstaller 配置") -and $allPassed
$allPassed = (Test-Item "pc-client\backend\hooks\hook-comtypes.py" "comtypes Hook") -and $allPassed
Write-Host ""

# 前端文件
Write-Host "Electron 前端:" -ForegroundColor Cyan
$allPassed = (Test-Item "pc-client\frontend\package.json" "package.json") -and $allPassed
$allPassed = (Test-Item "pc-client\frontend\electron-builder.yml" "electron-builder 配置") -and $allPassed
$allPassed = (Test-Item "pc-client\frontend\electron\main.ts" "Electron 主进程") -and $allPassed
$allPassed = (Test-Item "pc-client\frontend\electron\pythonBridge.ts" "Python 桥接") -and $allPassed
$allPassed = (Test-Item "pc-client\frontend\electron\preload.ts" "预加载脚本") -and $allPassed
Write-Host ""

# 安装脚本
Write-Host "安装脚本:" -ForegroundColor Cyan
$allPassed = (Test-Item "pc-client\frontend\installer\installer.nsh" "NSIS 自定义脚本") -and $allPassed
Write-Host ""

# 构建脚本
Write-Host "构建工具:" -ForegroundColor Cyan
$allPassed = (Test-Item "scripts\build.ps1" "一键构建脚本") -and $allPassed
$allPassed = (Test-Item "scripts\verify-installer.ps1" "安装包验证脚本") -and $allPassed
Write-Host ""

# 图标文件（可选）
Write-Host "图标文件（可选）:" -ForegroundColor Cyan
$hasBackendIcon = Test-Item "pc-client\backend\icon.ico" "后端图标"
$hasFrontendIcon = Test-Item "pc-client\frontend\assets\icon.ico" "前端图标"

if (-not $hasBackendIcon -or -not $hasFrontendIcon) {
    Write-Host "⚠ 图标文件缺失，打包时将使用默认图标" -ForegroundColor Yellow
    Write-Host "  参考: docs\图标准备指南.md" -ForegroundColor Gray
}
Write-Host ""

# 文档
Write-Host "文档:" -ForegroundColor Cyan
Test-Item "docs\modules\P2-M5_打包发布.md" "详细方案文档" | Out-Null
Test-Item "docs\打包发布指南.md" "操作指南" | Out-Null
Test-Item "docs\图标准备指南.md" "图标准备指南" | Out-Null
Write-Host ""

# 总结
Write-Host "========================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "  ✓ 配置检查通过" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "可以开始打包！" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步:" -ForegroundColor Yellow
    Write-Host "  1. 添加图标文件（可选）" -ForegroundColor Gray
    Write-Host "  2. 运行: scripts\build.ps1" -ForegroundColor Gray
} else {
    Write-Host "  ✗ 配置检查失败" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "请修复上述问题后重试" -ForegroundColor Yellow
}
Write-Host ""
