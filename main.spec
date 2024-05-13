# -*- mode: python ; coding: utf-8 -*-

"""
This file is part of the PetalVault password manager distribution. See <https://github.com/F33RNI/PetalVault>.

Copyright (C) 2024 Fern Lane

This program is free software: you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.
If not, see <http://www.gnu.org/licenses/>.
"""

import os
import platform

import PyInstaller.config

# Set working path
PyInstaller.config.CONF["workpath"] = "./build"

SOURCE_FILES = [
    "main.py",
    "clear_layout.py",
    "combo_box_dialogue.py",
    "config_manager.py",
    "encrypt_decrypt.py",
    "get_resource_path.py",
    "gui_main_window.py",
    "gui_wrapper.py",
    "mnemonic_dialogue.py",
    "qr_scanner_thread.py",
    "scan_dialogue.py",
    "translator.py",
    "_version.py",
    "view_dialogue.py",
]

# Final name
COMPILE_NAME = f"petalvault-{platform.system()}-{platform.machine()}".lower()

# Files and folders to include inside builded binary
INCLUDE_FILES = [
    (os.path.join("langs", "*.json"), "langs"),
    (os.path.join("icons", "*.*"), "icons"),
    (os.path.join("forms", "*.*"), "forms"),
    ("wordlist.txt", "."),
    ("LICENSE", "."),
]

block_cipher = None

a = Analysis(
    SOURCE_FILES,
    pathex=[],
    binaries=[],
    datas=INCLUDE_FILES,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["_bootlocale"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=COMPILE_NAME,
    debug=False,
    bootloader_ignore_signals=True,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join("icons", "icon.ico")],
)
