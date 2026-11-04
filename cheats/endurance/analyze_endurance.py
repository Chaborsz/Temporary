#!/usr/bin/env python3
"""Read-only static audit of the Endurance (stamina/arousal) gauge in AGTK PE32.
No patches, runtime cheats, executables, or game data are generated.
"""
import argparse, hashlib, json, re, struct, zipfile
from pathlib import Path
from collections import Counter

EXPECTED_SHA256 = "02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
EXPECTED_SIZE = 8757760
TERMS = [
    "endurance", "excitation", "arousal", "stamina", "excitement",
    "lust", "libido", "pleasure", "orgasm", "energy", "tension",
    "興奮", "興奋", "耐久", "快感", "絶頂", "欲情", "体力", "精力",
]
STRONG = {"endurance", "excitation", "arousal", "興奮", "興奋", "耐久"}
ENCODINGS = ("utf-8-sig", "utf-16-le", "cp932")
MAX_FILE = 5_000_000
MAX_MATCHES = 300

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as fp:
        for part in iter(lambda: fp.read(1024*1024), b""):
            h.update(part)
    return h.hexdigest()

def sanitize(s, length=240):
    s="".join(c if c.isprintable() or c == " " else " " for c in s)
    return s[:length]

def binary_strings(data):
    patterns = [
      (re.compile(rb"[\x20-\x7e]{4,}"), "ascii"),
      (re.compile(rb"(?:[\x20-\x7e]\x00){4,}"), "utf16le"),
    ]
    for pat, typ in patterns:
        for m in pat.finditer(data):
            try:
                txt=m.group().decode("ascii" if typ=="ascii" else "utf-16le")
            except UnicodeError:
                continue
            if any(t in txt.casefold() for t in TERMS):
                yield {"offset":m.start(), "encoding":typ, "text":sanitize(txt)}

def matched_lines(name, blob):
    if len(blob)>MAX_FILE or b"\x00" in blob[:512] and b"\xff\xfe" not in blob[:4]:
        return []
    for enc in ENCODINGS:
        try:
            text=blob.decode(enc)
        except UnicodeError:
            continue
        if sum(x in text.casefold() for x in TERMS)==0:
            continue
        matches=[]
        for lineno, line in enumerate(text.splitlines(),1):
            if any(t in line.casefold() for t in TERMS):
                matches.append({"source":name,"line":lineno,"text":sanitize(line)})
                if len(matches)>=MAX_MATCHES:
                    break
        return matches
    return []

def analyze_assets(root):
    matches=[]
    seen=Counter()
    if not root.exists(): return matches, seen
    for item in sorted(root.rglob("*")):
        if not item.is_file(): continue
        name=item.relative_to(root).as_posix()
        if item.suffix.lower()==".zip":
            try:
                with zipfile.ZipFile(item) as z:
                    for zf in z.infolist():
                        if zf.is_dir() or zf.file_size>MAX_FILE: continue
                        if not zf.filename.lower().endswith((".json",".txt",".csv",".xml",".js",".dat",".md",".ini",".yaml",".yml")):
                            continue
                        seen["zip_members_checked"]+=1
                        matches.extend(matched_lines(name+"!"+zf.filename, z.read(zf)))
            except (OSError,zipfile.BadZipFile,RuntimeError) as e:
                seen["archive_errors"]+=1
            continue
        if item.suffix.lower() not in (".json",".txt",".csv",".xml",".js",".dat",".md",".ini",".yaml",".yml"):
            continue
        if item.stat().st_size>MAX_FILE: continue
        seen["text_files_checked"]+=1
        try: matches.extend(matched_lines(name,item.read_bytes()))
        except OSError: seen["file_errors"]+=1
    return matches[:MAX_MATCHES],seen

