"""
setup.py - macOS app bundle build script py2app segítségével

HASZNÁLAT (csak macOS-en működik!):
    1. python3 -m venv venv
       source venv/bin/activate
    2. pip install py2app customtkinter pillow pycryptodome
    3. python setup.py py2app

    A kész app itt lesz: dist/StegBen.app

Ha teszt buildet akarsz (gyorsabb, de csak a saját géped futtatja):
    python setup.py py2app -A
    (alias/dev mód - nem terjeszthető, de gyors iterációhoz jó)
"""

from setuptools import setup
import customtkinter
import os

APP = ['beta.py']
APP_NAME = 'StegBen'

# --- Ikon ---
# Az .icns fájlt elő kell állítani egy .png-ből (pl. a Szteganosaurus logóból):
#   mkdir icon.iconset
#   sips -z 16 16     logo.png --out icon.iconset/icon_16x16.png
#   sips -z 32 32     logo.png --out icon.iconset/icon_16x16@2x.png
#   sips -z 32 32     logo.png --out icon.iconset/icon_32x32.png
#   sips -z 64 64     logo.png --out icon.iconset/icon_32x32@2x.png
#   sips -z 128 128   logo.png --out icon.iconset/icon_128x128.png
#   sips -z 256 256   logo.png --out icon.iconset/icon_128x128@2x.png
#   sips -z 256 256   logo.png --out icon.iconset/icon_256x256.png
#   sips -z 512 512   logo.png --out icon.iconset/icon_256x256@2x.png
#   sips -z 512 512   logo.png --out icon.iconset/icon_512x512.png
#   cp logo.png (1024x1024-es) icon.iconset/icon_512x512@2x.png
#   iconutil -c icns icon.iconset -o icon.icns
ICON_FILE = 'icon.icns'  # ha nincs kész, kommenteld ki lent az 'iconfile' sort

# --- customtkinter asset mappa (téma JSON-ök, betűtípusok) ---
# py2app alapból csak a .py fájlokat viszi be a site-packages-ből,
# a customtkinter viszont futásidőben tölt be .json (téma) és .otf (font)
# fájlokat is -> ezeket explicit be kell húzni, különben az app
# "FileNotFoundError: assets/themes/..." hibával elszáll indításkor.
ctk_path = os.path.dirname(customtkinter.__file__)
ctk_assets = (
    'customtkinter',
    [os.path.join(ctk_path, 'assets')]
)

DATA_FILES = []

OPTIONS = {
    'argv_emulation': False,   # True esetén gond lehet drag&drop-pal / file dialogokkal
    'iconfile': ICON_FILE,
    'packages': [
        'customtkinter',   # egészben bevisszük -> assetek is jönnek vele
        'PIL',
        'Crypto',           # pycryptodome
    ],
    'includes': [
        'tkinter',
    ],
    'excludes': [
        'matplotlib', 'numpy', 'scipy',  # ha nem használod, kispórolható -> kisebb app
    ],
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleIdentifier': 'com.benkovszky.stegben',
        'CFBundleVersion': '1.2.0',
        'CFBundleShortVersionString': '1.2.0',
        'NSHumanReadableCopyright': 'Benkovszky László',
        'NSHighResolutionCapable': True,
    },
}

setup(
    app=APP,
    name=APP_NAME,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)