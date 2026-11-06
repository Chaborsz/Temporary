#!/usr/bin/env python3
"""Stage49 narrow PE32 audit: native event routing paths not covered by Stage48."""
from pathlib import Path
import pefile,capstone,hashlib
p=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(p.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
pe=pefile.PE(str(p));base=pe.OPTIONAL_HEADER.ImageBase
export={}
for s in pe.DIRECTORY_ENTRY_EXPORT.symbols:
 if s.name:export[base+s.address]=s.name.decode("utf8","replace")
tokens=("getTargetObjectById@ObjectAction","getTargetObjectByGroup@ObjectAction",
"checkLinkConditionObject","checkLinkConditionHit","checkLinkConditionAttack",
"changeAction@Object","setAction@Object","startAction@Object",
"addCollisionHitAttack@Object","addCollisionAttackHit@Object",
"getCollisionHitAttackList@Object","getCollisionAttackHitList@Object",
"setCollisionHitAttackList@Object","getDamagedList@Object",
"getTargetObjectLocked@ObjectAction","objectHit@Object")
selected=[(a,n) for a,n in export.items() if any(z.lower() in n.lower() for z in tokens)]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=False
for a,n in sorted(selected):
 raw=pe.__data__[pe.get_offset_from_rva(a-base):][:96]
 ins=[]
 for x in md.disasm(raw,a):
  ins.append("%s %s"%(x.mnemonic,x.op_str))
  if len(ins)>=18 or x.mnemonic.startswith("ret"):break
 print("S49_NATIVE",hex(a),"rva",hex(a-base),n,"BYTES",raw[:20].hex(),"INS"," | ".join(ins))
print("STAGE49_STATIC_NATIVE_AUDIT_PASS",len(selected))
