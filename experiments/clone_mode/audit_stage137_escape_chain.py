#!/usr/bin/env python3
"""FOBS Stage137 - Escape/entrapment HUD causal audit, read-only original Build29.
Never emits game assets or full JSON. All reports bounded.
"""
import ijson, collections, json, re, hashlib
from pathlib import Path
P=Path("/tmp/clone-control/project_decrypted.json")
assert P.stat().st_size==301997021
ESC=2031
NAME=re.compile("脱出|ゲージ|エスケープ|抵抗|拘束|抜け|捕|連打|escape|trapped|gauge|meter|HUD",re.I)
HARD={1,49,72,91,103,158,195,218,219,239,25}
report={"objects":[],"writers":[],"readers":[],"link_conditions":[],"definitions":[]}
writer_by_owner=collections.Counter();read_by_owner=collections.Counter();cond_by_owner=collections.Counter()
def reduced(para):
    return {k:v for k,v in para.items() if k in ("variableId","variableObjectId","variableQualifierId",
      "variableAssignValueType","variableAssignOperator","assignValue","assignVariableId",
      "assignVariableObjectId","assignVariableQualifierId","switchId","switchObjectId","switchQualifierId",
      "objectId","targetObjectId","targettingType","actionId","operationKeyId","commandType",
      "compareVariableId","compareVariableObjectId","compareVariableQualifierId","compareVariableOperator",
      "variableCondition","compareValue","conditionType")}
def refs(v,path="",depth=0):
    if depth>5:return
    if isinstance(v,dict):
        for k,z in v.items():
            k2=path+"."+k
            if isinstance(z,int) and z==ESC and k in ("variableId","assignVariableId","compareVariableId","itemId","id"):
                yield k2
            if isinstance(z,dict):yield from refs(z,k2,depth+1)
            if isinstance(z,list) and len(z)<120:
                for u in z:yield from refs(u,k2,depth+1)
def defsearch(v,path="",depth=0):
    if depth>6:return
    if isinstance(v,dict):
        if v.get("id")==ESC or v.get("variableId")==ESC:
            yield {"path":path,"metadata":{k:str(t)[:100] for k,t in v.items()
                if isinstance(t,(str,int,float,bool)) and k not in ("script","valueJson")}}
        for k,z in v.items():
            if k in ("actionList","actionLinkList","objCommandList"):continue
            if isinstance(z,dict):yield from defsearch(z,path+"."+k,depth+1)
            elif isinstance(z,list):
                for i,u in enumerate(z[:150]):yield from defsearch(u,path+"."+k+f"[{i}]",depth+1)
    elif isinstance(v,list):
        for i,u in enumerate(v[:100]):yield from defsearch(u,path+f"[{i}]",depth+1)
with P.open("rb") as f:
    for o in ijson.items(f,"objectList.item",use_float=False):
        if not isinstance(o,dict):continue
        oid=o.get("id")
        name=str(o.get("name",""))
        acts=o.get("actionList",[]) or []
        links=o.get("actionLinkList",[]) or []
        w=[];read=[];lc=[]
        for a in acts:
            aid=a.get("id");aname=str(a.get("name",""))[:75]
            for ci,c in enumerate(a.get("objCommandList",[]) or []):
                if not isinstance(c,dict):continue
                for block,para in c.items():
                    if not isinstance(para,dict):continue
                    if para.get("variableId")==ESC and c.get("commandType")==31 and block=="switchVariableChange" and para.get("swtch") is False:
                        w.append({"action":aid,"name":aname,"index":ci,"cmdid":c.get("id"),
                                  "block":block,"params":reduced(para)})
                    elif para.get("assignVariableId")==ESC or para.get("compareVariableId")==ESC:
                        read.append({"action":aid,"name":aname,"index":ci,"cmdid":c.get("id"),
                                     "block":block,"params":reduced(para)})
        for l in links:
            for co in l.get("linkConditionList",[]) or []:
                if any(True for _ in refs(co)):
                    lc.append({"link":l.get("id"),"pair":l.get("typeIdPair"),
                               "condition":{"type":co.get("type"),"ignored":co.get("ignored"),
                                  "fields":[{"block":k,"params":reduced(v)} for k,v in co.items()
                                   if isinstance(v,dict)]}})
        if oid in HARD or NAME.search(name) or w or read or lc:
            row={"id":oid,"name":name[:70],"actions":len(acts),"links":len(links),
                 "writes2031":len(w),"reads2031":len(read),"conditions2031":len(lc)}
            report["objects"].append(row)
            writer_by_owner[str(oid)]+=len(w);read_by_owner[str(oid)]+=len(read);cond_by_owner[str(oid)]+=len(lc)
            if w:report["writers"].extend([dict(owner=oid,owner_name=name[:70],**x) for x in w])
            if read:report["readers"].extend([dict(owner=oid,owner_name=name[:70],**x) for x in read])
            if lc:report["link_conditions"].extend([dict(owner=oid,owner_name=name[:70],**x) for x in lc])
        if oid==1:
            report["definitions"]+=list(defsearch(o,"object1"))[:120]
print("STAGE137_ESCAPE_COUNTS",json.dumps({"writers":sum(writer_by_owner.values()),"readers":sum(read_by_owner.values()),
  "conditions":sum(cond_by_owner.values()),"owners":len(writer_by_owner)},ensure_ascii=False))
print("STAGE137_ESCAPE_OWNERS",json.dumps({"writes":writer_by_owner.most_common(30),"reads":read_by_owner.most_common(30),"conditions":cond_by_owner.most_common(30)},ensure_ascii=False))
print("STAGE137_ESCAPE_NAME_MATCHES",json.dumps([x for x in report["objects"] if NAME.search(x["name"])][:85],ensure_ascii=False)[:12000])
print("STAGE137_ESCAPE_DEFS",json.dumps(report["definitions"][:100],ensure_ascii=False)[:10000])
for oid in (1,12,49,91,103,158,195,218,219,239):
    print("STAGE137_ESCAPE_OWNER_WRITES",oid,json.dumps([x for x in report["writers"] if x["owner"]==oid][:18],ensure_ascii=False,default=str)[:9500])
    print("STAGE137_ESCAPE_OWNER_READS",oid,json.dumps([x for x in report["readers"] if x["owner"]==oid][:18],ensure_ascii=False,default=str)[:9500])
    print("STAGE137_ESCAPE_OWNER_LINKS",oid,json.dumps([x for x in report["link_conditions"] if x["owner"]==oid][:15],ensure_ascii=False,default=str)[:9500])
out=Path("/tmp/clone-control/STAGE137_ESCAPE_CHAIN.json")
out.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str))
print("STAGE137_ESCAPE_AUDIT_PASS",out.stat().st_size)
