#!/usr/bin/env python3
"""Stage45 read-only narrow report: exported actor IDs and their event/command structure.
Never dumps complete copyrighted project assets.
"""
import ijson,collections,json
from pathlib import Path
project=Path("/tmp/clone-control/project_decrypted.json")
assert project.stat().st_size==301997021
wanted={1,2,25,85,91,195}
def brief(v,depth=0):
 if depth>=4:return str(v)[:100] if not isinstance(v,(dict,list)) else ("{...}" if isinstance(v,dict) else "[...]")
 if isinstance(v,dict):
  out={}
  for key,value in list(v.items())[:32]:
   if any(x in key.lower() for x in ("image","texture","tileset","textureid","atlas","file","resource")):continue
   out[key]=brief(value,depth+1)
  return out
 if isinstance(v,list):return [brief(x,depth+1) for x in v[:4]]
 if isinstance(v,str):return v[:220]
 return v
def show_command(a,action):
 result={"action_id":action.get("id"),"name":action.get("name"),"keys":list(action)[:32]}
 for k,v in action.items():
  if isinstance(v,list) and "command" in k.lower():
   result[k+"_count"]=len(v)
   result[k+"_head"]=[brief(obj) for obj in v[:3]]
  elif isinstance(v,dict) and any(x in k.lower() for x in ("command","variable","switch")):
   result[k]=brief(v)
 return result
with project.open("rb") as f:
 selected=[]
 for entry in ijson.items(f,"objectList.item",use_float=False):
  oid=entry.get("id")
  if oid not in wanted:continue
  selected.append(oid)
  print("S45_OBJECT",json.dumps({"id":oid,"name":entry.get("name"),"keys":list(entry)[:70],
      "operatable":entry.get("operatable"),"objectGroup":entry.get("objectGroup"),
      "actionListLength":len(entry.get("actionList",[]))},ensure_ascii=False,default=str))
  for key,value in entry.items():
   if isinstance(value,list):
    print("S45_LIST",oid,key,"count",len(value),"first_type",type(value[0]).__name__ if value else "-")
   elif isinstance(value,dict) and any(x in key.lower() for x in ("action","link","condition","variable","switch","player","collision")):
    print("S45_MAP",oid,key,brief(value))
  for a in entry.get("actionList",[])[:7]:
   print("S45_ACTION",oid,json.dumps(show_command(oid,a),ensure_ascii=False,default=str)[:6000])
  for key,v in entry.items():
   if "actionLink" in key and isinstance(v,list):
    for x in v[:6]:print("S45_LINK",oid,json.dumps(brief(x),ensure_ascii=False,default=str)[:2400])
 print("STAGE45_GAME_OBJECT_IDS_FOUND",selected)
