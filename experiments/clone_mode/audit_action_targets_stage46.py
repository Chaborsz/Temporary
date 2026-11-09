#!/usr/bin/env python3
"""Stage46: game object actions and real event-trigger conditions by object ID.
Read-only project schema, bounded console output.
"""
import ijson, collections,json
from pathlib import Path
src=Path("/tmp/clone-control/project_decrypted.json")
assert src.stat().st_size==301997021
selected={1,2,25,85,91,195}
with src.open("rb") as f:
 for obj in ijson.items(f,"objectList.item",use_float=False):
  id=obj.get("id")
  if id not in selected:continue
  counter=collections.Counter()
  references=collections.Counter()
  snippets=[]
  named=[]
  switchdefs={}
  for ac in obj.get("actionList",[]):
   for cmd in ac.get("objCommandList",[]):
    t=cmd.get("commandType","-")
    counter[t]+=1
    for typ,val in cmd.items():
     if not isinstance(val,dict):continue
     for k,v in val.items():
      if k in ("variableObjectId","assignVariableObjectId","switchObjectId",
       "objectId","targetObjectId","objectGroup","qualifierId",
       "variableQualifierId","assignVariableQualifierId","switchQualifierId","targetQualifierId"):
       references[(t,typ,k,str(v))]+=1
     if ("script" in typ.lower() or "switchvariable" in typ.lower() or
       "actionexec" in typ.lower()) and len(snippets)<12:
      snippets.append({"action_name":ac.get("name"),"action_id":ac.get("id"),
          "cmd_type":t,"fields":{k:str(v)[:200] for k,v in val.items() if
            any(z in k.lower() for z in ("object","qualifier","variable","script","switch","action","id","assign"))}})
   name=str(ac.get("name",""))
   if any(k in name.lower() for k in ("hit","attack","player","damage","rape","sex","ゲージ","ＨＰ","ダメージ","えっち","拘束","射精","吸収","ダウン","捕","当たり","興奮","性的")) and len(named)<70:
    named.append((ac.get("id"),name))
  linkcounts=collections.Counter()
  linkforeign=collections.Counter()
  linkhits=[]
  for link in obj.get("actionLinkList",[]):
   for cond in link.get("linkConditionList",[]):
    tp=cond.get("type","-")
    linkcounts[tp]+=1
    for k,v in cond.items():
     if not isinstance(v,dict):continue
     for attr,ref in v.items():
      if "objectId" in attr and str(ref) not in ("-1","-2","0"):
       linkforeign[(tp,k,attr,str(ref))]+=1
     if any(q in k.lower() for q in ("objecthit","wall","otherobject","switchvariable","attack","colli")):
      if len(linkhits)<8 and (id in (1,195) or tp!=17):
       linkhits.append({"link_id":link.get("id"),"link_type":link.get("changeConditionType"),
          "name":k,"type":tp,"params":{q:str(w)[:70] for q,w in list(v.items())[:20]}})
  print("S46_OBJECT",id,obj.get("name"),"actions",len(obj.get("actionList",[])),
    "commands",sum(counter.values()),"links",len(obj.get("actionLinkList",[])))
  print("S46_COMMAND_TYPES",id,counter.most_common(26))
  print("S46_LINK_TYPES",id,linkcounts.most_common(20))
  print("S46_REFERENCE_COUNTS",id,[(*key,n) for key,n in references.most_common(35)])
  print("S46_LINK_FOREIGN",id,[(*key,n) for key,n in linkforeign.most_common(25)])
  print("S46_NAMED_ACTIONS",id,json.dumps(named,ensure_ascii=False,default=str)[:6000])
  print("S46_COMMAND_SAMPLES",id,json.dumps(snippets[:12],ensure_ascii=False,default=str)[:8500])
  print("S46_LINK_SAMPLES",id,json.dumps(linkhits[:8],ensure_ascii=False,default=str)[:4600])
print("STAGE46_PROJECT_ACTION_AUDIT_PASS")

# Stage134: separate read-only native event chain audit using the same verified original inputs.
import runpy
runpy.run_path(str(Path(__file__).with_name('audit_stage134_full_chain.py')), run_name='__main__')

# Stage134: native graph from physical contact transitions to resource/movement actions.
runpy.run_path(str(Path(__file__).with_name('audit_stage134_link_graph.py')), run_name='__main__')
