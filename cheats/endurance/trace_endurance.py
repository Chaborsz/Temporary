#!/usr/bin/env python3
"""Second-stage, read-only AGTK Endurance audit: symbol and call-graph reconnaissance.
Do NOT infer a cheat from generic engine variable functions.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path
import capstone,pefile

EXPECTED = "02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
TOKENS = ("endurance","excitation","excitement","arousal","stamina","lust","pleasure","tension",
          "gauge","meter","variable","switch","status","parameter","parameter",
          "player","object","energy","scene","project","ui","display","value")
STRONG = ("endurance","excitation","excitement","arousal","stamina","lust","pleasure","tension",
          "興奮","興奋","耐久","快感","欲情","精力")
GENERIC = ("variable","switch","parameter","gauge","meter","value")
def load(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--exe",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    if not a.exe.is_file(): raise SystemExit("MISSING_CANONICAL_EXE")
    sha=load(a.exe)
    if sha!=EXPECTED: raise SystemExit("CANONICAL_SHA_MISMATCH "+sha)
    pe=pefile.PE(str(a.exe),fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    exports=[]
    for e in getattr(getattr(pe,"DIRECTORY_ENTRY_EXPORT",None),"symbols",[]):
        n=(e.name or b"").decode("utf-8","replace")
        exports.append({"va":pe.OPTIONAL_HEADER.ImageBase+e.address,
                        "rva":e.address,"name":n})
    relevant=[x for x in exports if any(t in x["name"].lower() for t in TOKENS)]
    # Exclude health point methods from discussion; we're tracing engine variables only.
    def exclude_hp(s):
        return bool(re.search(r"(?:getHp|setHp|addHp|decHp|reduceHp|damageHp)",s,re.I))
    relevant=[x for x in relevant if not exclude_hp(x["name"])]
    core=[x for x in relevant if any(t in x["name"].lower() for t in GENERIC)]
    md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
    call_counts=collections.Counter()
    callers=collections.defaultdict(list)
    core_vas={x["va"] for x in core}
    instr_count=0
    for section in pe.sections:
        if not (section.Characteristics & 0x20000000):continue
        base=pe.OPTIONAL_HEADER.ImageBase+section.VirtualAddress
        for ins in md.disasm(section.get_data(),base):
            instr_count+=1
            if ins.mnemonic!="call": continue
            if not ins.op_str.startswith("0x"):continue
            try: dest=int(ins.op_str,16)
            except ValueError:continue
            if dest in core_vas:
                call_counts[dest]+=1
                if len(callers[dest])<8:callers[dest].append(hex(ins.address))
    ranked=[]
    for e in core:
        if not e["name"]:continue
        ranked.append({"va":hex(e["va"]),"rva":hex(e["rva"]),
           "symbol":e["name"][:200],"static_direct_calls":call_counts[e["va"]],
           "sample_call_sites":callers[e["va"]]})
    ranked.sort(key=lambda x:(-x["static_direct_calls"],x["symbol"]))
    strong_exports=[{"va":hex(e["va"]),"name":e["name"][:200]} for e in relevant
                    if any(t in e["name"].casefold() for t in STRONG)]
    info={"phase":"Endurance V2 symbol/call reconnaissance","source_sha256":sha,
          "target":"Endurance=aguante/excitacion, BELOW HP/MP",
          "hp_excluded":True,"symbols_total":len(exports),
          "candidate_exports":len(relevant),"generic_value_symbols":len(core),
          "instructions_disassembled":instr_count,
          "direct_named_endurance_symbols":strong_exports[:30],
          "generic_candidate_functions":ranked[:120],
          "warning":"Exported AGTK engine methods are general-purpose. CALL counts DO NOT identify the Endurance game variable.",
          "next":"Need game-specific metadata/variable IDs or runtime gauge correlation; no direct Endurance identification is proven."}
    (a.out/"stage2.json").write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STAGE2 SHA OK | exports="+str(len(exports))+
          " | candidate="+str(len(relevant))+" | generic="+str(len(core))+
          " | disassembled="+str(instr_count))
    print("DIRECT_ENDURANCE_SYMBOLS "+str(len(strong_exports)))
    for e in strong_exports[:10]: print("DIRECT",e["va"],e["name"][:140])
    print("TOP_GENERIC_CANDIDATES")
    for e in ranked[:24]:print(e["va"],"calls="+str(e["static_direct_calls"]),e["symbol"][:130])
    print("ENDURANCE_LIVE_VARIABLE_UNPROVEN")
if __name__=="__main__":main()