def run(exe, assets):
    info={"project":"AGTK / Pixel Game Maker MV","target":"Endurance / stamina-arousal gauge BELOW HP/MP",
          "hp_excluded":True,"source":str(exe),"status":"SOURCE_REQUIRED","evidence":[]}
    asset_matches, seen=analyze_assets(assets)
    info["asset_scan"]={"counts":dict(seen),"matches":asset_matches}
    if not exe.is_file():
        info["next"]="Supply original player.exe as cheats/endurance/input/player.exe. The source is not in GitHub."
        return info
    info["size"]=exe.stat().st_size
    info["sha256"]=digest(exe)
    if info["size"]!=EXPECTED_SIZE or info["sha256"]!=EXPECTED_SHA256:
        info["status"]="SOURCE_MISMATCH"
        info["next"]="Do not analyze a different or corrupted executable without updating the canonical baseline."
        return info
    import pefile, capstone
    pe=pefile.PE(str(exe), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    if pe.FILE_HEADER.Machine!=0x14c or pe.OPTIONAL_HEADER.ImageBase!=0x400000:
        info["status"]="PE_FORMAT_MISMATCH"
        return info
    raw=exe.read_bytes()
    sections=[]
    for s in pe.sections:
        sections.append({"name":s.Name.rstrip(b"\x00").decode("ascii","replace"),
          "rva":hex(s.VirtualAddress),"raw_offset":hex(s.PointerToRawData),
          "raw_size":s.SizeOfRawData})
    info["pe"]={"machine":"i386","image_base":hex(pe.OPTIONAL_HEADER.ImageBase),"sections":sections}
    strings=[]
    section_map=[]
    for s in pe.sections:
        start=s.PointerToRawData
        end=start+s.SizeOfRawData
        for found in binary_strings(raw[start:end]):
            offset=start+found["offset"]
            rva=s.VirtualAddress+(offset-start)
            found.update({"file_offset":hex(offset),"rva":hex(rva),"va":hex(0x400000+rva),
                          "section":s.Name.rstrip(b"\x00").decode("ascii","replace")})
            strings.append(found)
    strings.sort(key=lambda x:(not any(t in x["text"].casefold() for t in STRONG),int(x["rva"],16)))
    strings=strings[:MAX_MATCHES]
    info["binary_keyword_strings"]=strings
    exports=[]
    for e in getattr(getattr(pe,"DIRECTORY_ENTRY_EXPORT",None),"symbols",[]):
        nm=(e.name or b"").decode("utf-8","replace")
        if any(t in nm.casefold() for t in ("variable","value","endurance","excite","stamina","arousal","agtk::")):
            exports.append({"name":sanitize(nm,180),"rva":hex(e.address),"va":hex(0x400000+e.address)})
    info["relevant_exports"]=exports[:250]
    # Trace concrete absolute references to discovered label strings only.
    targets={int(x["va"],16) for x in strings}
    xrefs=[]
    md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
    md.detail=True
    for s in pe.sections:
        if not (s.Characteristics & 0x20000000): continue
        code=s.get_data()
        for ins in md.disasm(code,0x400000+s.VirtualAddress):
            refs=set()
            for op in ins.operands:
                if op.type==capstone.x86.X86_OP_IMM and op.imm in targets and not ins.mnemonic.startswith(("j","call")):
                    refs.add(op.imm)
                if op.type==capstone.x86.X86_OP_MEM and op.mem.disp in targets:
                    refs.add(op.mem.disp)
            if refs:
                xrefs.append({"at":hex(ins.address),"instruction":sanitize(ins.mnemonic+" "+ins.op_str,160),
                             "target_va":[hex(t) for t in sorted(refs)]})
                if len(xrefs)>=MAX_MATCHES: break
        if len(xrefs)>=MAX_MATCHES: break
    info["string_xrefs"]=xrefs
    confirmed=[m for m in asset_matches if any(t in m["text"].casefold() for t in STRONG)]
    confirmed+= [m for m in strings if any(t in m["text"].casefold() for t in STRONG)]
    info["status"]="AUDITED_WITH_DIRECT_TERMS" if confirmed else "AUDITED_NO_DIRECT_TERM"
    info["interpretation"]="String/reference candidates are NOT proven to be the live gauge variable or damage/regen function."
    info["next"]="Correlate candidate labels with player game-data variable IDs and xrefs. Trace writes, consumption, regen; do not patch HP."
    return info

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--exe",type=Path,required=True)
    p.add_argument("--assets",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    try:
        result=run(a.exe,a.assets)
    except Exception as e:
        result={"status":"ANALYSIS_ERROR","error":type(e).__name__+": "+sanitize(str(e))}
    (a.output/"endurance-audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=[
        "# Endurance — static checkpoint",
        "Status: "+result["status"],
        "Target: Endurance = aguante/excitación gauge, below HP and MP.",
        "HP is not in scope; no runtime test and no modification performed.",
        "Source hash: "+result.get("sha256","not available"),
        "Strong text matches: "+str(sum(1 for m in result.get("binary_keyword_strings",[]) if any(t in m["text"].casefold() for t in STRONG))),
        "Asset matches: "+str(len(result.get("asset_scan",{}).get("matches",[]))),
        "Static string xrefs: "+str(len(result.get("string_xrefs",[]))),
        "Next: "+result.get("next","See JSON for error.")
    ]
    (a.output/"CHECKPOINT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))
    if result["status"] in ("SOURCE_MISMATCH","PE_FORMAT_MISMATCH","ANALYSIS_ERROR"):
        raise SystemExit(1)

if __name__=="__main__":main()
