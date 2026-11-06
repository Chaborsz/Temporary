#!/usr/bin/env python3
"""Stage40: map actual actor damage/action application API. Read-only canonical x86 scan."""
from pathlib import Path
import pefile,hashlib,capstone,collections
P=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(P.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
pe=pefile.PE(str(P),fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
B=pe.OPTIONAL_HEADER.ImageBase
names={B+x.address:x.name.decode("utf8","replace") for x in pe.DIRECTORY_ENTRY_EXPORT.symbols if x.name}
criteria=("damage","hitpoint","addhp","sethp","gethp","attack","hitobject","attacked","collision",
          "changeaction","changeobject","execut","changevariable","switchvariable",
          "execaction","hitattack","hitby","receive","apply","event","targetobject","getobjectplayer")
found=[]
for va,n in names.items():
 low=n.lower()
 if any(k in low for k in criteria) and (
   "@Object@agtk" in n or "@ObjectAction@agtk" in n or
   "@PlayObjectData@data@agtk" in n or "@GameManager@@" in n or
   "@Scene@agtk" in n or "@ObjectCollision@agtk" in n):
  found.append((va,n))
print("S40_TOTAL_METHODS",len(found))
for a,n in found:
 print("S40_SYMBOL",hex(a),n[:260])
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
key=( "addHp@PlayObjectData","setHp@PlayObjectData",
      "getHp@PlayObjectData","addDamage@Object","damage@Object",
      "damaged@Object","getDamage@Object","execActionObjectChange@Object",
      "execActionObjectChange@ObjectAction", "execActionObjectDestroy@Object",
      "execActionObjectPushPull@Object","checkAttackableObject@Object",
      "execActionObjectChange@Object","getTargetObjectListByObjectId@GameManager",
      "getTargetObjectByInstanceId@GameManager","getObjectPlayer@Scene")
targets={a:n for a,n in found if any(k in n for k in key)}
for a,n in targets.items():
 raw=pe.__data__[pe.get_offset_from_rva(a-B):][:110]
 dis=[]
 for i in md.disasm(raw,a):
  dis.append(i.mnemonic+" "+i.op_str)
  if len(dis)>=15 or i.mnemonic.startswith("ret"):break
 print("S40_TARGET",hex(a),n,"PROLOGUE",raw[:14].hex(),"INS"," | ".join(dis))
print("STAGE40_ATTACK_METHOD_AUDIT_PASS")
