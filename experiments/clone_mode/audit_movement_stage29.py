#!/usr/bin/env python3
"""Stage29 static audit of AGTK per-object movement direction and controller routing.
No modifications to game EXE or runtime; inspect complete prologues and xrefs.
"""
import pefile,capstone,hashlib
from pathlib import Path
path=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(path.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
pe=pefile.PE(str(path),fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
b=pe.OPTIONAL_HEADER.ImageBase
exps={b+v.address:v.name.decode("utf8","replace") for v in pe.DIRECTORY_ENTRY_EXPORT.symbols if v.name}
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
keys=("getInputDirectionId@Object","getInputDirectionIdOld@Object","getMoveDirection@Object",
"getMoveDirectionBit@Object","getControllerId@Object","getPlayerId@Object",
"objectUpdateBefore@Object","objectUpdateAfter@Object","earlyUpdate@Object",
"getOperationKeyValue@InputController","getInputController@","getInputDirection@",
"getOperate","getNoInput","getInputId","getInputDirectionId@","getControllerId@PlayObjectData",
"Object::update")
targets={a:n for a,n in exps.items() if any(x.lower() in n.lower() for x in keys)}
for a,n in targets.items():
 print("S29_TARGET",hex(a),n)
 data=pe.__data__[pe.get_offset_from_rva(a-b):][:650]
 ins=[]
 for x in md.disasm(data,a):
  ins.append(f"{hex(x.address)} {x.mnemonic} {x.op_str}")
  if len(ins)>=110 or (x.mnemonic.startswith("ret") and len(ins)>8):break
 for i in range(0,min(110,len(ins)),20):
  print("S29_BODY",hex(a),i," | ".join(ins[i:i+20])[:3200])
# Disassemble executable sections once; xrefs for exact method locations
calls={}
for section in pe.sections:
 if not section.Characteristics & 0x20000000:continue
 addr=b+section.VirtualAddress
 ins=list(md.disasm(section.get_data(),addr))
 for k,x in enumerate(ins):
  if x.mnemonic!="call" or not x.op_str.startswith("0x"):continue
  try:dest=int(x.op_str,16)
  except ValueError:continue
  if dest in targets and len(calls.get(dest,[]))<22:
   callsite=" | ".join(f"{hex(y.address)} {y.mnemonic} {y.op_str}" for y in ins[max(0,k-12):k+5])
   calls.setdefault(dest,[]).append((x.address,callsite))
for dest,items in calls.items():
 print("S29_REFERENCES",hex(dest),targets[dest],len(items))
 for addr,context in items[:18]:print("S29_CALL",hex(dest),hex(addr),context[:1800])
print("STAGE29_MOVEMENT_AUDIT_PASS",len(targets))
