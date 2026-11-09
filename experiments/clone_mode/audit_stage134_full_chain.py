#!/usr/bin/env python3
"""FOBS Stage134 read-only original Build29 event/selector audit.
Runs on the existing project input inside clone-stage45-project workflow.
Only emits compact metadata, NEVER game assets or full project JSON.
"""
import collections, hashlib, json, struct
from pathlib import Path
import ijson

ROOT=Path("/tmp/clone-control")
P=ROOT/"project_decrypted.json"
E=Path("cheats/endurance/input/player.exe")
EXP_P="2a19596ffc6e54c4651780ad9ee0ab37dc98d4b6a0a979d63ec2b32523e1af89"
EXP_E="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):h.update(block)
    return h.hexdigest()
assert P.stat().st_size==301997021 and sha(P)==EXP_P, "ORIGINAL_PROJECT_MISMATCH"
assert E.stat().st_size==8757760 and sha(E)==EXP_E, "ORIGINAL_EXE_MISMATCH"
print("STAGE134_CANONICAL_SOURCES_PASS",P.stat().st_size,E.stat().st_size)
WATCH={1,25,72,85,91,103,107,158,195,218,219,239,49}
CRITICAL={2,9,10,23,2001,2003,2031,2042,2044,2047,2054,2103}
SWITCHES={2021,2023,2041,2036}
doc={"sources":{"exe_sha256":EXP_E,"project_sha256":EXP_P},"actors":{},"project_counts":{}}
allObj=0
allActions=0
allCommands=0
allLinks=0
foreign=collections.Counter()
def shape(cmd):
    fields={}
    for block,para in cmd.items():
        if not isinstance(para,dict):continue
        relevant={k:v for k,v in para.items() if k in (
          "objectId","targetObjectId","targetQualifierId","variableObjectId",
          "variableQualifierId","variableId","switchId","switchObjectId",
          "switchQualifierId","assignVariableObjectId","assignVariableId",
          "variableAssignOperator","variableAssignValueType","assignValue",
          "actionId","actionExecObjectId","swtch","objectType","qualifierId",
          "targettingType","moveType","changeConditionType")}
        if relevant:fields[block]=relevant
    return fields
def classcmd(cmd):
    out=[]
    for blk,p in cmd.items():
        if not isinstance(p,dict):continue
        vd=p.get("variableId")
        sid=p.get("switchId")
        if vd in CRITICAL and cmd.get("commandType")==31 and blk=="switchVariableChange" and p.get("swtch") is False:
            out.append(f"WRITE_{vd}_S{p.get('variableObjectId')}_Q{p.get('variableQualifierId')}")
        if sid in SWITCHES and cmd.get("commandType")==31 and blk=="switchVariableChange" and p.get("swtch") is True:
            out.append(f"SWITCH_{sid}_S{p.get('switchObjectId')}")
        if p.get("assignVariableObjectId")==1:out.append("READ_RHS_ID1")
        if p.get("assignVariableObjectId")==0 and p.get("assignVariableId") in CRITICAL:out.append("READ_RHS_GLOBAL")
        if blk=="objectMove" and p.get("targetObjectId")==1:out.append("MOVE_ID1")
        if blk=="actionExec" and p.get("objectId")==1:out.append("EXEC_ID1")
        if blk=="objectLock" and p.get("objectId")==1:out.append("LOCK_ID1")
        if p.get("targetObjectId")==1 and blk!="objectMove":out.append("TARGET_ID1_"+blk)
        if p.get("variableObjectId")==1 and vd not in CRITICAL:out.append("OTHER_VAR_ID1")
        if p.get("switchObjectId")==1 and sid not in SWITCHES:out.append("OTHER_SWITCH_ID1")
    return out
def briefly(link):
    out={}
    for k,v in link.items():
        if isinstance(v,(int,float,bool,str)):
            out[k]=v if not isinstance(v,str) else v[:100]
        elif isinstance(v,list):
            if "Condition" in k or "condition" in k:
                out[k]=[{q:({p:z for p,z in val.items() if isinstance(z,(str,int,bool,float))} if isinstance(val,dict) else val) for q,val in c.items()} if isinstance(c,dict) else str(c)[:80] for c in v[:2]]
            else:out[k]=str(v)[:150]
    return out
