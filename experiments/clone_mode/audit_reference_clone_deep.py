#!/usr/bin/env python3
"""Targeted read-only evidence on PGMM clone action ID 27 vs player ID 1."""
import argparse,collections,ijson,json,re
from pathlib import Path

KEYWORD=re.compile("分身|clone|duplicate|copy|召喚|身代|デコイ|影分身",re.I)
def brief(v, depth=0):
 if isinstance(v,str):return v[:180]
 if isinstance(v,dict):
  return {str(k):brief(val,depth+1) for k,val in list(v.items())[:50]
          if depth<3 and not any(z in str(k).lower() for z in ("image","texture","tileset","bitmap","atlas","sound","scripttext"))}
 if isinstance(v,list):return [brief(x,depth+1) for x in v[:8]] if depth<3 else ["..."]
 return v
def fields(cmd):
 d={"type":cmd.get("commandType")}
 for k,v in cmd.items():
  if k=="commandType":continue
  if isinstance(v,dict):d[k]=brief(v)
  elif k in ("id","name"):d[k]=brief(v)
 return d
def main():
 a=argparse.ArgumentParser();a.add_argument("--project",required=True);a.add_argument("--out",required=True);x=a.parse_args()
 out=Path(x.out);out.mkdir(parents=True,exist_ok=True)
 objs=[];all_actions=[];spawns=[];refs=collections.Counter()
 with open(x.project,"rb") as f:
  for obj in ijson.items(f,"objectList.item",use_float=False):
   if not isinstance(obj,dict):continue
   oid=obj.get("id");actions=obj.get("actionList",[]) or []
   objs.append({"id":oid,"name":obj.get("name"),"actions":len(actions),"group":obj.get("objectGroup"),"operatable":obj.get("operatable")})
   for ac in actions:
    if not isinstance(ac,dict):continue
    aid=ac.get("id"); name=ac.get("name",""); commands=ac.get("objCommandList",[]) or []
    matched=bool(KEYWORD.search(str(name)))
    for i,cmd in enumerate(commands):
     if not isinstance(cmd,dict):continue
     if cmd.get("commandType")==2 and isinstance(cmd.get("objectCreate"),dict):
      target=cmd["objectCreate"].get("objectId")
      if target in (1,19,27,72,74) or matched:
       spawns.append({"source_id":oid,"source_name":obj.get("name"),"action_id":aid,"action_name":name,"command_index":i,
         "target_id":target,"target_action":cmd["objectCreate"].get("actionId"),"args":brief(cmd["objectCreate"])})
     if matched or oid in (1,19,27,72,74):
      for k,v in cmd.items():
       if isinstance(v,dict):
        for vk,vv in v.items():
         if vk in ("variableObjectId","switchObjectId","variableQualifierId","switchQualifierId","targetObjectId","objectId"):
          refs[(str(oid),str(aid),str(vk),str(vv))]+=1
    if oid in (1,19,27,72,74) and (matched or oid in (19,72,74) or (oid==27 and aid in (40,41,44,45,48,54,55,59,60,61,62,63,70,71,72,116,117,123,124,130)) or (oid==1 and aid in (3,4,117,127,128,162,169,170,328,330,331,332,334,339))):
     all_actions.append({"object_id":oid,"id":aid,"name":str(name)[:160],"commands_total":len(commands),
      "commands":[fields(z) for z in commands[:18] if isinstance(z,dict)]})
   if oid in (1,19,27,72,74):
    lk=obj.get("actionLinkList",[]) or []
    links=[brief(lk[i]) for i in range(min(len(lk),5))]
    action_ids={z["id"] for z in all_actions if z["object_id"]==oid}
    for link in lk:
     if isinstance(link,dict) and any(link.get(k) in action_ids for k in ("actionId","nextActionId","prevActionId","fromActionId","toActionId")) and len(links)<30:
      links.append(brief(link))
    (out/("object_"+str(oid)+"_summary.json")).write_text(json.dumps({
     "id":oid,"name":obj.get("name"),"keys":list(obj)[:80],
     "scalars":{k:brief(v) for k,v in obj.items() if not isinstance(v,(dict,list))},
     "list_lengths":{k:len(v) for k,v in obj.items() if isinstance(v,list)},
     "action_names":[{"id":z.get("id"),"name":z.get("name")} for z in actions if KEYWORD.search(str(z.get("name","")))][:120],
     "links_head":links},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
 objs.sort(key=lambda x:(int(x["id"]) if isinstance(x["id"],int) else 999999))
 payload={"objects":objs,"selected_actions":all_actions,"clone_or_player_object_creates":spawns[:450],
  "reference_counts":[{"key":list(k),"count":n} for k,n in refs.most_common(140)]}
 (out/"DEEP_OBJECTS_AND_ACTIONS.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
 print("=== OBJECTS (id and name) ===")
 for x in objs:print("OBJ",x["id"],str(x["name"])[:95],"group",x["group"],"actions",x["actions"])
 print("=== PLAYER OBJECT 1: CLONE ACTIONS ===")
 for z in all_actions:
  if z["object_id"]==1:
   print("PLAYER_ACTION",z["id"],repr(z["name"]),"commands",z["commands_total"])
   if z["id"] in (3,4,117,128,162,169,170,328,330,331,332):
    for cmd in z["commands"][:12]:print("  PLAYER_COMMAND",json.dumps(cmd,ensure_ascii=False,default=str)[:1300])
 print("=== OBJECT 27: CLONE/PROJECTILE ACTIONS ===")
 for z in all_actions:
  if z["object_id"]==27:
   print("OBJECT27_ACTION",z["id"],repr(z["name"]),"commands",z["commands_total"])
   if z["id"] in (40,62,63,70):
    for cmd in z["commands"][:12]:print("  OBJECT27_COMMAND",json.dumps(cmd,ensure_ascii=False,default=str)[:1200])
 print("=== CLONE OBJECT ID 19 / 74 / CHAIN ID 72 ===")
 for z in all_actions:
  if z["object_id"] in (19,72,74):
   print("CLONE_ENTITY_ACTION",z["object_id"],z["id"],repr(z["name"]),"commands",z["commands_total"])
   if z["id"] in (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,22,25,30,33,35,77,78,81,83,85,92,93) or KEYWORD.search(z["name"]):
    for cmd in z["commands"][:8]:print("  CLONE_ENTITY_COMMAND",json.dumps(cmd,ensure_ascii=False,default=str)[:1050])
 print("=== OBJECT 27 ACTION CHAIN EXTRA ===")
 for z in all_actions:
  if z["object_id"]==27 and z["id"] in (41,44,45,48,54,55,59,60,61,71,72,123,124,130):
   print("MIRROR_ACTION",z["id"],repr(z["name"]),"commands",z["commands_total"])
   for cmd in z["commands"][:8]:print("  MIRROR_COMMAND",json.dumps(cmd,ensure_ascii=False,default=str)[:850])
 print("=== OBJECT CREATES INTO PLAYER 1 OR OBJECT 27 ===")
 for z in ([x for x in spawns if x["target_id"] in (19,72,74)][:90] + [x for x in spawns if x["source_id"] in (1,19,27,72,74)][:55]):print("CREATE",str(z["source_id"]),str(z["action_id"]),repr(z["action_name"])[:90],"->",str(z["target_id"]),str(z["target_action"]),json.dumps(z["args"],ensure_ascii=False,default=str)[:800])
 print("DEEP_REFERENCE_EVIDENCE_PASS actions",len(all_actions),"creates",len(spawns))
if __name__=="__main__":main()
