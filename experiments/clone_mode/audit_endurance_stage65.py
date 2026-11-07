#!/usr/bin/env python3
"""Endurance Stage65: read-only feasibility of an independent typed clone.
Audits original AGTK project data (not the other game's ID19), plus canonical
binary, with bounded report. No memory edits, patches or game execution.
"""
import collections, csv, hashlib, json, re, argparse
from pathlib import Path
import ijson,pefile,capstone

TOKENS=re.compile(r"clone|clon|copy|duplicate|player|dummy|decoy|body|主人公|分身|プレイヤ|player|ヒロイン|分裂|ダミー",re.I)
NATIVE_TOKENS=("CreateObjectForScript","createObject","getObjectData","getObjectPlayer",
   "getTargetObjectById@ObjectAction","getTargetObjectByGroup@ObjectAction",
   "getTargetObjectListByObjectId","getTargetObjectByInstanceId",
   "getInstanceId@Object","damaged@Object","checkAttackableObject",
   "execActionObjectCreate","execActionSwitchVariableChange")
CRITICAL={2003,2031,2044,2047}
def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for c in iter(lambda:f.read(1<<20),b""):h.update(c)
 return h.hexdigest()
def slim(obj,limit=500):
 return {str(k):v for k,v in list(obj.items())[:limit] if isinstance(v,(str,int,float,bool)) or v is None}
