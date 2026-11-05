#!/usr/bin/env python3
"""Audit imports and export/calling conventions for 32-bit AGTK DLL add-on.
Never patches original player.exe.
"""
import capstone,pefile,hashlib,json,sys
from pathlib import Path
EXE=Path("cheats/endurance/input/player.exe")
EXPECTED="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
assert hashlib.sha256(EXE.read_bytes()).hexdigest()==EXPECTED
pe=pefile.PE(str(EXE))
base=pe.OPTIONAL_HEADER.ImageBase
pe.parse_data_directories()
imports=[]
for lib in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[]):
    imports.append({"dll":lib.dll.decode("ascii","replace"),
      "imports":[e.name.decode("ascii","replace") if e.name else "#"+str(e.ordinal) for e in lib.imports]})
exp=[]
for e in getattr(pe.DIRECTORY_ENTRY_EXPORT,"symbols",[]):
    if e.name:
        name=e.name.decode("utf-8","replace")
        if any(x in name.lower() for x in ("playvariabledata@","playdata@data@agtk","gamemanager@agtk","projectdata@","getinstance@","appdelegate@","variabledata@","dll","plugin","scriptexecute")):
            exp.append({"va":hex(base+e.address),"rva":hex(e.address),"name":name})
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
md.detail=True
selected=[x for x in exp if "playvariabledata@" in x["name"].lower() or "playdata@data@agtk" in x["name"].lower() or "gamemanager@agtk" in x["name"].lower() or ("getinstance@" in x["name"].lower() and "agtk" in x["name"].lower())]
disasm={}
for x in selected[:90]:
    va=int(x["va"],16)
    rva=va-base
    try:
        off=pe.get_offset_from_rva(rva)
        code=pe.__data__[off:off+128]
        ins=[]
        for i in md.disasm(code,va):
            ins.append({"va":hex(i.address),"hex":i.bytes.hex(),"asm":i.mnemonic+" "+i.op_str})
            if len(ins)>=28 or i.mnemonic in ("ret","retn"):break
        disasm[x["name"]]={"va":x["va"],"lines":ins}
    except Exception as exc:
        disasm[x["name"]]={"error":str(exc)}
data={"size":EXE.stat().st_size,"sha256":EXPECTED,"machine":hex(pe.FILE_HEADER.Machine),
      "image_base":hex(base),"imports":imports,"symbols":exp,"prologues":disasm}
Path("cheats/endurance/dll").mkdir(parents=True,exist_ok=True)
Path("/tmp/endurance_pe_audit.json").write_text(json.dumps(data,ensure_ascii=False,indent=2))
print("PE_TARGET_ARCH x86",data["size"],data["image_base"])
for lib in imports:
    print("IMPORT",lib["dll"],len(lib["imports"]),"examples",",".join(lib["imports"][:16]))
print("RELEVANT_SYMBOLS",len(exp),"FUNCTIONS",len(selected))
for x in exp:
    if any(y in x["name"].lower() for y in ("playvariabledata@","getvariabledata@playdata@","getinstance@","setvalue@","getvalue@","getid@","getvariable")):
        print("EXPORT",x["va"],x["name"])
for x in selected:
    if "playvariabledata@" in x["name"].lower() or "getvariabledata@playdata@" in x["name"].lower() or ("getinstance@" in x["name"].lower() and "agtk" in x["name"].lower()):
        info=disasm.get(x["name"])
        if info:print("CODE",x["va"],x["name"]," | ".join(i["asm"] for i in info.get("lines",[])[:21]))
