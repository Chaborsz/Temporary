#!/usr/bin/env python3
"""Stage28: static READ ONLY audit of PGMMV player controller routing.
Focus on native object input control; zero gameplay modifications.
"""
import hashlib,pefile,capstone
from pathlib import Path
exe=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(exe.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
p=pefile.PE(str(exe),fast_load=True)
p.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
base=p.OPTIONAL_HEADER.ImageBase
symbols={base+s.address:s.name.decode("utf8","replace") for s in p.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
# list exported Object methods related to per-instance keyboard / control / simulation
for va,name in symbols.items():
 if "@Object@agtk" in name and any(x in name.lower() for x in (
  "input","control","operat","update","direction","move","getobjectdata","getplayer",
  "setposition","updateaction","execaction","getaction")):
  print("S28_OBJECT",hex(va),name[:195])
for va,name in symbols.items():
 if "@PlayObjectData@data@agtk" in name and any(x in name.lower() for x in ("control","operat","input","move","player")):
  print("S28_PLAY_OBJECT",hex(va),name[:190])
for va,name in symbols.items():
 if any(x in name.lower() for x in ("operatable","operated","ignoremoveinput","useinput","noinput")):
  print("S28_OPTION",hex(va),name[:200])
t={
 "Object_getControllerId":0x528aa0,
 "PlayObjectData_getControllerId":0x46c530,
 "PlayObjectData_setControllerId":0x46c500,
 "Object_update":next((a for a,n in symbols.items() if n.startswith("?update@Object@agtk@@")),0),
 "Object_updateInput":next((a for a,n in symbols.items() if "updateInput@Object@agtk" in n),0),
}
for name,va in t.items():
 if not va:print("S28_MISSING",name);continue
 raw=p.__data__[p.get_offset_from_rva(va-base):][:950]
 ins=list(md.disasm(raw,va))[:210]
 print("S28_TARGET",name,hex(va),symbols.get(va,""))
 for at in range(0,len(ins),28):
  print("S28_CODE",name,at," | ".join(f"{hex(i.address)} {i.mnemonic} {i.op_str}" for i in ins[at:at+28])[:3600])
# Find calls to the two getters and the setter and surrounding sites
locations={k:v for k,v in t.items() if v}
calls={v:[] for v in locations.values()}
for section in p.sections:
 if not section.Characteristics&0x20000000:continue
 va=base+section.VirtualAddress
 ins=list(md.disasm(section.get_data(),va))
 for i,s in enumerate(ins):
  if s.mnemonic!="call" or not s.op_str.startswith("0x"):continue
  try:d=int(s.op_str,16)
  except ValueError:continue
  if d not in calls:continue
  if len(calls[d])>=45:continue
  nearby=ins[max(0,i-9):i+7]
  calls[d].append({"at":hex(s.address),"code":" | ".join(f"{hex(x.address)} {x.mnemonic} {x.op_str}" for x in nearby)})
for name,addr in locations.items():
 print("S28_CALLS",name,len(calls[addr]))
 for c in calls[addr][:15]:print("S28_CALL",name,c["at"],c["code"][:1380])
print("STAGE28_AUDIT_PASS")