with P.open("rb") as f:
    for obj in ijson.items(f,"objectList.item",use_float=False):
        if not isinstance(obj,dict):continue
        allObj+=1
        oid=obj.get("id")
        acts=obj.get("actionList",[]) or []
        links=obj.get("actionLinkList",[]) or []
        allActions+=len(acts)
        allLinks+=len(links)
        if oid not in WATCH:
            allCommands+=sum(len(a.get("objCommandList",[]) or []) for a in acts)
            continue
        summary={"id":oid,"name":str(obj.get("name",""))[:70],"action_count":len(acts),
                 "link_count":len(links),"command_count":0,
                 "categories":collections.Counter(),"critical_actions":[],
                 "link_samples":[],"links_of_contact":[],"link_keys":collections.Counter(),
                 "command_fields":collections.Counter()}
        for a in acts:
            c=collections.Counter()
            examples=[]
            for cmd in a.get("objCommandList",[]) or []:
                allCommands+=1
                summary["command_count"]+=1
                for term in classcmd(cmd):c[term]+=1;summary["categories"][term]+=1
                for blk,p in cmd.items():
                    if isinstance(p,dict):
                        for k in p:summary["command_fields"][f"{blk}.{k}"]+=1
                if len(examples)<6 and (classcmd(cmd) or cmd.get("commandType") in (31,32)):
                    examples.append({"type":cmd.get("commandType"),"fields":shape(cmd)})
            if c:
                summary["critical_actions"].append({
                    "action_id":a.get("id"),"name":str(a.get("name",""))[:65],
                    "flags":dict(c),"examples":examples[:3]})
        for l in links:
            for k in l:summary["link_keys"][k]+=1
            if len(summary["link_samples"])<3:summary["link_samples"].append(briefly(l))
            conds=l.get("linkConditionList",[]) or []
            hit=False
            for cond in conds:
                if not isinstance(cond,dict):continue
                if cond.get("type") in (25,):hit=True
                if any("objectHit" in str(k) or "attackAreaTouched" in str(k) for k in cond):hit=True
            if hit:
                summary["links_of_contact"].append(briefly(l))
        summary["critical_actions"].sort(key=lambda x:sum(x["flags"].values()),reverse=True)
        summary["critical_actions"]=summary["critical_actions"][:60]
        summary["links_of_contact"]=summary["links_of_contact"][:50]
        summary["categories"]=dict(summary["categories"])
        summary["link_keys"]=dict(summary["link_keys"])
        summary["command_fields"]=dict(summary["command_fields"].most_common(15))
        doc["actors"][str(oid)]=summary
        print("STAGE134_OBJECT",oid,summary["name"],"actions",summary["action_count"],
            "links",summary["link_count"],"commands",summary["command_count"],
            "flags",json.dumps(summary["categories"],ensure_ascii=False)[:1200])
        print("STAGE134_LINK_KEYS",oid,json.dumps(summary["link_keys"],ensure_ascii=False)[:500])
        print("STAGE134_LINK_SAMPLE",oid,json.dumps(summary["link_samples"][:1],ensure_ascii=False,default=str)[:1200])
        print("STAGE134_CONTACT_LINKS",oid,len(summary["links_of_contact"]),
          json.dumps(summary["links_of_contact"][:2],ensure_ascii=False,default=str)[:2200])
        print("STAGE134_ACTION_TOP",oid,json.dumps(summary["critical_actions"][:3],ensure_ascii=False,default=str)[:2200])
doc["project_counts"]={"objects":allObj,"actions":allActions,"commands":allCommands,"links":allLinks}
print("STAGE134_GLOBAL_PROJECT_COUNTS",json.dumps(doc["project_counts"]))
# Original executable RVA fingerprint, no disassembly or modification.
exe=E.read_bytes()
e_lfanew=struct.unpack_from("<I",exe,0x3c)[0]
assert exe[:2]==b"MZ" and exe[e_lfanew:e_lfanew+4]==b"PE\x00\x00"
machine,nsects=struct.unpack_from("<HH",exe,e_lfanew+4)
opt_size=struct.unpack_from("<H",exe,e_lfanew+20)[0]
sections=[]
for i in range(nsects):
    off=e_lfanew+24+opt_size+40*i
    nm=exe[off:off+8].rstrip(b"\x00").decode("latin1")
    vsize,rva,rawsize,rawptr=struct.unpack_from("<IIII",exe,off+8)
    sections.append((nm,rva,max(vsize,rawsize),rawptr))
assert machine==0x14c
def rva_bytes(rva,n=12):
    for nm,base,size,ptr in sections:
        if base<=rva<base+size:
            offset=ptr+(rva-base)
            return {"section":nm,"file_offset":offset,"bytes":exe[offset:offset+n].hex()}
    return None
rv={hex(k):rva_bytes(k) for k in [0x14D320,0x154920,0x146470,0x148530,0x149980,0x1401a0,0x14D270,0x151890]}
doc["exe_function_fingerprints"]=rv
print("STAGE134_EXE_SECTIONS",json.dumps(sections))
print("STAGE134_RVA_FINGERPRINTS",json.dumps(rv))
out=ROOT/"STAGE134_EVENT_CHAIN_ORIGINAL.json"
out.write_text(json.dumps(doc,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
print("STAGE134_COMPLETE_AUDIT_PASS","report_bytes",out.stat().st_size)
