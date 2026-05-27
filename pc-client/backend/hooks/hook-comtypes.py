# hooks/hook-comtypes.py
# PyInstaller hook for comtypes library
# 处理 COM 组件的特殊打包需求

from PyInstaller.utils.hooks import collect_all, collect_data_files, is_module_satisfies

# 收集 comtypes 所有依赖
datas, binaries, hiddenimports = collect_all('comtypes')

# 添加额外的隐藏导入
hiddenimports += [
    'comtypes.client',
    'comtypes.shelllink',
    'comtypes.automation',
    'comtypes.typeinfo',
    'comtypes.persist',
    'comtypes.connectionpoints',
    'comtypes.tools.tlbparser',
    'comtools',
]

# 收集 comtypes 生成的 COM 类型缓存
datas += collect_data_files('comtypes', include_py_files=True)

# 如果使用 win32com，也需要处理
try:
    import win32com
    datas += collect_data_files('win32com', include_py_files=True)
    hiddenimports += [
        'win32com.client',
        'win32com.server',
        'win32com.server.util',
        'win32com.server.policy',
    ]
except ImportError:
    pass
