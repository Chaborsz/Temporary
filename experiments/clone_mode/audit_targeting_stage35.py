#!/usr/bin/env python3
"""Stage35: inspect player targeting and collision/event dispatch. Read-only."""
from pathlib import Path
import hashlib,pefile,capstone,collections,json
P=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(P.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
pe=pefile.PE(str(P),fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
base=pe.OPTIONAL_HEADER.ImageBase
name={base+e.address:e.name.decode("utf-8","replace") for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
search=("getObjectPlayer@Scene","getTargetObject","getObjectInstance@Scene",
        "getObjectAll@Scene","getObjectInstanceByName@Scene",
        "execAction","execCommand","collision","lockObject","targetObject",
        "playerObject","player@","attackHit","hitAttack","touch","contact",
        "getPortal","getTarget","resolve")
match={a:n for a,n in name.items() if any(term.lower() in n.lower() for term in search)}
for a,n in match.items():
 if any(term.lower() in n.lower() for term in ("getObjectPlayer","getTargetObject","getObjectInstance@Scene",
        "getObjectInstanceByName","getTarget","targetObject","collision","hitAttack","attackHit",
        "execActionObject","execActionAttack","execActionApply","contact","touch","lockObject")):
  print("S35_SYMBOL",hex(a),n[:180])
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
targets={
 "Scene_getObjectPlayer":0x597780,
 "Scene_getObjectInstance":0x59be80,
 "Scene_getObjectInstanceByName":0x59bfe0,
 "GameManager_getTargetObjectByInstanceId":0x5e8470,
}
for k,a in targets.items():
 raw=pe.__data__[pe.get_offset_from_rva(a-base):][:520]
 ins=[]
 for x in md.disasm(raw,a):
  ins.append(f"{hex(x.address)} {x.mnemonic} {x.op_str}")
  if len(ins)>=88 or (x.mnemonic.startswith("ret") and len(ins)>24):break
 print("S35_TARGET",k,hex(a),name.get(a,"?"))
 print("S35_BODY",k," | ".join(ins)[:4500])
# direct calls to known player resolver with bounded contextual disassembly;
# count all call refs to key player API (many may be vtable indirect and absent)
calls=collections.defaultdict(list)
for sec in pe.sections:
 if not sec.Characteristics&0x20000000:continue
 inst=list(md.disasm(sec.get_data(),base+sec.VirtualAddress))
 for ix,x in enumerate(inst):
  if x.mnemonic!="call" or not x.op_str.startswith("0x"):continue
  try:t=int(x.op_str,16)
  except ValueError:continue
  if t not in targets.values():continue
  context=" | ".join(f"{hex(y.address)} {y.mnemonic} {y.op_str}" for y in inst[max(ix-14,0):ix+8])
  calls[t].append((x.address,context))
for k,a in targets.items():
 print("S35_XREF_COUNT",k,len(calls[a]))
 for c,ctx in calls[a][:65]:print("S35_XREF",k,hex(c),ctx[:1550])
print("STAGE35_STATIC_TARGETING_PASS",len(match))
