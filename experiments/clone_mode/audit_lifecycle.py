#!/usr/bin/env python3
"""Stage20 targeted canonical AGTK clone lifecycle exports / x86 layouts."""
from pathlib import Path
import hashlib,pefile,capstone
p=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(p.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
pe=pefile.PE(str(p),fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
b=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
patterns=("getId@ObjectData","getId@Object@agtk","getId@SceneLayer","getLayer","getObjectData@Object@",
          "getTargetObjectByInstanceId","getInstance@GameManager","getInstanceId@Object",
          "execActionDisappear","createForScript@ObjectCommandDisappear",
          "removeObject@SceneLayer","getSceneLayer@Scene",
          "getSceneLayer@Object","addObject@SceneLayer","getPlayObjectData@Object",
          "getPosition@Object","getObjectId@SceneLayer")
for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
 if not e.name:continue
 n=e.name.decode("utf8","replace")
 if not any(x in n for x in patterns):continue
 a=b+e.address
 try:
  raw=pe.__data__[pe.get_offset_from_rva(e.address):][:85]
  lines=[]
  for ins in md.disasm(raw,a):
   lines.append(ins.mnemonic+" "+ins.op_str)
   if len(lines)>=13 or ins.mnemonic.startswith("ret"):break
  print("CLONE20_SYMBOL",hex(a),n," | ".join(lines)[:800])
 except Exception as ex:print("FAIL",n,str(ex))
targets={"Layer_remove":0x58b5c0,"GameManager_getObjectByInstance":0x5e8470,
         "ObjectAction_disappear":0x543b20,"Scene_getLayer":0x59b9a0,
         "Object_getInstance":0x528a80}
for title,va in targets.items():
 raw=pe.__data__[pe.get_offset_from_rva(va-b):][:530]
 ins=list(md.disasm(raw,va))
 print("CLONE20_TARGET",title,hex(va))
 for i in range(0,min(len(ins),130),27):
  print("CLONE20_CODE",title,i," | ".join(f"{hex(x.address)} {x.mnemonic} {x.op_str}" for x in ins[i:i+27])[:3100])
print("CLONE20_PASS")
