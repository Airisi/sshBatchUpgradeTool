# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],  # 主程序文件
    pathex=[''],  # 项目路径
    binaries=[],
    datas=[
        ('config.json', '.'),  # 包含配置文件
        ('readme.md', '.'),  # 包含说明文件
        ('requirements.txt', '.'),  # 包含依赖文件
        ('ssh_manager.py', '.'),  # 包含Python文件
        ('upgrade_manager.py', '.'),  # 包含Python文件
        ('ui\main_window.ui', 'ui')  # 包含UI文件
    ],
    hiddenimports=[
        'PyQt5',
        'pandas',
        'asyncio',
        'asyncssh',
        'numpy',
        'paramiko',
        'cryptography',
        'openpyxl',
        'cffi',
        'PyNaCl',
        'python-dateutil',
        'pytz',
        'tzdata',
        'bcrypt',
        'et_xmlfile',
        'six',
        'typing_extensions',
        # 添加任何其他需要的隐藏导入
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UpgradeTool',
    debug=False,  # True 启用调试模式
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # True 启用控制台窗口以查看错误信息
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SSHTool',
)
