import os
import subprocess
from pathlib import Path

cmd = [
    'python',
    '-m', 'PyInstaller',
    'serialqt.pyw', # your main file with ui.run()
    '--name', 'SevenSerial', # name of your app
#    '--onefile',
    '--windowed', # prevent console appearing, only use with ui.run(native=True, ...)
    '--add-data', 'core:core',
    '--add-data', 'plugins:plugins',
    '--add-data', 'ui:ui',
    '--collect-submodules', 'pykka',
    '--collect-submodules', 'yapsy',
    '--collect-submodules', 'stransi',
    '--collect-submodules', 'pylink',
]
print(cmd)
subprocess.call(cmd)
