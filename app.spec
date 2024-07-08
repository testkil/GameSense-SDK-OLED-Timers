# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['main.py'],
             pathex=['.'],
             binaries=[],
             datas=[('stopwatch.ico', '.')],  # Ensure the icon is included
             hiddenimports=['pystray._util.win32', 'pynput'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='TimerApp',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,  # Set to True if you want a console window
          icon='stopwatch.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='TimerApp')