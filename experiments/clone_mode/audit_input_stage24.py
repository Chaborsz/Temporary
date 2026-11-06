#!/usr/bin/env python3
"""Stage24: Find clone-specific controller/input routing, and available F keys.
READ-ONLY binary and project-data inspection.
"""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,re,json,pefile,ijson,capstone
EXE=Path("cheats/endurance/input/player.exe")
PROJECT=Path("/tmp/clone-control/project_decrypted.json")
assert hashlib.sha256(EXE.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
assert PROJECT.stat().st_size==301997021
p=pefile.PE(str(EXE),fast_load=True)
p.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
b=p.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
identifiers=("operat","control","input","keybord","keyboard","keyinput","joy","gamepad","gamecontroller","player","keycode","press","trigger")
symbols=[]
for e in p.DIRECTORY_ENTRY_EXPORT.symbols:
 if not e.name:continue
 name=e.name.decode("utf-8","replace")
 low=name.lower()
 if any(term in low for term in identifiers):
  isObject="@Object@agtk@@" in name
  if isObject or any(x in low for x in ("operat","input","keybord","keyboard","player","gamepad","controller","keycode")):
   symbols.append((b+e.address,name))
print("STAGE24_INTERESTING_ENGINE_EXPORTS",len(symbols))
for va,n in symbols[:275]:
 print("ENGINE_INPUT_SYMBOL",hex(va),n[:230])
 if "@Object@agtk@@" in n and any(term in n.lower() for term in identifiers):
  raw=p.__data__[p.get_offset_from_rva(va-b):][:90]
  ins=[]
  for i in md.disasm(raw,va):
   ins.append(i.mnemonic+" "+i.op_str)
   if len(ins)>=16 or i.mnemonic.startswith("ret"):break
  print("ENGINE_INPUT_DISASM",hex(va)," | ".join(ins)[:610])
# track actual keyboard mapping F keys and project controls, rather than invent F availability.
terms=("f1","f2","f3","f4","f5","f6","f7","f8","f9","f10","f11","f12","keycode","keycodeid","keyboard","input","keyconfig","inputmapping","keybinding","keyid","keyboardid","operatable")
keycounts=Counter()
pairs=defaultdict(list)
hits=[]
stack=[]
with PROJECT.open("rb") as fh:
 for prefix,event,value in ijson.parse(fh,use_float=False):
  if event=="start_map":stack.append({"prefix":prefix,"fields":{}})
  elif event=="map_key":
   k=str(value)
   if any(x in k.casefold() for x in ("key","input","operat","button","controller")):
    keycounts[k]+=1
  elif event in ("string","number","boolean","null"):
   name=prefix.rsplit(".",1)[-1]
   if stack and prefix.rsplit(".",1)[0]==stack[-1]["prefix"] and len(stack[-1]["fields"])<45:
    if name in ("id","name","keyCode","keycode","key","keyId","keyid","inputId","inputType","button","buttonId","keyboard","operatable","actionId","objectId","value","type","keyName"):
     stack[-1]["fields"][name]=str(value)[:125]
   val=str(value).casefold()
   if event=="string" and re.search(r'\bf(?:[1-9]|1[0-2])\b',val):
    if len(hits)<130:
     hits.append({"path":prefix[-175:],"value":str(value)[:140],
                  "context":[x["fields"] for x in stack[-3:]]})
  elif event=="end_map" and stack:
   fr=stack.pop()
   f=fr["fields"]
   if any(k in f for k in ("keyCode","keycode","keyId","keyid","keyboard","buttonId","inputId")):
    prefix_key=fr["prefix"][:120]
    pairs[prefix_key].append(f)
print("STAGE24_KEY_PROPERTY_COUNTS",json.dumps(keycounts.most_common(90),ensure_ascii=False))
for n,a in list(pairs.items())[:95]:
 print("KEY_RECORD",n,json.dumps(a[:3],ensure_ascii=False)[:750])
for h in hits[:110]:
 print("KEY_F_LITERAL",json.dumps(h,ensure_ascii=False)[:650])
print("STAGE24_PASS",len(symbols),len(keycounts),sum(map(len,pairs.values())),len(hits))
out=Path("experiments/clone_mode/analysis/stage24-input-control.json")
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({"symbols":[{"va":hex(a),"name":n} for a,n in symbols],
 "f_literal_hits":hits,"keys":keycounts.most_common(200),
 "keyrecords":dict((k,v[:15]) for k,v in list(pairs.items())[:180])},
 ensure_ascii=False,indent=2))
