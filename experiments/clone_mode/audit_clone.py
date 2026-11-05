#!/usr/bin/env python3
"""Clone-mode stage14: audit existing AGTK object/scene spawning facilities.
READ ONLY; no game modifications. Emits only compact project metadata.
"""
from __future__ import annotations
import collections,hashlib,json,re
from pathlib import Path
import pefile,ijson,capstone

EXE=Path("cheats/endurance/input/player.exe")
PROJECT=Path("/tmp/clone-mode/project_decrypted.json")
EXPECTED="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
out=Path("experiments/clone_mode/analysis")
out.mkdir(parents=True,exist_ok=True)
assert hashlib.sha256(EXE.read_bytes()).hexdigest()==EXPECTED
assert PROJECT.stat().st_size==301997021
pe=pefile.PE(str(EXE),fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
base=pe.OPTIONAL_HEADER.ImageBase
exports=[]
for e in getattr(pe.DIRECTORY_ENTRY_EXPORT,"symbols",[]):
    if not e.name:continue
    n=e.name.decode("utf-8","replace")
    if any(x in n.casefold() for x in ("createobject","addobject","appearobject","spawnobject","generateobject",
                    "objectinstance","createplayer","objectmanager","create@object",
                    "create@scene","objectcreate","generate@","appear@","createobjectdata")):
        exports.append({"va":base+e.address,"name":n})
print("PLAYER_EXE_CANONICAL_PASS",len(exports),"related_exports")
for x in exports[:175]:
    print("ENGINE_SYMBOL",hex(x["va"]),x["name"][:220])
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for item in exports:
    n=item["name"].lower()
    if any(t in n for t in ("createobject","addobject","spawnobject","generateobject","create@object@","create@scene","objectmanager")):
        rva=item["va"]-base
        try:
            code=pe.__data__[pe.get_offset_from_rva(rva):][:110]
            lines=[]
            for i in md.disasm(code,item["va"]):
                lines.append(i.mnemonic+" "+i.op_str)
                if len(lines)>=15 or i.mnemonic in ("ret","retn"):break
            print("ENGINE_CODE",hex(item["va"]),item["name"][:135]," | ".join(lines)[:720])
        except Exception:pass
varsTop=[]
objects=[]
sceneParts=[]
keycounts=collections.Counter()
keyexamples=collections.defaultdict(list)
scene_context={}
stack=[]
LIMIT=150
def j(v):
    if isinstance(v,(str,int,bool)):return v if len(str(v))<=200 else str(v)[:200]
    return str(v)[:150]
def parent_info():
    return [{"path":f["prefix"][-100:],
             "id":f["attrs"].get("id"),"name":str(f["attrs"].get("name",""))[:90]}
            for f in stack
            if "id" in f["attrs"] and "name" in f["attrs"]
            and (f["prefix"].startswith(("sceneList.item","objectList.item")) or f["prefix"].endswith("scenePartList.item"))][-4:]
with PROJECT.open("rb") as file:
    for prefix,event,value in ijson.parse(file,use_float=False):
        if event=="start_map":
            stack.append({"prefix":prefix,"attrs":{}})
        elif event=="map_key":
            key=str(value)
            x=key.casefold()
            if any(z in x for z in ("appear","spawn","generate","createobject","objectcreate","objectgenerate","player","clone","duplicate","copyobject","objectid")):
                keycounts[key]+=1
                if len(keyexamples[key])<2:
                    keyexamples[key].append({"path":prefix[-170:],"context":parent_info()})
        elif event in ("string","number","boolean"):
            if stack and prefix.rsplit(".",1)[0]==stack[-1]["prefix"]:
                key=prefix.rsplit(".",1)[-1]
                if (key in ("id","name","objectId","player","playerId","playerGroup","group","groupBit","objectGroup",
                          "operatable","operated","inputDevice","inputDeviceId","input","defaultActionId",
                          "initialActionId","isPlayer","isOperatable","dispPriority","isPortal",
                          "createObjectId","appearObjectId","objectType","objectTypeId","groupId",
                          "lockPlayer","ignorePlayer","layerIndex","x","y","posX","posY",
                          "folder","type","isFolder")):
                    stack[-1]["attrs"][key]=j(value)
        elif event=="end_map":
            if not stack:continue
            f=stack.pop()
            pref=f["prefix"]
            attrs=f["attrs"]
            if pref in ("objectList.item","objectList.item.children.item","objectList.item.children.item.children.item"):
                if len(objects)<1200:objects.append(attrs)
            if pref.endswith("scenePartList.item") and ("objectId" in attrs or "name" in attrs):
                if len(sceneParts)<800:
                    name=str(attrs.get("name",""))
                    if ("プレイヤー" in name or "主人公" in name or "player" in name.lower() or "clon" in name.lower() or "objectId" in attrs):
                        sceneParts.append({"attrs":attrs,"parent":parent_info()})
            if pref in ("sceneList.item","sceneList.item.children.item"):
                if len(varsTop)<300:varsTop.append(attrs)
result={
 "target":"Clone player via safe AGTK spawn, not memory copy",
 "source_file_sha256":EXPECTED,
 "decoded_project_size":PROJECT.stat().st_size,
 "candidate_engine_exports":exports,
 "all_objects":objects,
 "scene_meta":varsTop,
 "scene_part_sample":sceneParts[:180],
 "spawn_keys": [{"name":k,"count":n,"examples":keyexamples[k]} for k,n in keycounts.most_common(160)]
}
(out/"stage14-project-and-engine.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str))
print("CLONE_STAGE14_PASS objects",len(objects),"sceneParts",len(sceneParts),"keys",len(keycounts))
for v in objects:
    if any(k in str(v).lower() for k in ("プレイヤー","主人公","player","clone","プレイヤー動作","複製")):
        print("PLAYER_CANDIDATE",json.dumps(v,ensure_ascii=False))
for k,n in keycounts.most_common(90):
    print("PROJECT_KEY",k,n,json.dumps(keyexamples[k][:1],ensure_ascii=False)[:300])
for p in sceneParts[:35]:
    print("SCENE_PLAYER_CANDIDATE",json.dumps(p,ensure_ascii=False)[:550])
