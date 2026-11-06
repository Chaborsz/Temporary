#!/usr/bin/env python3
"""Stage26: verify per-instance PlayObjectData::setControllerId and actual F9/F10 mappings."""
import ijson,pefile,hashlib,capstone
from pathlib import Path
e=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(e.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
p=pefile.PE(str(e),fast_load=True); b=p.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for name,va in [
 ("PlayObjectData::setControllerId",0x46c500),
 ("PlayObjectData::getControllerId",0x46c530),
 ("Object::getControllerId",0x528aa0),
 ("Object::getPlayObjectData",0x431a60),
 ("InputManager::getController",0x5fd840)
]:
 raw=p.__data__[p.get_offset_from_rva(va-b):][:280]
 instructions=[]
 for i in md.disasm(raw,va):
  instructions.append(f"{hex(i.address)} {i.mnemonic} {i.op_str}")
  if len(instructions)>=70 or (len(instructions)>=15 and i.mnemonic.startswith("ret")):break
 print("S26_METHOD",name,hex(va),"entry",raw[:12].hex())
 for i in range(0,len(instructions),19):
  print("S26_BODY",name,i," | ".join(instructions[i:i+19]))
with Path("/tmp/clone-control/project_decrypted.json").open("rb") as fh:
 mapping=next(ijson.items(fh,"inputMapping"),None)
values=[]
for cat,v in mapping.items():
 if isinstance(v,list):
  for x in v:
   if isinstance(x,dict):
    pc=x.get("pcInput",-1)
    if isinstance(pc,int) and 16777264<=pc<=16777275:
     values.append({"category":cat,"record":x,"F":"F"+str(pc-16777263)})
print("S26_BOUND_FUNCTION_KEYS",values)
print("S26_F9_MAPPED",any(x["F"]=="F9" for x in values))
print("S26_F10_MAPPED",any(x["F"]=="F10" for x in values))
print("S26_F6_MAPPED",any(x["F"]=="F6" for x in values))
print("STAGE26_PASS")
