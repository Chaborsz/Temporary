#!/usr/bin/env python3
"""Stage19 clone runtime accessors and native spawn return, no patch."""
import collections,hashlib,pefile,capstone,ijson,json
from pathlib import Path
exe=Path("cheats/endurance/input/player.exe");project=Path("/tmp/clone-mode/project_decrypted.json")
assert hashlib.sha256(exe.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
p=pefile.PE(str(exe),fast_load=True)
p.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
b=p.OPTIONAL_HEADER.ImageBase
names={}
for e in p.DIRECTORY_ENTRY_EXPORT.symbols:
 if e.name:names[b+e.address]=e.name.decode("utf8","replace")
patterns=("getLayerId@SceneLayer","getLayerIndex@SceneLayer","getId@ObjectData",
 "getObjectId@Object","getObjectId@SceneLayer","getObjectByInstanceId",
 "getInstanceId@Object","getInstanceId@SceneLayer","getObjectById",
 "getPlayerObject","getObjectList@SceneLayer","removeObject@SceneLayer",
 "removeObject@Scene","disappear@Object","execActionDisappear@Object",
 "destroy@Object","setOperatable","setInputDevice","setInputDirection","getCurrentScene@","getSceneLayer@","execActionObjectCreateForScript")
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for va,n in names.items():
 if any(t in n for t in patterns):
  try:
   raw=p.__data__[p.get_offset_from_rva(va-b):][:130]
   dis=[]
   for i in md.disasm(raw,va):
    dis.append(i.mnemonic+" "+i.op_str)
    if len(dis)>=13 or i.mnemonic.startswith("ret"):break
   print("CLONE19_SYMBOL",hex(va),n," | ".join(dis)[:600])
  except Exception:pass
for name,va,nbytes in (("spawn_tail",0x5400e0,1050),("execForScript_tail",0x53ffe0,560),
                       ("object_execCreate_tail",0x530500,700)):
  raw=p.__data__[p.get_offset_from_rva(va-b):][:nbytes]
  ins=list(md.disasm(raw,va))
  print("CLONE19_CODE_BEGIN",name)
  for i in range(0,min(len(ins),125),25):
   print("CLONE19_BLOCK",name,i," | ".join(f"{hex(v.address)} {v.mnemonic} {v.op_str}" for v in ins[i:i+25])[:3100])
layers=collections.Counter();scene_counts=collections.Counter();examples=[]
stack=[]
with project.open("rb") as f:
 for path,event,value in ijson.parse(f,use_float=False):
  if event=="start_map":stack.append({"p":path,"v":{}})
  elif event in ("number","string","boolean"):
   if stack and path.rsplit(".",1)[0]==stack[-1]["p"]:
    name=path.rsplit(".",1)[-1]
    if name in ("id","name","objectId","layerIndex","layerId","x","y","initialActionId"):
     stack[-1]["v"][name]=str(value) if event=="number" and not isinstance(value,int) else value
  elif event=="end_map" and stack:
   fr=stack.pop()
   if fr["p"].endswith(".scenePartList.item") and fr["v"].get("objectId")==1:
    l=fr["v"].get("layerIndex")
    layers[str(l)]+=1
    sc=next((f["v"].get("name","") for f in reversed(stack) if f["p"].startswith("sceneList.item") and "name" in f["v"]),"?")
    scene_counts[str(sc)]+=1
    if len(examples)<20:examples.append({"layerIndex":l,"scene":sc,"part":fr["v"]})
print("CLONE19_PLAYER_LAYER_COUNTS",json.dumps(dict(layers)))
print("CLONE19_PLAYER_SCENE_SAMPLE",json.dumps(examples,ensure_ascii=False))
print("CLONE19_PLAYER_SCENES",len(scene_counts),"parts",sum(layers.values()))
print("CLONE19_PASS")
