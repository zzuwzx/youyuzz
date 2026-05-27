<#
.SYNOPSIS
    鱿郁仔仔一键构建脚本
.DESCRIPTION
    自动完成 Python 后端和 Electron 前端的打包工作
.PARAMETER SkipBackend
    跳过 Python 后端打包
.PARAMETER SkipFrontend
    跳过 Electron 前端打包
.PARAMETER Clean
    清理之前的构建产物
.EXAMPLE
    .\build.ps1
    .\build.ps1 -Clean
    .\build.ps1 -SkipBackend
#>

param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackendDir = Join-Path $RootDir "pc-client\backend"
$FrontendDir = Join-Path $RootDir "pc-client\frontend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  鱿郁仔仔 - 打包构建脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查依赖
function Test-Dependencies {
    Write-Host "检查依赖..." -ForegroundColor Yellow
    
    # Python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "✗ Python 未安装" -ForegroundColor Red
        return $false
    }
    
    # Node.js
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Host "✗ Node.js 未安装" -ForegroundColor Red
        return $false
    }
    
    # PyInstaller
    if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
        Write-Host "✗ PyInstaller 未安装，正在安装..." -ForegroundColor Yellow
        pip install pyinstaller
    }
    
    Write-Host "✓ 依赖检查通过" -ForegroundColor Green
    return $true
}

# 清理构建产物
function Clear-BuildArtifacts {
    Write-Host "清理构建产物..." -ForegroundColor Yellow
    
    $paths = @(
        (Join-Path $BackendDir "build"),
        (Join-Path $BackendDir "dist"),
        (Join-Path $FrontendDir "release"),
        (Join-Path $FrontendDir "dist"),
        (Join-Path $FrontendDir "dist-electron")
    )
    
    foreach ($path in $paths) {
        if (Test-Path $path) {
            Remove-Item -Recurse -Force $path
            Write-Host "  已删除: $path" -ForegroundColor Gray
        }
    }
    
    Write-Host "✓ 清理完成" -ForegroundColor Green
}

# 检查图标文件
function Test-IconFiles {
    Write-Host "检查图标文件..." -ForegroundColor Yellow
    
    $backendIcon = Join-Path $BackendDir "icon.ico"
    $frontendIcon = Join-Path $FrontendDir "assets\icon.ico"
    
    $hasError = $false
    
    if (-not (Test-Path $backendIcon)) {
        Write-Host "⚠ 缺少: $backendIcon" -ForegroundColor Yellow
        $hasError = $true
    }
    
    if (-not (Test-Path $frontendIcon)) {
        Write-Host "⚠ 缺少: $frontendIcon" -ForegroundColor Yellow
        $hasError = $true
    }
    
    if ($hasError) {
        Write-Host "  请添加图标文件，或使用 -NoIcon 参数跳过（待实现）" -ForegroundColor Yellow
        return $false
    }
    
    Write-Host "✓ 图标文件检查通过" -ForegroundColor Green
    return $true
}

# 打包 Python 后端
function Build-Backend {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  打包 Python 后端" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    Set-Location $BackendDir
    
    # 检查虚拟环境
    $venvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        Write-Host "使用虚拟环境 Python..." -ForegroundColor Yellow
        $pythonExe = $venvPython
    } else {
        Write-Host "使用系统 Python..." -ForegroundColor Yellow
        $pythonExe = "python"
    }
    
    # 安装依赖
    Write-Host "安装 Python 依赖..." -ForegroundColor Yellow
    & $pythonExe -m pip install -r requirements.txt -q
    
    # 运行 PyInstaller
    Write-Host "运行 PyInstaller..." -ForegroundColor Yellow
    & $pythonExe -m PyInstaller build.spec --clean --noconfirm
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Python 后端打包成功" -ForegroundColor Green
        $exePath = Join-Path $BackendDir "dist\backend.exe"
        if (Test-Path $exePath) {
            $size = (Get-Item $exePath).Length / 1MB
            Write-Host "  产物: $exePath ($([math]::Round($size, 2)) MB)" -ForegroundColor Gray
        }
        return $true
    } else {
        Write-Host "✗ Python 后端打包失败" -ForegroundColor Red
        return $false
    }
}

# 打包 Electron 前端
function Build-Frontend {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  打包 Electron 前端" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    Set-Location $FrontendDir
    
    # 安装依赖
    Write-Host "安装 Node.js 依赖..." -ForegroundColor Yellow
    npm install
    
    # 构建前端
    Write-Host "构建前端资源..." -ForegroundColor Yellow
    npm run build
    
    # 打包 Electron 应用
    Write-Host "打包 Electron 应用..." -ForegroundColor Yellow
    npm run electron:build:win
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Electron 前端打包成功" -ForegroundColor Green
        
        # 生成校验和
        $releaseDir = Join-Path $FrontendDir "release"
        if (Test-Path $releaseDir) {
            $exeFiles = Get-ChildItem -Path $releaseDir -Filter "*.exe"
            foreach ($exe in $exeFiles) {
                $hash = (Get-FileHash -Path $exe.FullName -Algorithm SHA256).Hash
                "$hash  $($exe.Name)" | Out-File -FilePath (Join-Path $releaseDir "checksums.sha256") -Append -Encoding UTF8
                Write-Host "  校验和已生成: $($exe.Name)" -ForegroundColor Gray
            }
        }
        
        return $true
    } else {
        Write-Host "✗ Electron 前端打包失败" -ForegroundColor Red
        return $false
    }
}

# 主流程
function Main {
    $startTime = Get-Date
    
    # 检查依赖
    if (-not (Test-Dependencies)) {
        Write-Host "依赖检查失败，请先安装必要的工具" -ForegroundColor Red
        exit 1
    }
    
    # 清理
    if ($Clean) {
        Clear-BuildArtifacts
    }
    
    # 构建后端
    $backendSuccess = $true
    if (-not $SkipBackend) {
        $backendSuccess = Build-Backend
    } else {
        Write-Host "跳过 Python 后端打包" -ForegroundColor Yellow
    }
    
    # 构建前端
    $frontendSuccess = $true
    if (-not $SkipFrontend) {
        if ($backendSuccess) {
            $frontendSuccess = Build-Frontend
        } else {
            Write-Host "由于后端打包失败，跳过前端打包" -ForegroundColor Red
            $frontendSuccess = $false
        }
    } else {
        Write-Host "跳过 Electron 前端打包" -ForegroundColor Yellow
    }
    
    # 完成
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  构建完成" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "耗时: $($duration.ToString('mm\:ss'))" -ForegroundColor Gray
    
    if ($backendSuccess -and $frontendSuccess) {
        Write-Host "状态: ✓ 全部成功" -ForegroundColor Green
        
        # 显示产物位置
        Write-Host ""
        Write-Host "构建产物:" -ForegroundColor Yellow
        if (-not $SkipBackend) {
            Write-Host "  - Python 后端: pc-client\backend\dist\backend.exe" -ForegroundColor Gray
        }
        if (-not $SkipFrontend) {
            Write-Host "  - 安装包: pc-client\frontend\release\" -ForegroundColor Gray
        }
    } else {
        Write-Host "状态: ✗ 部分失败" -ForegroundColor Red
        exit 1
    }
}

# 运行
Main
