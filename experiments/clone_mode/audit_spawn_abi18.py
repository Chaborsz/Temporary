#!/usr/bin/env python3
"""Read-only reconstruction of AGTK execActionObjectCreateForScript ABI."""
from pathlib import Path
import pefile,hashlib,capstone
exe=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(exe.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
pe=pefile.PE(str(exe),fast_load=True)
base=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
methods=[("createForScript",0x4555d0,290),("execForScript",0x53fcf0,1050),
 ("getGameScene",0x5d32d0,200),("nativeCreate",0x51fe20,350),
 ("execActionObjectCreate",0x530030,1100)]
for name,va,nn in methods:
 raw=pe.__data__[pe.get_offset_from_rva(va-base):][:nn]
 ins=list(md.disasm(raw,va))
 print("ABI18_METHOD",name,hex(va),"length",len(ins))
 for index in range(0,len(ins),36):
  print("ABI18_BLOCK",name,index," | ".join(f"{hex(i.address)} {i.mnemonic} {i.op_str}" for i in ins[index:index+36])[:5000])
 print("ABI18_PARAMS",name," | ".join(f"{hex(i.address)} {i.mnemonic} {i.op_str}" for i in ins if "ebp + " in i.op_str)[:2000])
print("ABI18_PASS")
