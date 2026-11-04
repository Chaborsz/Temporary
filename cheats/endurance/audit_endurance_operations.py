#!/usr/bin/env python3
"""Stage 6: reconstruct Endurance/excitation variable writes and conditions.
Bounded, read-only stream traversal of AGTK project metadata.
"""
import argparse,collections,json
from pathlib import Path
import ijson

IDS={2003:"player ejaculation gauge",2011:"gauge stored value",
     2047:"temptation gauge",2054:"current excitement",
     2386:"player ejaculation gauge display"}

def main():
    ar=argparse.ArgumentParser()
    ar.add_argument("--project",required=True,type=Path)
    ar.add_argument("--out",required=True,type=Path)
    a=ar.parse_args()
    stack=[]
    counts=collections.Counter()
    samples=collections.defaultdict(list)
    player_action_names=[]
    common_ids=[]
    def where():
        return [{"p":f["p"],"id":f["fields"].get("id"),"name":str(f["fields"].get("name",""))[:75]}
                for f in stack if f["p"].startswith(("objectList.item","sceneList.item")) and
                ("id" in f["fields"] or "name" in f["fields"])][-6:]
    with a.project.open("rb") as f:
        for prefix,event,val in ijson.parse(f,use_float=False):
            if event=="start_map":
                stack.append({"p":prefix,"fields":{}})
                continue
            if event in ("number","boolean","string"):
                if stack and prefix.rsplit(".",1)[0]==stack[-1]["p"]:
                    k=prefix.rsplit(".",1)[-1]
                    if len(stack[-1]["fields"])<85 and len(str(val))<250:
                        stack[-1]["fields"][k]=val
                continue
            if event!="end_map":continue
            item=stack.pop()
            p=item["p"]
            fields=item["fields"]
            if p.endswith(".switchVariableChange"):
                kind="change"; variable=fields.get("variableId")
            elif p.endswith(".switchVariableReset.item"):
                kind="reset"; variable=fields.get("itemId")
            elif p.endswith(".switchVariableChanged"):
                kind="changed_condition"; variable=fields.get("variableId")
            elif p.endswith(".switchVariableCompare"):
                kind="compare"; variable=fields.get("variableId")
            else:
                kind=None
            if kind and variable in IDS:
                key=(int(variable),kind,p)
                counts[key]+=1
                if len(samples[key])<5:
                    sample={k:v for k,v in fields.items() if k not in ("name","memo")}
                    samples[key].append({"path":p,"settings":sample,"context":where()})
            if p.endswith(".objAction") and (
                "興奮" in str(fields.get("name","")) or
                "誘惑" in str(fields.get("name","")) or
                "ゲージ" in str(fields.get("name",""))):
                if len(player_action_names)<90:
                    player_action_names.append({"id":fields.get("id"),"name":str(fields.get("name"))[:100],
                                                "context":where()})
    report={
      "focus":"Endurance/stamina-arousal, exclude HP",
      "candidate_variable_ids":IDS,
      "counts":[{"variable_id":k[0],"kind":k[1],"path":k[2],"occurrences":v}
                for k,v in sorted(counts.items(),key=lambda kv:(kv[0][0],kv[0][1],-kv[1]))],
      "samples":[{"variable_id":k[0],"kind":k[1],"path":k[2],"samples":v}
                 for k,v in samples.items()],
      "relevant_object_actions":player_action_names,
      "warning":"Game-data references prove a variable is used, not yet which runtime HUD field maps to Endurance."
    }
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"stage6-endurance-operations.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STAGE6_DONE",sum(counts.values()),"candidate-operations",len(counts),"categories",len(IDS))
    for k,v in sorted(counts.items(),key=lambda kv:(kv[0][0],kv[0][1],-kv[1])):
        print("VAR_OP",k[0],IDS[k[0]],k[1],"count",v,"path",k[2])
    for k,v in samples.items():
        if k[0] in (2054,2047,2003,2386):
            for sample in v[:2]:
                print("VAR_SAMPLE",k[0],k[1],json.dumps(sample,ensure_ascii=False)[:1700])
    for e in player_action_names[:42]:
        print("ACTION",json.dumps(e,ensure_ascii=False)[:1000])

if __name__=="__main__":
    main()
