#!/usr/bin/env python3
"""Read-only, streaming AGTK reference project/EXE audit."""
import argparse, collections, csv, hashlib, json
from pathlib import Path

HIGH=("clone","duplicate","duplication","decoy","分身","クローン","複製","コピー","影分身","残像")
LOW=("player","spawn","summon","damage","collision","attack","生成","召喚")
KEYS=("objectid","instanceid","actionid","target","qualifier","commandtype","create","spawn","damage","hp","switch","variable")
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""): h.update(block)
    return h.hexdigest()
def short(v,n=120):return str(v).replace("\n"," ")[:n]
def summarize_action(action):
    todo=[(action,0,"")];visited=0;score=0;calls=0;types=collections.Counter();signals=[]
    while todo and visited<12000:
        v,d,path=todo.pop();visited+=1
        if d>10:continue
        if isinstance(v,dict):
            t=v.get("commandType")
            if t is not None:
                calls+=1;types[str(t)]+=1
            for k,item in v.items():
                kl=k.lower()
                if any(x in kl for x in ("image","texture","scripttext","tileset","sound")):continue
                if any(x in kl for x in KEYS) and len(signals)<14 and not isinstance(item,(list,dict)):
                    signals.append({"field":short(path+"."+k,90),"value":short(item,90)})
                todo.append((item,d+1,path+"."+k))
        elif isinstance(v,list):
            for j,item in enumerate(v[:2500]):todo.append((item,d+1,path+"["+str(j)+"]"))
        elif isinstance(v,str):
            s=v.lower()
            if any(x.lower() in s for x in HIGH):
                score+=25 if "name" in path.lower() else 8
                if len(signals)<14:signals.append({"field":short(path,90),"value":short(v,90)})
    return score,calls,types,signals
def analyze_project(path,out):
    import ijson
    rows=[];candidates=[];all_types=collections.Counter();n_actions=0;n_objects=0
    with path.open("rb") as f:
        for o in ijson.items(f,"objectList.item",use_float=False):
            if not isinstance(o,dict):continue
            n_objects+=1
            oid=o.get("id");name=short(o.get("name",""),160)
            actions=o.get("actionList") or []
            if not isinstance(actions,list):actions=[]
            n_actions+=len(actions)
            score=40 if any(x.lower() in name.lower() for x in HIGH) else 0
            selected=[]
            for a in actions:
                if not isinstance(a,dict):continue
                sc,count,types,evidence=summarize_action(a)
                all_types.update(types)
                aname=short(a.get("name",""),130)
                if any(x.lower() in aname.lower() for x in HIGH):sc+=50
                elif any(x.lower() in aname.lower() for x in LOW):sc+=3
                score+=min(sc,100)
                if sc: selected.append({"id":a.get("id"),"name":aname,"score":sc,"commands":count,
                                       "types":dict(types.most_common(10)),"signals":evidence[:9]})
            rows.append({"id":oid,"name":name,"actions":len(actions),"score":score})
            if score:
                candidates.append({"id":oid,"name":name,"actions":len(actions),"score":score,
                                   "objectGroup":o.get("objectGroup"),"operatable":o.get("operatable"),
                                   "relevantActions":sorted(selected,key=lambda x:-x["score"])[:24]})
    candidates.sort(key=lambda x:-x["score"]);rows.sort(key=lambda x:-x["score"])
    with (out/"objects.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["id","name","actions","score"]);w.writeheader();w.writerows(rows)
    (out/"clone_candidates.json").write_text(json.dumps(candidates[:150],indent=2,ensure_ascii=False,default=str),encoding="utf-8")
    return {"sha256":sha(path),"size":path.stat().st_size,"objects":n_objects,"actions":n_actions,
            "candidates":len(candidates),"top":candidates[:40],"commandTypes":all_types.most_common(45)}
def analyze_exe(path,out):
    import pefile
    pe=pefile.PE(str(path))
    imports=[{"dll":e.dll.decode("ascii","replace"),"count":len(e.imports)}
             for e in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[])]
    exports=[]
    for e in getattr(getattr(pe,"DIRECTORY_ENTRY_EXPORT",None),"symbols",[]):
        if not e.name:continue
        n=e.name.decode("utf-8","replace")
        if any(k in n.lower() for k in HIGH+("agtk","object","damage","collision","player","target")):
            exports.append({"name":n[:190],"rva":hex(e.address)})
    data={"sha256":sha(path),"size":path.stat().st_size,"machine":hex(pe.FILE_HEADER.Machine),
          "imageBase":hex(pe.OPTIONAL_HEADER.ImageBase),"entryRva":hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),
          "imports":imports,"matchingExports":exports[:250]}
    (out/"exe_pe.json").write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    return data
def selftest():
    import io,ijson
    b=b'{"objectList":[{"id":1,"name":"clone","actionList":[{"id":2,"name":"copy"}]}]}'
    o=list(ijson.items(io.BytesIO(b),"objectList.item"))
    assert len(o)==1 and o[0]["actionList"][0]["id"]==2
    assert summarize_action(o[0]["actionList"][0])[0]>0
    print("REFERENCE_AUDIT_SELFTEST_PASS")
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--project",type=Path);a.add_argument("--exe",type=Path)
    a.add_argument("--out",type=Path,default=Path("analysis-results/clone-reference"))
    a.add_argument("--self-test",action="store_true")
    x=a.parse_args()
    if x.self_test:
        selftest()
        if not x.project:return
    if not x.project or not x.exe:a.error("both --project and --exe are required")
    if not x.project.is_file() or not x.exe.is_file():a.error("missing inputs")
    x.out.mkdir(parents=True,exist_ok=True)
    p=analyze_project(x.project,x.out);e=analyze_exe(x.exe,x.out)
    (x.out/"summary.json").write_text(json.dumps({"project":p,"exe":e},indent=2,ensure_ascii=False,default=str),encoding="utf-8")
    md=["# Reference game's clone audit","",
        "Read-only; candidate scores are heuristic and do not prove damage isolation.","",
        "Project SHA256: "+p["sha256"],"EXE SHA256: "+e["sha256"],
        "Project objects: "+str(p["objects"]),"Project actions: "+str(p["actions"]),
        "Candidate objects: "+str(p["candidates"]),"EXE machine: "+e["machine"],"",
        "| Object ID | Name | Actions | Score |","|---:|---|---:|---:|"]
    for o in p["top"][:35]:
        md.append("| "+short(o["id"],20)+" | "+o["name"].replace("|","/")+" | "+str(o["actions"])+" | "+str(o["score"])+" |")
    md+=["","To establish event and damage isolation, inspect matching actions and native call paths in Ghidra and Rizin.",
         "Do not mutate working Stage49/64 version.dll based only on candidate scores."]
    (x.out/"summary.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print("REFERENCE_CLONE_AUDIT_PASS objects="+str(p["objects"])+" actions="+str(p["actions"])+" candidates="+str(p["candidates"]))
if __name__=="__main__":main()
