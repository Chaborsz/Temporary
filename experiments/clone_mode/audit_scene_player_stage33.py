#!/usr/bin/env python3
"""Stage33: validate Scene::getObjectPlayer ABI and usage (read-only)."""
import hashlib,pefile,capstone
from pathlib import Path
path=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(path.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
pe=pefile.PE(str(path),fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
base=pe.OPTIONAL_HEADER.ImageBase
export={base+e.address:e.name.decode("utf8","replace") for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
va=0x597780
assert "getObjectPlayer@Scene@agtk" in export.get(va,""),export.get(va)
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
data=pe.__data__[pe.get_offset_from_rva(va-base):][:500]
ins=list(md.disasm(data,va))
print("STAGE33_SCENE_PLAYER_EXPORT_PASS",export[va])
for i in range(0, min(len(ins),130),25):
 print("S33_BODY",i," | ".join(f"{hex(x.address)} {x.mnemonic} {x.op_str}" for x in ins[i:i+25])[:3000])
for v,n in export.items():
 if "getObjectPlayer@Scene@" in n or "getObjectPlayer@SceneLayer" in n or "getPlayerObject@" in n:
  print("S33_RELATED",hex(v),n)
print("STAGE33_SCENE_GET_OBJECT_PLAYER_PASS")
