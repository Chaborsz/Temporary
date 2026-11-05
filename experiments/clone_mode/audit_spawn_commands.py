#!/usr/bin/env python3
"""Stage17: find pre-existing player/visual actor spawn commands and native ABI.
Read-only. Never changes game assets.
"""
import collections,json,hashlib
from pathlib import Path
import ijson,pefile,capstone

project=Path("/tmp/clone-mode/project_decrypted.json")
exe=Path("cheats/endurance/input/player.exe")
assert project.stat().st_size==301997021
assert hashlib.sha256(exe.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
hist=collections.Counter()
samples={}
player=[]
sampleObjects=[]
stack=[]
with project.open("rb") as f:
 for path,event,value in ijson.parse(f,use_float=False):
  if event=="start_map":
   stack.append({"p":path,"v":{}})
  elif event in ("number","string","boolean"):
   if stack and path.rsplit(".",1)[0]==stack[-1]["p"]:
    field=path.rsplit(".",1)[-1]
    if len(stack[-1]["v"])<45 and len(str(value))<170:
     stack[-1]["v"][field]=str(value) if event=="number" and not isinstance(value,int) else value
  elif event=="end_map":
   if not stack:continue
   fr=stack.pop()
   if fr["p"].endswith(".objectCreate"):
    entry=fr["v"]
    objid=entry.get("objectId")
    hist[str(objid)]+=1
    k=str(objid)
    if len(samples.get(k,[]))<2:
     context=[{"id":e["v"].get("id"),"name":e["v"].get("name"),"p":e["p"][-130:]}
              for e in stack if e["p"].endswith((".scenePartList.item",".actionList.item")) or e["p"]=="objectList.item"]
     samples.setdefault(k,[]).append({"path":fr["p"][-160:],"settings":entry,"context":context[-4:]})
    if k in ("1","73","207","229","223","225","228","22") and len(player)<85:
     player.append({"id":objid,"settings":entry,"path":fr["p"][-150:]})
   if fr["p"]=="objectList.item" and fr["v"].get("id") in (1,73,207,229,22,223,225,228):
    sampleObjects.append(fr["v"])
print("STAGE17_PROJECT_PASS objectCreate_total",sum(hist.values()),"unique_target_ids",len(hist))
print("PLAYER_SPAWN_TALLY",json.dumps({k:hist[k] for k in ("1","73","207","229","223","225","228","22")}))
for x in player[:25]:print("PLAYER_SPAWN",json.dumps(x,ensure_ascii=False)[:1050])
print("OBJECTS",json.dumps(sampleObjects,ensure_ascii=False)[:3500])
print("TOP_CREATE_IDS",hist.most_common(22))
p=pefile.PE(str(exe),fast_load=True)
p.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
base=p.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
targets={"execForScript":0x53fcf0,"execActionObjectCreate":0x530030,"createForScript":0x4555d0,
         "Object_Create":0x51fe20,"ScriptingCore_executeString":0x42ad20}
for key,va in targets.items():
 raw=p.__data__[p.get_offset_from_rva(va-base):][:2600]
 instructions=[]
 for i in md.disasm(raw,va):
  instructions.append(hex(i.address)+" "+i.mnemonic+" "+i.op_str)
  if len(instructions)>=225 or (i.mnemonic.startswith("ret") and len(instructions)>55):break
 print("NATIVE_LENGTH",key,len(instructions))
 for i in range(0,len(instructions),28):
  print("NATIVE_BLOCK",key,i," | ".join(instructions[i:i+28])[:2250])
doc={"spawn_counts":dict(hist),"spawn_samples":samples,"target_spawns":player,"important_object_meta":sampleObjects}
out=Path("experiments/clone_mode/analysis/stage17-spawn-commands.json")
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(doc,ensure_ascii=False,indent=2,default=str))
