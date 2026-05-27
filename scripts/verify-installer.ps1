<#
.SYNOPSIS
    验证安装包完整性
.DESCRIPTION
    使用 SHA256 校验和验证安装包是否被篡改
.PARAMETER InstallerPath
    安装包文件路径
.PARAMETER ChecksumFile
    校验和文件路径（默认: checksums.sha256）
.EXAMPLE
    .\verify-installer.ps1 -InstallerPath "release\鱿郁仔仔 Setup 0.2.0.exe"
    .\verify-installer.ps1 -InstallerPath "release\鱿郁仔仔 Setup 0.2.0.exe" -ChecksumFile "release\checksums.sha256"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$InstallerPath,
    
    [Parameter(Mandatory=$false)]
    [string]$ChecksumFile = "checksums.sha256"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  鱿郁仔仔 - 安装包完整性验证" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查文件是否存在
if (-not (Test-Path $InstallerPath)) {
    Write-Host "✗ 安装包文件不存在: $InstallerPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ChecksumFile)) {
    Write-Host "✗ 校验和文件不存在: $ChecksumFile" -ForegroundColor Red
    exit 1
}

# 获取文件名
$fileName = Split-Path -Leaf $InstallerPath
Write-Host "验证文件: $fileName" -ForegroundColor Yellow

# 计算实际哈希值
Write-Host "计算 SHA256 哈希..." -ForegroundColor Gray
$actualHash = (Get-FileHash -Path $InstallerPath -Algorithm SHA256).Hash

# 从校验和文件中读取期望的哈希值
$checksumContent = Get-Content $ChecksumFile -Encoding UTF8
$expectedLine = $checksumContent | Where-Object { $_ -match [regex]::Escape($fileName) }

if (-not $expectedLine) {
    Write-Host "✗ 在校验和文件中未找到该文件的记录" -ForegroundColor Red
    Write-Host ""
    Write-Host "可用的文件记录:" -ForegroundColor Yellow
    $checksumContent | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    exit 1
}

# 解析期望的哈希值
$expectedHash = ($expectedLine -split '\s+')[0].ToUpper()

Write-Host ""
Write-Host "期望哈希: $expectedHash" -ForegroundColor Gray
Write-Host "实际哈希: $actualHash" -ForegroundColor Gray
Write-Host ""

# 验证
if ($expectedHash -eq $actualHash) {
    Write-Host "✓ 验证通过" -ForegroundColor Green
    Write-Host "  安装包完整，未被篡改" -ForegroundColor Green
    Write-Host ""
    
    # 显示文件信息
    $fileInfo = Get-Item $InstallerPath
    $sizeMB = [math]::Round($fileInfo.Length / 1MB, 2)
    Write-Host "文件信息:" -ForegroundColor Yellow
    Write-Host "  大小: $sizeMB MB" -ForegroundColor Gray
    Write-Host "  修改时间: $($fileInfo.LastWriteTime)" -ForegroundColor Gray
    
    exit 0
} else {
    Write-Host "✗ 验证失败" -ForegroundColor Red
    Write-Host "  文件可能被篡改或损坏" -ForegroundColor Red
    Write-Host ""
    Write-Host "请重新下载安装包或联系开发者。" -ForegroundColor Yellow
    exit 1
}
