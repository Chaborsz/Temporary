#!/usr/bin/env python3
"""Determine exact AGTK PlayVariableData read/write entry points for next x86 diagnostic.
Read-only static PE scan: no game patch.
"""
import collections,hashlib,json
from pathlib import Path
import pefile,capstone
EXE=Path("cheats/endurance/input/player.exe")
EXPECTED="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
sha=hashlib.sha256(EXE.read_bytes()).hexdigest()
assert sha==EXPECTED
pe=pefile.PE(str(EXE),fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
base=pe.OPTIONAL_HEADER.ImageBase
names={}
for item in getattr(getattr(pe,"DIRECTORY_ENTRY_EXPORT",None),"symbols",[]):
  if item.name:
    names[base+item.address]=item.name.decode("utf-8","replace")
targets={
  "get_value":{"va":0x4057c0,"meaning":"PlayVariableData::getValue"},
  "get_first":{"va":0x4052a0,"meaning":"PlayVariableData::getValueFirst"},
  "set_value_candidate":{"va":0x46ab90,"meaning":"maybe PlayVariableData::setValue; verify"},
  "reset":{"va":0x46ab00,"meaning":"PlayVariableData::reset"},
  "request_value":{"va":0x46acb0,"meaning":"PlayVariableData::requestValue(double,float)"},
  "assign_game_manager":{"va":0x5e8760,"meaning":"GameManager::assignVariableData; hook observed zero calls"},
  "get_common_variable":{"va":0x46d7b0,"meaning":"PlayData::getCommonVariableData(id)"},
  "get_variable_object":{"va":0x46bee0,"meaning":"PlayObjectData::getVariableData(id)"},
  "get_var_by_scene":{"va":0x46d940,"meaning":"PlayData::getVariableData(int,int)"},
  "adjust_global":{"va":0x46e140,"meaning":"PlayData::adjustCommonVariableData"},
}
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
listing=[]
for section in pe.sections:
  if not section.Characteristics&0x20000000:continue
  addr=base+section.VirtualAddress
  for inst in md.disasm(section.get_data(),addr):
    if inst.mnemonic!="call" or not inst.op_str.startswith("0x"):continue
    try:callee=int(inst.op_str,16)
    except ValueError:continue
    if callee in [x["va"] for x in targets.values()]:
      listing.append((callee,inst.address))
for key,t in targets.items():
  va=t["va"];code=pe.__data__[pe.get_offset_from_rva(va-base):][:160]
  instructions=[];used=0
  for inst in md.disasm(code,va):
    instructions.append({"offset":hex(inst.address),"bytes":inst.bytes.hex(),"mnemonic":inst.mnemonic,"operands":inst.op_str})
    used += inst.size
    if len(instructions)>=40 or inst.mnemonic in ("ret","retn"):break
  direct=[hex(a) for x,a in listing if x==va]
  print("TARGET",key,hex(va),"symbol",names.get(va,"none"),"firstbytes",code[:24].hex(),"calls",len(direct))
  print("DISASM",key," | ".join("%s %s"%(i["mnemonic"],i["operands"]) for i in instructions))
  print("CALL_SAMPLES",key,",".join(direct[:12]))
  t.update({"symbol":names.get(va),"entry_hex":code[:32].hex(),"instructions":instructions,"direct_calls":len(direct),"samples":direct[:20]})
for va,n in names.items():
  if 0x46a900<=va<=0x46ad50:
    print("NEARBY_EXPORT",hex(va),n)
out=Path("analysis-results/endurance/stage11-static-writer-audit.json")
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({"sha256":sha,"targets":targets},ensure_ascii=False,indent=2))
print("STAGE11_STATIC_PASS",len(listing))
