#!/usr/bin/env python3
"""Stage 5: streaming project data correlation for Endurance (NOT HP).
Outputs only bounded object/variable metadata, no copyrighted game dialog text.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import ijson

TARGET_ID=2054
NAME_TERMS=("興奮","精力","耐久","スタミナ","快感","欲情",
            "arousal","endurance","stamina","excitation","lust",
            "ゲージ","射精","オナニー")
def matches(s):
    s=str(s).casefold()
    return any(t.casefold() in s for t in NAME_TERMS)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    md=hashlib.sha256()
    with a.project.open("rb") as f:
        for ch in iter(lambda:f.read(1024*1024),b""):md.update(ch)
    stack=[]
    scalar_events=0
    global_vars=[]
    object_vars=[]
    variable_ref_count=collections.Counter()
    ref_samples=[]
    numeric_id_count=0
    gauges=[]
    seen=collections.Counter()
    def obj_context():
        data=[]
        for x in stack:
            if x["prefix"].startswith(("objectList.item","variableList.item","sceneList.item")) and ("id" in x or "name" in x):
                data.append({"path":x["prefix"],"id":x.get("id"),"name":str(x.get("name",""))[:95]})
        return data[-6:]
    with a.project.open("rb") as f:
        for prefix,event,value in ijson.parse(f,use_float=False):
            if event=="start_map":
                stack.append({"prefix":prefix})
            elif event=="end_map":
                if not stack: raise RuntimeError("unbalanced maps")
                frame=stack.pop()
                if frame["prefix"]=="variableList.item":
                    seen["global_vars_total"]+=1
                    if matches(frame.get("name","")) or frame.get("id")==TARGET_ID:
                        global_vars.append({"id":frame.get("id"),"name":frame.get("name"),
                                            "initialValue":frame.get("initialValue"),
                                            "memo":str(frame.get("memo",""))[:200]})
                elif frame["prefix"].endswith(".variableList.item") and "objectList" in frame["prefix"]:
                    seen["object_vars_total"]+=1
                    if matches(frame.get("name","")) or frame.get("id")==TARGET_ID:
                        object_vars.append({"id":frame.get("id"),"name":frame.get("name"),
                                            "initialValue":frame.get("initialValue"),"context":obj_context()})
                elif frame["prefix"].startswith(("imageList.item","imageList.item.children.item")):
                    if matches(frame.get("name","")):
                        if len(gauges)<60:
                            gauges.append({"id":frame.get("id"),"name":frame.get("name"),"path":frame["prefix"]})
            elif event in ("number","string","boolean","null"):
                scalar_events+=1
                if stack:
                    leaf=prefix.rsplit(".",1)[-1]
                    frame=stack[-1]
                    if prefix==frame["prefix"]+"."+leaf and leaf in ("id","name","initialValue","memo"):
                        frame[leaf]=value
                if event=="number":
                    if value==TARGET_ID:
                        numeric_id_count+=1
                        variable_ref_count[prefix]+=1
                        if len(ref_samples)<85:
                            ref_samples.append({"path":prefix,"context":obj_context()})
    report={
      "project":"Forest of the Blue Skin AGTK","focus":"Endurance=stamina/arousal under HP/MP, exclude HP",
      "sha256":md.hexdigest(),"size":a.project.stat().st_size,
      "global_variables_checked":seen["global_vars_total"],
      "object_variables_checked":seen["object_vars_total"],
      "global_named_candidates":global_vars[:160],"object_named_candidates":object_vars[:160],
      "gauge_image_candidates":gauges,
      "target_global_variable":{"id":TARGET_ID,"expected_name":"現在の興奮度",
           "confirmed":any(x.get("id")==TARGET_ID and x.get("name")=="現在の興奮度" for x in global_vars)},
      "numeric_2054_occurrences":numeric_id_count,
      "numeric_2054_reference_paths":dict(variable_ref_count.most_common(80)),
      "numeric_2054_context_samples":ref_samples,
      "interpretation":"Named excitation variable is real project metadata; do not yet equate it with HUD Endurance without matching gauge binding.",
      "next":"Link variable 2054 usage in action commands and HUD object to actual Endurance bar mechanics."
    }
    (a.out/"stage5-endurance-variable.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STAGE5_DONE source_bytes",report["size"],
          "sha256",report["sha256"],
          "globals",seen["global_vars_total"],
          "object_vars",seen["object_vars_total"],
          "numeric_2054",numeric_id_count)
    print("ENDURANCE_VARIABLE_2054",json.dumps(report["target_global_variable"],ensure_ascii=False))
    for x in global_vars[:60]: print("GLOBAL_VAR",json.dumps(x,ensure_ascii=False))
    for x in object_vars[:35]: print("OBJECT_VAR",json.dumps(x,ensure_ascii=False))
    for x in gauges[:40]: print("GAUGE_IMAGE",json.dumps(x,ensure_ascii=False))
    for path,cnt in variable_ref_count.most_common(35):print("REFERENCE_2054",cnt,path)
    for x in ref_samples[:25]:print("REFERENCE_CONTEXT_2054",json.dumps(x,ensure_ascii=False))

if __name__=="__main__":main()
