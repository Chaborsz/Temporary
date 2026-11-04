#!/usr/bin/env python3
"""Stage 7 — identify whether HUD Endurance is AGTK global var 2047.
Static read-only metadata correlation. Never changes game data.
"""
import argparse,collections,json
from pathlib import Path
import ijson

TARGETS={2047:"Temptation gauge (MAX76)",2003:"Player ejaculation gauge",
         2386:"Ejaculation display mirror",2054:"Excitement state"}
HUD=("endurance","stamina","excit","arous","hp","mp","hud","ゲージ",
     "誘惑","興奮","精液","エスケープ","体力","魔力","表示")
def relevant(s):
    x=str(s).casefold()
    return any(a in x for a in HUD)

def run(project):
    stack=[]
    counts=collections.Counter()
    examples=collections.defaultdict(list)
    scene_hud=[]
    objects=[]
    def context():
        chain=[]
        for frame in stack:
            p=frame["p"]
            if (p=="objectList.item" or p.endswith(".objectList.item") or
                p.endswith(".scenePartList.item") or
                p.startswith("sceneList.item") and (p.count("item")<=2) or
                p=="sceneList.item"):
                v=frame["fields"]
                if "name" in v or "id" in v:
                    chain.append({"path":p[-110:],
                                 "id":v.get("id"),"name":str(v.get("name",""))[:80]})
        return chain[-7:]
    with project.open("rb") as fh:
        for p,e,v in ijson.parse(fh,use_float=False):
            if e=="start_map":
                stack.append({"p":p,"fields":{}})
                continue
            if e in ("number","string","boolean"):
                if stack and p.rsplit(".",1)[0] == stack[-1]["p"]:
                    key=p.rsplit(".",1)[-1]
                    if len(stack[-1]["fields"])<90 and len(str(v))<180:
                        stack[-1]["fields"][key]=str(v) if e=="number" and not isinstance(v,int) else v
                continue
            if e!="end_map" or not stack:continue
            node=stack.pop()
            p=node["p"]
            attrs=node["fields"]
            if p.endswith((".switchVariableChange",".switchVariableChanged",".switchVariableCompare")):
                try: vid=int(attrs.get("variableId",-1))
                except (ValueError,TypeError): continue
                if vid in TARGETS:
                    kind=p.rsplit(".",1)[-1]
                    ctxt=context()
                    owner=next((c for c in reversed(ctxt) if c["name"]),"n/a")
                    if isinstance(owner,dict):owner=owner["name"]
                    count_key=(vid,kind,owner)
                    counts[count_key]+=1
                    if len(examples[count_key])<3:
                        examples[count_key].append({
                          "context":ctxt,"source_path":p[-160:],
                          "operator":attrs.get("variableAssignOperator",attrs.get("compareVariableOperator")),
                          "operand_type":attrs.get("variableAssignValueType",attrs.get("compareValueType")),
                          "value":str(attrs.get("assignValue",attrs.get("compareValue","")))[:60],
                          "source_variable_id":attrs.get("assignVariableId",attrs.get("compareVariableId")),
                          "source_object_id":attrs.get("assignVariableObjectId",attrs.get("compareVariableObjectId")),
                        })
            if (p.endswith(".scenePartList.item") or p=="sceneList.item.scenePartList.item") and relevant(attrs.get("name","")):
                if len(scene_hud)<600:
                    k={s:attrs.get(s) for s in ("id","name","objectId","x","y","posX","posY",
                         "scaleX","scaleY","visible","angle","layerIndex") if s in attrs}
                    k["context"]=context()
                    scene_hud.append(k)
            if (p=="objectList.item" or p=="objectList.item.children.item") and relevant(attrs.get("name","")):
                if len(objects)<150:
                    objects.append({"id":attrs.get("id"),"name":attrs.get("name"),
                                    "context":context()})
    totals=collections.Counter()
    for (vid,kind,owner),n in counts.items():totals[(vid,kind)]+=n
    byid={}
    for vid in TARGETS:
        top=sorted([(n,kind,owner,examples[(i,kind,owner)])
                    for (i,kind,owner),n in counts.items() if i==vid],
                    key=lambda z:-z[0])[:35]
        byid[str(vid)]={
         "total_operations":sum(n for (i,_,_),n in counts.items() if i==vid),
         "operations_by_kind":{kind:n for (i,kind),n in totals.items() if i==vid},
         "top_owners":[{"count":n,"kind":kind,"owner":owner,"examples":sample} 
                       for n,kind,owner,sample in top]
        }
    return {
        "scope":"Endurance gauge beneath HP & MP; HP untouched",
        "project_bytes":project.stat().st_size,
        "target_variable_names":TARGETS,
        "operations":byid,
        "hud_relevant_scene_parts":scene_hud,
        "hud_relevant_object_defs":objects,
        "caveat":"Scene names and variable assignments alone do not validate HUD position or player-only effect.",
    }

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--project",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    opt=a.parse_args()
    result=run(opt.project)
    opt.out.mkdir(parents=True,exist_ok=True)
    (opt.out/"stage7-hud-gauge-ownership.json").write_text(
      json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    print("STAGE7_PASS",result["project_bytes"],"scene_hud_candidates",
          len(result["hud_relevant_scene_parts"]),"object_defs",len(result["hud_relevant_object_defs"]))
    for i,rec in result["operations"].items():
        print("ID",i,result["target_variable_names"][int(i)],
              "ops",rec["total_operations"],"kinds",json.dumps(rec["operations_by_kind"]))
        for x in rec["top_owners"][:8]:
            print("OWNER",i,x["count"],x["kind"],json.dumps(x["owner"],ensure_ascii=False),
                  "sample",json.dumps(x["examples"][:1],ensure_ascii=False,default=str)[:900])
    for row in result["hud_relevant_scene_parts"][:85]:
        print("HUD_SCENE",json.dumps(row,ensure_ascii=False,default=str)[:650])
    for row in result["hud_relevant_object_defs"][:40]:
        print("HUD_OBJECT",json.dumps(row,ensure_ascii=False,default=str)[:450])
if __name__=="__main__":main()
