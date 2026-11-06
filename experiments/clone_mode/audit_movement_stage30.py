#!/usr/bin/env python3
"""Stage30: identify authoritative per-object movement/update input path.
Canonical PE32 static analysis, read-only.
"""
import hashlib,pefile,capstone
from pathlib import Path
p=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(p.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
pe=pefile.PE(str(p),fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
b=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
names={b+e.address:e.name.decode("utf8","replace") for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
for va,n in names.items():
 if ("@ObjectMovement@agtk" in n or ("@Object@agtk" in n and any(k in n.lower() for k in ("operat","input","movement","motion","move","direction")))):
  print("S30_SYMBOL",hex(va),n[:220])
methods={}
for a,n in names.items():
 if any(k in n for k in ("update@ObjectMovement","getInputDirection@ObjectMovement",
     "setInputDirection@ObjectMovement","getMoveDirection@Object","getInputDirectionId@Object",
     "updateMove@ObjectMovement","move@ObjectMovement","updateMovement@Object",
     "getObjectMovement@Object")):
  methods[a]=n
for a,n in methods.items():
 raw=pe.__data__[pe.get_offset_from_rva(a-b):][:630]
 ins=[]
 for i in md.disasm(raw,a):
  ins.append(f"{hex(i.address)} {i.mnemonic} {i.op_str}")
  if len(ins)>=105 or (i.mnemonic.startswith("ret") and len(ins)>15):break
 print("S30_METHOD",hex(a),n)
 for i in range(0,len(ins),22):
  print("S30_BODY",hex(a),i," | ".join(ins[i:i+22])[:2800])
print("S30_COMPLETE",len(methods))