def recursive_objects(items):
    """Yield every object, including classes nested inside folder children."""
    for root in items:
        stack=[root]
        while stack:
            obj=stack.pop()
            if not isinstance(obj,dict):
                continue
            yield obj
            children=obj.get("children",[])
            if isinstance(children,list):
                stack.extend(reversed(children))

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--project",required=True);ap.add_argument("--exe",required=True);ap.add_argument("--output",required=True)
 arg=ap.parse_args();pr=Path(arg.project);exe=Path(arg.exe);out=Path(arg.output);out.mkdir(parents=True,exist_ok=True)
 assert exe.is_file() and pr.is_file()
 assert sha(exe)=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea", "Wrong baseline EXE"
 p=pefile.PE(str(exe));exports={}
 for s in p.DIRECTORY_ENTRY_EXPORT.symbols:
  if s.name:exports[s.name.decode("utf8","replace")]=s.address
 md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
 native=[]
 for n,rva in sorted(exports.items()):
  if not any(t.lower() in n.lower() for t in NATIVE_TOKENS):continue
  raw=p.get_data(rva,64)
  inst=list(md.disasm(raw,p.OPTIONAL_HEADER.ImageBase+rva))
  native.append({"symbol":n[:240],"rva":hex(rva),"entry":raw[:20].hex(),
     "ins":[f"{z.mnemonic} {z.op_str}" for z in inst[:7]]})
 inventory=[];link_types=collections.Counter();ref_ids=collections.Counter();source_targets=collections.Counter()
 player_targets=collections.Counter();direct_global=collections.Counter();target_commands=collections.Counter()
 per_actor=[];spawned=collections.Counter();create_samples=[];script_examples=[];object_shapes={}
 all_actions=0;all_commands=0;enemy_player_ref=collections.Counter();players_name=[];deep_targets={}
 with pr.open("rb") as f:
  for obj in recursive_objects(ijson.items(f,"objectList.item",use_float=False)):
   if not isinstance(obj,dict):continue
   oid=obj.get("id");name=str(obj.get("name",""))[:150]
   acts=obj.get("actionList",[]) or [];links=obj.get("actionLinkList",[]) or []
   if oid in (1,12,19,22,27,30,33,55,71,72,74,84,85,91,92,93,96,195,200):
    picked=[]
    for ac in acts:
     if not isinstance(ac,dict):continue
     matched=[]
     for cmd in ac.get("objCommandList",[]) or []:
      if not isinstance(cmd,dict):continue
      for key in ("switchVariableChange","objectCreate","actionExec","objectMove","objectLock"):
       v=cmd.get(key)
       if not isinstance(v,dict):continue
       relevant=(oid in (22,27,30,195)) or (key=="switchVariableChange" and v.get("variableId") in (2,2003,2031,2038,2044,2047,2042,2022,2057)) or (key in ("objectCreate","actionExec") and v.get("objectId") in (1,19,27,74))
       if relevant:
        matched.append({"type":cmd.get("commandType"),"kind":key,"params":v})
     if matched:
      picked.append({"id":ac.get("id"),"name":ac.get("name"),"commands":matched})
    deep_targets[str(oid)]={"name":name,"action_count":len(acts),
       "selected_action_details":picked,
       "links":links if oid in (1,12,27,33,55,71,72,93,195,200) else []}
   ncommands=sum(len(x.get("objCommandList",[]) or []) for x in acts if isinstance(x,dict))
   all_actions+=len(acts);all_commands+=ncommands
   scalar=slim(obj)
   inventory.append({"id":oid,"name":name,"actions":len(acts),"commands":ncommands,"links":len(links),
                     "object_group":obj.get("objectGroup"),"operatable":obj.get("operatable"),
                     "player_like_name":int(bool(TOKENS.search(name)))})
   if oid==1 or TOKENS.search(name):
    object_shapes[str(oid)]={"id":oid,"name":name,"scalars":scalar,
       "list_lengths":{k:len(v) for k,v in obj.items() if isinstance(v,list)},
       "dict_shapes":{k:list(v)[:35] for k,v in obj.items() if isinstance(v,dict)},
       "actions":[{"id":a.get("id"),"name":str(a.get("name",""))[:100]} for a in acts[:65]]}
   p_refs=collections.Counter()
   for action in acts:
    if not isinstance(action,dict):continue
    for cmd in action.get("objCommandList",[]) or []:
     if not isinstance(cmd,dict):continue
     ct=str(cmd.get("commandType","?"))
     create=cmd.get("objectCreate")
     if isinstance(create,dict):
      dest=create.get("objectId")
      spawned[str(dest)]+=1
      if dest==1 or oid==1 or (dest is not None and str(dest) not in ("1","0")):
       if len(create_samples)<250 and (oid==1 or dest==1):
        create_samples.append({"from_object":oid,"from_action":action.get("id"),
           "name":str(action.get("name",""))[:70],"target_object":dest,
           "action":create.get("actionId"),"child":create.get("childObject"),
           "connect":create.get("connectId")})
     for key,part in cmd.items():
      if not isinstance(part,dict):continue
      for k,v in part.items():
       lk=k.lower()
       if lk in ("objectid","targetobjectid","variableobjectid","switchobjectid",
                 "assignvariableobjectid","actionexecobjectid"):
        ref_ids[str(v)]+=1
        if v==1:
         p_refs[f"{ct}:{key}.{k}"]+=1
         player_targets[f"{ct}:{key}.{k}"]+=1
         if oid!=1:enemy_player_ref[str(oid)]+=1
         if len(script_examples)<110 and oid!=1:
          script_examples.append({"owner":oid,"name":name,"action":action.get("id"),
            "action_name":str(action.get("name",""))[:100],"commandType":ct,
            "field":f"{key}.{k}","target":v,
            "object_qualifier":part.get("variableQualifierId",part.get("switchQualifierId",part.get("qualifierId")))})
       if lk=="variableid" and v in CRITICAL:
        direct_global[str(v)]+=1
        if oid!=1:source_targets[(str(oid),str(v))]+=1
       if lk in ("variableobjectid","switchobjectid") and v in (0,1,-1,-2):
        target_commands[(str(oid),ct,str(key),str(v))]+=1
   for lnk in links:
    if not isinstance(lnk,dict):continue
    for cond in lnk.get("linkConditionList",[]) or []:
     if isinstance(cond,dict):link_types[str(cond.get("type","?"))]+=1
   if p_refs:per_actor.append({"id":oid,"name":name,"player_references":sum(p_refs.values()),
                          "by_path":p_refs.most_common(20),"actions":len(acts)})
 with (out/"original_object_inventory.csv").open("w",encoding="utf-8",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(inventory[0]) if inventory else ["id"]);w.writeheader();w.writerows(inventory)
 object_ids={x["id"] for x in inventory if isinstance(x["id"],int)}
 gaps=[i for i in range(1,max(object_ids)+2) if i not in object_ids]
 summary={
  "baseline":{"exe_sha256":sha(exe),"exe_size":exe.stat().st_size,"json_sha256":sha(pr),"json_size":pr.stat().st_size},
  "objects":len(inventory),"actions":all_actions,"commands":all_commands,
  "players_and_named_candidates":[x for x in inventory if x["id"]==1 or x["player_like_name"]],
  "object_id_19_existing":next((x for x in inventory if x["id"]==19),None),
  "object_id_74_existing":next((x for x in inventory if x["id"]==74),None),
  "object_id_27_existing":next((x for x in inventory if x["id"]==27),None),
  "object_id_gaps_example":gaps[:60],
  "spawn_destinations":spawned.most_common(45),"spawn_player_count":spawned.get("1",0),
  "other_actors_ref_player":len([x for x in per_actor if x["id"]!=1]),
  "player_ref_total":sum(enemy_player_ref.values()),"by_actor":sorted(per_actor,key=lambda x:-x["player_references"])[:65],
  "id1_references":player_targets.most_common(50),"critical_variable_refs":direct_global.most_common(),
  "critical_by_actor":source_targets.most_common(50),
  "object_shapes":object_shapes,"native":native[:220],
  "link_types":link_types.most_common(35),
  "creation_examples":create_samples[:110],"script_examples":script_examples[:110]}
 (out/"STAGE65_DEEP_ACTION_LINKS.json").write_text(json.dumps(deep_targets,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
 (out/"STAGE65_CLASS_FEASIBILITY.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
 print("STAGE65_INPUT_VALID",json.dumps(summary["baseline"],ensure_ascii=False))
 print("STAGE65_INVENTORY objects",len(inventory),"actions",all_actions,"commands",all_commands)
 print("STAGE65_ACTOR_IDS 1",summary["players_and_named_candidates"][:12])
 for xid in (19,27,74):print("STAGE65_ID_COLLISION",xid,summary[f"object_id_{xid}_existing"])
 print("STAGE65_SPAWN_DESTINATIONS",spawned.most_common(15))
 print("STAGE65_OTHER_ACTORS_EXPLICIT_PLAYER_REFERENCE",summary["other_actors_ref_player"],"total",summary["player_ref_total"])
 print("STAGE65_CRITICAL_GLOBAL",direct_global.most_common(),"by_actor",source_targets.most_common(15))
 print("STAGE65_TOP_PLAYER_REFERENCERS",[(q["id"],q["name"],q["player_references"]) for q in summary["by_actor"][:25]])
 print("STAGE65_NATIVE",len(native))
 print("STAGE65_FEASIBILITY_AUDIT_PASS")
if __name__=="__main__":main()
