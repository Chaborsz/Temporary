#!/usr/bin/env python3
"""Stage73: read-only disassembly of canonical AGTK command and victim routing.
Never executes player.exe or writes original game data."""
from pathlib import Path
import json,collections,struct,hashlib,sys
import pefile,capstone
EXE=Path("cheats/endurance/input/player.exe")
EXPECTED="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
OUT=Path("analysis-results/clone-stage73-native")
OUT.mkdir(parents=True,exist_ok=True)
assert hashlib.sha256(EXE.read_bytes()).hexdigest()==EXPECTED
pe=pefile.PE(str(EXE))
base=pe.OPTIONAL_HEADER.ImageBase
exports={s.address:s.name.decode("utf-8","replace") for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
starts=sorted(exports)
def sym(rva):
    if rva in exports:return exports[rva]
    lo=max((s for s in starts if s<=rva),default=None)
    return ("%s+0x%x"%(exports[lo],rva-lo)) if lo is not None and rva-lo<0x2000 else ""
target={
"exec_switch_variable":0x146470,
"action_exec_dispatch":0x148530,
"object_play_action":0x12fdf0,
"object_change_dispatch":0x1401a0,
"script_command_dispatch":0x149980,
"link_variable_condition":0x153080,
"get_object_variable":0x6bee0,
"get_object_state":0x12ffc0,
"viewport_intersects":0x1bca60,
"get_target_by_id":0x14d320,
"get_target_by_group":0x14d270,
"get_target_instance":0x14d420,
"manager_target_by_instance":0x1e8470,
"manager_target_list_by_object":0x1e8500,
"link_object_hit":0x154920,
"link_attack_area_touched":0x14f6d0,
"link_object_found":0x151890,
"set_play_variable_value":0x6ab90,
"object_damaged":0x12f760,
"object_attackable":0x12ffc0,
"playobject_add_hp":0x6c670,
}
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
md.detail=True
reports={}
all_comments=collections.Counter()
for name,rv in target.items():
    greater=next((r for r in starts if r>rv),None)
    size=min(20000,max(2048,(greater-rv) if greater else 8192))
    data=pe.get_data(rv,size)
    insns=list(md.disasm(data,base+rv))
    rows=[];links=[];constants=collections.Counter()
    for i in insns:
        rva=i.address-base
        if i.mnemonic.startswith("call") or i.mnemonic.startswith("j"):
            dest=None
            if i.operands and i.operands[0].type==capstone.x86.X86_OP_IMM:
                dest=i.operands[0].imm-base
                if dest>=0 and dest<pe.OPTIONAL_HEADER.SizeOfImage:
                    links.append({"rva":hex(rva),"operation":i.mnemonic,"target_rva":hex(dest),"name":sym(dest)})
        for op in i.operands:
            if op.type==capstone.x86.X86_OP_IMM and op.imm in (1,2,0x7fe,0xfffffffe,0xffffffff,0x2003,0x2031,0x2044,0x2047):
                constants[hex(op.imm&0xffffffff)]+=1
        rows.append(f"{rva:08x} {i.bytes.hex():<24} {i.mnemonic:<9} {i.op_str:<45} {sym(links[-1]['target_rva'] and int(links[-1]['target_rva'],16)) if links and links[-1]['rva']==hex(rva) else ''}")
    (OUT/(name+".asm.txt")).write_text("\n".join(rows)+"\n",encoding="utf-8")
    reports[name]={"rva":hex(rv),"name":sym(rv),"size":size,"decoded":len(insns),"last_rva":hex(insns[-1].address-base) if insns else None,"calls":[x for x in links if x['operation'].startswith('call')],"jumps":[x for x in links if not x['operation'].startswith('call')],"constants":dict(constants)}
(OUT/"STAGE73_NATIVE_CALLS.json").write_text(json.dumps(reports,indent=2,ensure_ascii=False),encoding="utf-8")
with (OUT/"STAGE73_NATIVE_SUMMARY.md").open("w",encoding="utf-8") as f:
    f.write("# Stage73 native command and contact routing audit\n\nCanonical PE32 SHA256: "+EXPECTED+"\n\n")
    for n,r in reports.items():
        f.write(f"## {n}\n\nRVA {r['rva']}, export {r['name']}, examined {r['size']} bytes, decoded {r['decoded']} instructions.\n\n")
        f.write("Direct call targets (unique):\n\n")
        for x in { (c['target_rva'],c['name']) for c in r['calls'] }:
            f.write(f"- {x[0]} {x[1]}\n")
        f.write("\n")
checks=[{"rva":hex(rv),"name":name} for rv,name in sorted(exports.items()) if "checkLinkCondition" in name or "getCollision" in name or "getAttack" in name or "getDamaged" in name or "getHit" in name]
relevant=[{"rva":hex(rv),"name":name} for rv,name in sorted(exports.items()) if ("ObjectActionLinkCondition" in name or "SwitchVariable" in name or "getVariableValue" in name or "getVariableData" in name or "PlayerData" in name) and ("get" in name or "SwitchVariable" in name)]
(OUT/"STAGE79_VARIABLE_CONDITION_EXPORTS.json").write_text(json.dumps(relevant,indent=2,ensure_ascii=False),encoding="utf-8")
(OUT/"STAGE73_CONDITION_EXPORTS.json").write_text(json.dumps(checks,indent=2,ensure_ascii=False),encoding="utf-8")
print("STAGE73_NATIVE_AUDIT_PASS",len(reports))
