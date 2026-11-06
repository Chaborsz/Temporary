#!/usr/bin/env python3
"""Stage39: interpret actual Stage38 caller 0x1E7074 and event target paths."""
from pathlib import Path
import pefile,capstone,hashlib,bisect
path=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(path.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
pe=pefile.PE(str(path),fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
base=pe.OPTIONAL_HEADER.ImageBase
export=sorted((base+s.address,s.name.decode("utf8","replace")) for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name)
addrs=[a for a,n in export]
for addr in (0x5e7074,0x5e706f,0x5e8470,0x5e8500,0x5e5ff0,0x5e6070,0x530030,0x54f6d0,0x554250):
 idx=bisect.bisect_right(addrs,addr)-1
 print("STAGE39_NEAREST",hex(addr),hex(export[idx][0]),export[idx][1],"offset",hex(addr-export[idx][0]))
 for x in export[max(idx-2,0):idx+4]:print("STAGE39_NEAR_SYMBOL",hex(x[0]),x[1][:230])
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for a,amount,label in [(0x5e6d50,1850,"caller_region"),(0x5e6f20,1050,"caller_local"),(0x5e8470,350,"instance_resolver"),
                       (0x530030,620,"object_action_create"),
                       (0x54f6d0,480,"attack_touch_condition")]:
  raw=pe.__data__[pe.get_offset_from_rva(a-base):][:amount]
  ins=list(md.disasm(raw,a))
  print("STAGE39_BODY_START",label)
  for i in range(0,len(ins),27):
   print("STAGE39_BODY",label,i," | ".join(f"{hex(x.address)} {x.mnemonic} {x.op_str}" for x in ins[i:i+27])[:3400])
print("STAGE39_STATIC_PASS")
