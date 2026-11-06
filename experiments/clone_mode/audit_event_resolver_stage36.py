#!/usr/bin/env python3
"""Stage36: analyze event/script object resolver callers and instance lookup ABI."""
import pefile,capstone,hashlib,bisect
from pathlib import Path
p=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(p.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
pe=pefile.PE(str(p),fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
B=pe.OPTIONAL_HEADER.ImageBase
syms=sorted((B+e.address,e.name.decode("utf8","replace")) for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name)
addrs=[x[0] for x in syms]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
locations=[0x478a77,0x46ca77,0x597780,0x59be80,0x5e8470,0x478a20,0x46ca00]
for addr in locations:
 ix=bisect.bisect_right(addrs,addr)-1
 print("S36_CONTEXT",hex(addr),"NEAREST",hex(syms[ix][0]),syms[ix][1],"DIST",addr-syms[ix][0])
 for j in range(max(0,ix-3),min(len(syms),ix+7)):
  print("S36_NEIGHBOR",hex(syms[j][0]),syms[j][1][:230])
for base,size,title in [(0x478900,950,"ScriptResolver"),(0x46c900,900,"SceneObjectFetch"),(0x59be80,980,"SceneGetObjectInstance")]:
 raw=pe.__data__[pe.get_offset_from_rva(base-B):][:size]
 inst=list(md.disasm(raw,base))
 print("S36_BEGIN",title)
 for i in range(0,min(len(inst),225),23):
  print("S36_BODY",title,i," | ".join(f"{hex(x.address)} {x.mnemonic} {x.op_str}" for x in inst[i:i+23])[:3200])
print("STAGE36_RESOLVER_PASS")
