"""Write PyInstaller version info so Windows shows WANDERCOIL as the publisher. Usage: make_version.py v0.2.1"""
import re
import sys

tag = sys.argv[1] if len(sys.argv) > 1 else "v0.0.0"
nums = [int(n) for n in re.findall(r"\d+", tag)[:3]] + [0, 0, 0]
a, b, c = nums[:3]
version = f"{a}.{b}.{c}"

open("version_info.txt", "w", encoding="utf-8").write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({a}, {b}, {c}, 0), prodvers=({a}, {b}, {c}, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'WANDERCOIL'),
      StringStruct('FileDescription', 'Lens It - find yourself in every moment'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'LensIt'),
      StringStruct('LegalCopyright', 'Copyright (C) 2026 WANDERCOIL. AGPL-3.0'),
      StringStruct('LegalTrademarks', 'Lens It and Wandercoil are trademarks of Wandercoil'),
      StringStruct('OriginalFilename', 'LensIt.exe'),
      StringStruct('ProductName', 'Lens It'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""")
print("version_info.txt for", version)
