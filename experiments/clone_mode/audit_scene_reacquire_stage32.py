#!/usr/bin/env python3
"""Read-only Stage32: identify native player objects and scene active object accessors."""
import pefile, hashlib, capstone
from pathlib import Path
p=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(p.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
exe=pefile.PE(str(p),fast_load=True)
exe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
b=exe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for v in exe.DIRECTORY_ENTRY_EXPORT.symbols:
 if not v.name:continue
 n=v.name.decode("utf-8","replace");low=n.lower()
 target= ("@scene@agtk" in low or "@scenelayer@agtk" in low or "@gamemanager@agtk" in low) and (
  "getplayer" in low or "getobject" in low or "getlayer" in low or "getscene" in low or "getinstance" in low or "getactive" in low or "find" in low or "gettarget" in low)
 if target:
  va=b+v.address
  print("S32_METHOD",hex(va),n)
  if any(x in low for x in ("getplayer","getobjectlist","getobjectby","getplayerobject","getscene@","getobjectall")):
   data=exe.__data__[exe.get_offset_from_rva(v.address):][:125]
   inst=[]
   for i in md.disasm(data,va):
    inst.append(i.mnemonic+" "+i.op_str)
    if len(inst)>=20 or (i.mnemonic.startswith("ret") and len(inst)>2):break
   print("S32_BODY",hex(va)," | ".join(inst))
print("STAGE32_SCENE_ACCESSOR_AUDIT_PASS")
