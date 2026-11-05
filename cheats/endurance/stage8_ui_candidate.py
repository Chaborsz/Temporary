#!/usr/bin/env python3
"""Stage 8: direct evidence for 2047/UI object49 and exact safe initial-value patch locus.
Read-only. Outputs no decrypted game project, only concise metadata.
"""
import argparse,collections,json,mmap,re,hashlib
from pathlib import Path
import ijson

TARGET=2047
TARGET_NAME="ちんこ誘惑ゲージ(MAX76)"
def inspect(path):
    with path.open("rb") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
        b=TARGET_NAME.encode("utf-8")
        n=mm.find(b)
        if n<0:raise RuntimeError("Global variable name not found in JSON")
        left=max(0,n-850);right=min(len(mm),n+180)
        fragment=mm[left:right].decode("utf-8","replace")
        # protect project contents: only print metadata near this named global variable.
        fragment=re.sub(r'("memo"\s*:\s*")[^"]{200,}',r'\1...truncated...',fragment)
        return {"name_file_offset":n,"fragment":fragment[:1030],
                "json_size":len(mm)}

def obj49(path):
    found=[]
    with path.open("rb") as f:
        for obj in ijson.items(f,"objectList.item",use_float=False):
            if obj.get("id")==49:
                found.append(obj)
                break
    if len(found)!=1:raise RuntimeError("Object ID49 absent")
    ob=found[0]
    actions=[]
    count=collections.Counter()
    conditions=[]
    def walk(x,p="",action_name="",action_id=None):
        if isinstance(x,dict):
            if x.get("variableId")==TARGET and p.endswith((".switchVariableChanged",".switchVariableChange")):
                r={"location":p[-190:],"type":p.rsplit(".",1)[-1],
                   "action_name":action_name[:85],"action_id":action_id,
                   "operator":x.get("compareVariableOperator",x.get("variableAssignOperator")),
                   "value":str(x.get("compareValue",x.get("assignValue",""))),
                   "source_var":x.get("compareVariableId",x.get("assignVariableId"))}
                count[r["type"]]+=1
                if len(conditions)<110:conditions.append(r)
            if "name" in x and ("objCommandList" in x or "actionList" in p or "commonAction" in p):
                action_name=str(x.get("name",""))
                if isinstance(x.get("id"),int):action_id=x["id"]
            for k,v in x.items():walk(v,p+"."+str(k),action_name,action_id)
        elif isinstance(x,list):
            for it in x:walk(it,p+".item",action_name,action_id)
    walk(ob)
    fields={k:v for k,v in ob.items() if k in ("id","name","folder","group","type","initialActionId","displayDirection","visible")}
    return {"object_fields":fields,"referencing_2047_counts":dict(count),"conditions":conditions,
           "keys":list(ob)[:45]}
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--project",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    args=a.parse_args()
    loc=inspect(args.project)
    ui=obj49(args.project)
    report={"focus":"Endurance UI temptation gauge only; HP excluded",
            "candidate_global_var_id":TARGET,
            "exact_variable_name":TARGET_NAME,
            "patch_locus":loc,"ui_object49":ui,
            "status":"CONFIRMED_2047_UI_ASSOCIATION_NOT_VISUAL_LABEL"}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"stage8-ui-2047-target.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    print("STAGE8_READONLY_PASS offset",loc["name_file_offset"],
          "object",json.dumps(ui["object_fields"],ensure_ascii=False),
          "conditions",json.dumps(ui["referencing_2047_counts"]))
    print("GLOBAL2047_BYTES",repr(loc["fragment"]))
    for row in ui["conditions"][:18]:
        print("UI49_REF",json.dumps(row,ensure_ascii=False,default=str))
if __name__=="__main__":main()
