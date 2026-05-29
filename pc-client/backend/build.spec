# -*- mode: python ; coding: utf-8 -*-
# 鱿郁仔仔 - PyInstaller 打包配置
# 使用方法: pyinstaller build.spec --clean --noconfirm

import sys
from pathlib import Path

block_cipher = None

# 获取项目根目录
BASE_DIR = Path(SPECPATH).resolve()

# 检查图标文件是否存在
ICON_PATH = BASE_DIR / 'icon.ico'
ICON_FILE = str(ICON_PATH) if ICON_PATH.exists() else None

if ICON_FILE is None:
    print(f"[警告] 图标文件不存在: {ICON_PATH}")
    print("[提示] 请参考 docs/图标准备指南.md 添加图标文件")

a = Analysis(
    ['main.py'],
    pathex=[str(BASE_DIR)],
    binaries=[
        # libmtp DLL（如果需要）
        # ('path/to/libmtp.dll', '.'),
        # ('path/to/libusb-1.0.dll', '.'),
    ],
    datas=[
        # Playwright 浏览器（首次启动下载，不打包）
        # 如果需要打包，取消下面注释
        # (str(BASE_DIR / 'playwright_browsers'), 'playwright/browsers'),
    ],
    hiddenimports=[
        # Windows COM 支持
        'win32com',
        'win32com.client',
        'win32com.server',
        'comtypes',
        'comtypes.client',
        'comtypes.shelllink',
        'comtypes.automation',
        'comtypes.typeinfo',
        
        # FastAPI 相关
        'fastapi',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        
        # Pydantic
        'pydantic',
        'pydantic.fields',
        'pydantic.networks',
        
        # 其他依赖
        'httpx',
        'multipart',
        'dotenv',
        'rich',
        'rich.console',
        'rich.logging',
        
        # 项目模块
        'api',
        'api.device',
        'api.install',
        'api.models',
        'api.search',
        'api.settings',
        'api.system',
        'cache',
        'cache.manager',
        'cache.models',
        'cache.storage',
        'cloud_disk',
        'cloud_disk.aliyun',
        'cloud_disk.baidu',
        'cloud_disk.base',
        'cloud_disk.kuake',
        'cloud_disk.models',
        'game_files',
        'game_files.cheat',
        'game_files.classifier',
        'game_files.models',
        'mtp',
        'mtp.base',
        'mtp.dbi_discovery',
        'mtp.ifile_operation',
        'mtp.shell_copy_here',
        'mtp.transfer_worker',
        'mtp.wpd_backend',
    ],
    hookspath=[str(BASE_DIR / 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'IPython',
        'jupyter',
        'notebook',
    ],
    noarchive=False,
    optimize=0,
)

# 创建 PYZ 归档
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 创建可执行文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 设置为 False 隐藏控制台窗口（调试时保持 True）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE,  # 如果没有图标文件则使用默认图标
)
