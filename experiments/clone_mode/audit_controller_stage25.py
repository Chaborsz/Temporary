#!/usr/bin/env python3
"""Stage25: per-instance player controller ID and unused function key evidence."""
import hashlib,pefile,capstone,ijson,json
from pathlib import Path
p=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(p.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
pe=pefile.PE(str(p),fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
b=pe.OPTIONAL_HEADER.ImageBase
names={b+e.address:e.name.decode("utf8","replace") for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
targets={
"Object::getControllerId":0x528aa0,
"PlayObjectData::getControllerId":0x46c530,
"PlayObjectData::getVariableData":0x46bee0,
"PlayVariableData::setValue":0x46ab90,
"InputManager::getController":0x5fd840,
"InputController::getController":0x403540,
"Object::updateInput?":0x52b000,
"ObjectAction::checkInputCondition":0x54d4d0
}
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for label,va in targets.items():
 raw=pe.__data__[pe.get_offset_from_rva(va-b):][:360]
 dis=[]
 for ins in md.disasm(raw,va):
  dis.append(f"{hex(ins.address)} {ins.mnemonic} {ins.op_str}")
  if len(dis)>=100 or (len(dis)>18 and ins.mnemonic.startswith("ret")):break
 print("S25_TARGET",label,hex(va),"SYM",names.get(va,"-"))
 for i in range(0,len(dis),20):
  print("S25_BODY",label,i," | ".join(dis[i:i+20])[:3200])
# all controller or operat accessor names, avoid constructor noise
for va,n in names.items():
 if any(x in n for x in ("getOperatable@","setOperatable@","isOperatable@","getControllerId@","setControllerId@",
  "getInputController@Object@","updateInput@Object@","getPlayerObject@","setInputController@","getMoveKey","getOperationKey")):
  print("S25_EXPORT",hex(va),n[:250])
project=Path("/tmp/clone-control/project_decrypted.json")
with project.open("rb") as f:
 mapping=next(ijson.items(f,"inputMapping"),None)
print("S25_INPUT_MAP_TYPE",str(type(mapping)),len(mapping) if isinstance(mapping,dict) else -1)
if isinstance(mapping,dict):
 print("S25_INPUT_MAP_KEYS",list(mapping))
 for name,value in mapping.items():
  if isinstance(value,list):
   print("S25_INPUT_MAP_LIST",name,"length",len(value),"examples",
    json.dumps(value[:14],ensure_ascii=False,default=str)[:19000])
  else:print("S25_INPUT_MAP_SCALAR",name,json.dumps(value,ensure_ascii=False,default=str)[:700])
print("STAGE25_PASS")
