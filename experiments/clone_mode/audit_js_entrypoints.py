#!/usr/bin/env python3
"""Stage15: native / JS entrypoint viability for hotkey-triggered AGTK player clone."""
import hashlib,json,pefile,capstone
from pathlib import Path
exe=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(exe.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
p=pefile.PE(str(exe),fast_load=True)
p.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
b=p.OPTIONAL_HEADER.ImageBase
symbols=[]
for o in p.DIRECTORY_ENTRY_EXPORT.symbols:
 if not o.name:continue
 n=o.name.decode("utf8","replace")
 nl=n.lower()
 categories={
 "script":("scriptcore","scriptingcore","evalstring","executescript","runscript","evaluate","scriptmanager",
           "jsb_","js::","jsengine","scriptengine","evalscript","javascrip","script@","execscript",
           "jscontext","jsapi","jsfunction","setscript"),
 "spawn":("execactionobjectcreate","_create@object@agtk","getcurrent","getscene","getscenelayer",
          "getobjectid@object","getposition@object","getobjectdata@object",
          "getplayer","setoperatable","isoperatable","setinput","getinput","changeinput","setcontrollable","getobjectlist",
          "createobject","setcreateobjectlist","getcreateobjectlist","getplayerobject"),
 "global":("gamemanager","scenemanager","getinstance@scene","getinstance@gamemanager")
 }
 cls=[k for k,words in categories.items() if any(x in nl for x in words)]
 if cls:symbols.append({"va":b+o.address,"name":n,"categories":cls})
print("STAGE15_EXPORT_COUNT",len(symbols))
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for o in symbols:
 print("SYM",",".join(o["categories"]),hex(o["va"]),o["name"][:220])
 if any(w in o["name"].lower() for w in ("evalstring","runscript","executescript","execactionobjectcreate","getscenelayer@object","getobjectdata@object",
                             "getinstance@scriptingcore","getscene@object","getcurrent","getplayerobject","getobjectid@object")):
  try:
   raw=p.__data__[p.get_offset_from_rva(o["va"]-b):][:110]
   instr=[]
   for i in md.disasm(raw,o["va"]):
    instr.append(i.mnemonic+" "+i.op_str)
    if len(instr)>=24 or i.mnemonic.startswith("ret"):break
   print("CODE",hex(o["va"])," | ".join(instr)[:820])
  except Exception:pass
path=Path("experiments/clone_mode/analysis/stage15-exports.json")
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(symbols,ensure_ascii=False,indent=2))
