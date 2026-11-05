#!/usr/bin/env python3
"""Stage16 native AGTK creation: exact ABI and setter symbols (static, read-only)."""
from pathlib import Path
import hashlib,pefile,capstone,json,collections
path=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(path.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
p=pefile.PE(str(path),fast_load=True)
p.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
base=p.OPTIONAL_HEADER.ImageBase
symbols={}
for e in p.DIRECTORY_ENTRY_EXPORT.symbols:
 if e.name:symbols[base+e.address]=e.name.decode("utf8","replace")
for va,n in symbols.items():
 if any(x in n for x in ("ObjectCommandObjectCreateData@","execActionObjectCreate@","execActionObjectCreateForScript@","getObjectData@Object@","getSceneLayer@Object@","update@Object@","update@SceneLayer@", "evalString@ScriptingCore@","executeString@ScriptingCore@","getInstance@ScriptingCore@","getInstance@GameManager@","getCreateObjectList@SceneLayer@")):
  print("CLONE16_EXPORT",hex(va),n[:220])
targets={
"Object::_create":0x51fe20,"ObjectAction::execForScript":0x53fcf0,
"Object::execActionObjectCreate":0x530030,
"ObjectCommandObjectCreateData::createForScript":0x4555d0,
"ScriptingCore::executeString":0x42ad20,
"SceneLayer::addObject":0x58b380,
"Object::getSceneLayer":0x4370b0,
"Object::getObjectData":0x429670,
"Object::getPosition":0x527d50,
}
for va,n in symbols.items():
 if "update@Object@agtk" in n or "update@SceneLayer@agtk" in n:
  targets[n]=va
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
calls=collections.defaultdict(list)
for section in p.sections:
 if not(section.Characteristics&0x20000000):continue
 addr=base+section.VirtualAddress
 inst=list(md.disasm(section.get_data(),addr))
 idx={i.address:n for n,i in enumerate(inst)}
 for i,j in enumerate(inst):
  if j.mnemonic!="call" or not j.op_str.startswith("0x"):continue
  try:dst=int(j.op_str,16)
  except ValueError:continue
  if dst in targets.values():
   if len(calls[dst])<9:
    ctx=inst[max(0,i-29):i+3]
    calls[dst].append({"at":hex(j.address),"nearby":[f"{hex(k.address)} {k.mnemonic} {k.op_str}" for k in ctx]})
report={}
for label,addr in targets.items():
 try:
  code=p.__data__[p.get_offset_from_rva(addr-base):][:380]
  ins=[]
  for i in md.disasm(code,addr):
   ins.append(f"{hex(i.address)} {i.mnemonic} {i.op_str}")
   if len(ins)>=85 or (i.mnemonic.startswith("ret") and len(ins)>5):break
  report[label]={"addr":hex(addr),"symbol":symbols.get(addr),"disasm":ins,"direct_calls":calls[addr]}
  print("CLONE16_TARGET",label,hex(addr),"calls",len(calls[addr]),"symbol",str(symbols.get(addr))[:160])
  print("CLONE16_BODY",label," | ".join(ins[:48])[:2600])
  for c in calls[addr][:4]:
   print("CLONE16_CALLER",label,c["at"]," | ".join(c["nearby"][-19:])[:2400])
 except Exception as e:print("CLONE16_FAIL",label,str(e))
out=Path("experiments/clone_mode/analysis/stage16-native-abi.json")
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2,ensure_ascii=False))
print("CLONE_STAGE16_STATIC_PASS",len(report))
