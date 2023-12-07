import os
import subprocess
from pathlib import Path
import customtkinter

cmd = [
    'python',
    '-m', 'PyInstaller',
    'serialtk.py', # your main file with ui.run()
    '--name', 'SevenSerial', # name of your app
    '--onedir',
    '--windowed', # prevent console appearing, only use with ui.run(native=True, ...)
    '--add-data', 'core:core',
    '--add-data', 'plugins:plugins',
    '--add-data', 'ui:ui',
    '--add-data', f'{Path(customtkinter.__file__).parent}:customtkinter',
    '--collect-submodules', 'pykka',
    '--collect-submodules', 'yapsy',
    '--collect-submodules', 'stransi',
    '--collect-submodules', 'pylink',
    '--collect-submodules', 'pyserial',
    '--collect-submodules', 'customtkinter',
]
print(cmd)
subprocess.call(cmd)
