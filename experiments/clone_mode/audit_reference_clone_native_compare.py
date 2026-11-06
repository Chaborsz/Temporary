#!/usr/bin/env python3
"""PE32 exported-function comparison between two PGMM builds; read-only."""
import argparse,collections,hashlib,json
from pathlib import Path
import pefile,capstone
TOKENS=("getTargetObjectById@ObjectAction","getTargetObjectByGroup@ObjectAction",
 "getTargetObjectInstanceId@ObjectAction","getTargetObjectByInstanceId@GameManager",
 "getTargetObjectListByObjectId@GameManager","getObjectPlayer@Scene",
 "getObjectInstance@Scene","createObject@SceneLayer","addObject@SceneLayer",
 "removeObject@SceneLayer","damaged@Object","addHp@PlayObjectData",
 "getCollisionHitAttackList@Object","getCollisionAttackHitList@Object",
 "getDamagedList@Object","checkAttackableObject@Object","execActionObjectCreate@ObjectAction",
 "execActionSwitchVariableChange@ObjectAction","checkLinkConditionObjectHit@ObjectAction",
 "checkLinkConditionAttackAreaTouched@ObjectAction","checkLinkConditionObjectFound@ObjectAction")
def read(p):
 pe=pefile.PE(str(p),fast_load=False)
 symbols={}
 for s in pe.DIRECTORY_ENTRY_EXPORT.symbols:
  if s.name:symbols[s.name.decode("utf-8","replace")]=s.address
 return pe,symbols
def at(pe,rva,n=32):
 try:return pe.get_data(rva,n)
 except Exception:return b""
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--new",required=True);ap.add_argument("--old",required=True);ap.add_argument("--out",required=True)
 a=ap.parse_args();old,sy=read(a.old);new,ns=read(a.new)
 selected=[]
 for tok in TOKENS:
  for name in sorted(set(sy)|set(ns)):
   if tok not in name:continue
   x=sy.get(name);y=ns.get(name)
   b1=at(old,x) if x is not None else b""
   b2=at(new,y) if y is not None else b""
   obj={"symbol":name,"old_rva":hex(x) if x is not None else None,"new_rva":hex(y) if y is not None else None,
     "rva_shift":y-x if x is not None and y is not None else None,
     "same_first32":bool(b1 and b2 and b1==b2),"old_first24":b1[:24].hex(),"new_first24":b2[:24].hex()}
   selected.append(obj)
 shifts=collections.Counter(ns[x]-sy[x] for x in set(sy)&set(ns))
 data={"old":str(a.old),"new":str(a.new),"exports_old":len(sy),"exports_new":len(ns),
       "exports_shared":len(set(sy)&set(ns)),"top_shifts":shifts.most_common(12),"native_functions":selected}
 dest=Path(a.out);dest.mkdir(parents=True,exist_ok=True)
 (dest/"NATIVE_FUNCTION_RVA_DIFF.json").write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
 print("=== NATIVE_COMPARE ===")
 print("EXPORT_COUNTS",len(sy),len(ns),"shared",data["exports_shared"])
 print("RVA_SHIFT_MODES",shifts.most_common(8))
 for p in selected:
  print("PE_SYMBOL",json.dumps(p,ensure_ascii=False,default=str)[:420])
 print("NATIVE_COMPARE_PASS functions",len(selected))
if __name__=="__main__":main()
