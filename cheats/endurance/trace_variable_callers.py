#!/usr/bin/env python3
"""AGTK Endurance stage 3: read-only callsite analysis of variable lookup.
Engine symbols do NOT themselves prove a specific game meter.
"""
import argparse, collections, hashlib, json
from pathlib import Path
import capstone, pefile

SHA="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
TARGET_SYMBOLS={
    "?getVariableData@PlayObjectData@data@agtk@@QAEPAVPlayVariableData@23@H@Z",
    "?getVariableData@PlayData@data@agtk@@QAEPAVPlayVariableData@23@HH@Z",
    "?getVariableDataByName@PlayObjectData@data@agtk@@QAEPAVPlayVariableData@23@PBD@Z",
    "?adjustVariableData@PlayObjectData@data@agtk@@QAEXPAVPlayVariableData@23@@Z",
}
def hashfile(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--exe",required=True,type=Path)
    pa.add_argument("--out",required=True,type=Path)
    opt=pa.parse_args()
    if hashfile(opt.exe)!=SHA:raise SystemExit("CANONICAL_SHA_MISMATCH")
    p=pefile.PE(str(opt.exe),fast_load=True)
    p.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    labels={}
    for s in p.DIRECTORY_ENTRY_EXPORT.symbols:
        name=(s.name or b"").decode("utf-8","replace")
        if name in TARGET_SYMBOLS:labels[p.OPTIONAL_HEADER.ImageBase+s.address]=name
    md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
    results=[]
    for sec in p.sections:
        if not(sec.Characteristics & 0x20000000):continue
        addr=p.OPTIONAL_HEADER.ImageBase+sec.VirtualAddress
        instructions=list(md.disasm(sec.get_data(),addr))
        for i,inst in enumerate(instructions):
            if inst.mnemonic!="call" or not inst.op_str.startswith("0x"):continue
            try: target=int(inst.op_str,16)
            except ValueError:continue
            if target not in labels:continue
            context=instructions[max(0,i-9):min(len(instructions),i+4)]
            # No variable IDs are asserted from stack arguments until proven.
            results.append({
                "function":labels[target],"function_va":hex(target),"call_va":hex(inst.address),
                "instructions":[{"va":hex(x.address),"asm":x.mnemonic+" "+x.op_str}
                                for x in context]})
    output={"source_sha256":SHA,"scope":"Endurance stamina/arousal, not HP",
        "stage":"AGTK play variable lookup callers","function_symbols":{hex(k):v for k,v in labels.items()},
        "callsite_count":len(results),"callsites":results,
        "interpretation":"These are generic AGTK PlayData calls. Immediate literals at callsites are not Endurance variable IDs absent game-data correlation.",
        "next":"Link source game-data/project variable identifiers and HUD gauge binding to callers."}
    opt.out.mkdir(parents=True,exist_ok=True)
    (opt.out/"stage3-variable-calls.json").write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    by=collections.Counter(x["function"] for x in results)
    print("STAGE3 SOURCE SHA OK; analyzed generic variable lookup callsites:",len(results))
    for sym in sorted(by):print("CALLS",by[sym],sym)
    print("SAMPLE_CALLSITES (not identification of Endurance):")
    for entry in results[:7]:
        print(entry["function"].split("@")[0],entry["call_va"],
              " | ".join(x["asm"][:50] for x in entry["instructions"][-10:]))
    print("TARGET_ENDURANCE_ID=UNPROVEN; NO_PATCH")
if __name__=="__main__":main()
