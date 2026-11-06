#!/usr/bin/env python3
"""Stage42 read-only: identify AGTK script/command victim-side event executors.
Observed Stage41 CALLER=0x1E604E is GameManager::getSwitchVariableDataList.
"""
import hashlib,pefile,capstone,bisect
from pathlib import Path
p=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(p.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
exe=pefile.PE(str(p),fast_load=True)
exe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
b=exe.OPTIONAL_HEADER.ImageBase
names={b+o.address:o.name.decode("utf8","replace") for o in exe.DIRECTORY_ENTRY_EXPORT.symbols if o.name}
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
targetNames=[
"execActionScriptEvaluate@ObjectAction@",
"execActionCustom@ObjectAction@",
"execActionSwitchVariableChange@ObjectAction@",
"execActionObjectChange@ObjectAction@",
"execActionActionExec@ObjectAction@",
"execActionObjectLock@ObjectAction@",
"execActionObjectMove@ObjectAction@",
"execActionObjectFilterEffect@ObjectAction@",
"execActionAttackSetting@ObjectAction@",
"execActionDatabaseReflect@ObjectAction@",
"calcSwichVariableChange@GameManager@",
"calcObjectActionProgram@GameManager@",
"getSwitchVariableDataList@GameManager@",
"getTargetObjectListByObjectId@GameManager@",
"getObjectPlayer@Scene@",
"getObject@ObjectAction@",
"getObject@Object@",
"getObjectId@Object@",
"getObjectAction@Object@",
"getObjectAction@",
"getObjectData@Object@",
"getObjectInstanceId@",
]
targets={a:n for a,n in names.items() if any(x in n for x in targetNames)}
for a,n in targets.items():
 print("S42_METHOD",hex(a),n[:220])
 code=exe.__data__[exe.get_offset_from_rva(a-b):][:580]
 ins=list(md.disasm(code,a))
 if "getObject" in n or "getTargetObjectList" in n:
  limit=25
 else:limit=115
 for i in range(0,min(len(ins),limit),22):
  print("S42_BODY",hex(a),i," | ".join(f"{hex(x.address)} {x.mnemonic} {x.op_str}" for x in ins[i:i+22])[:3300])
# Analyze exact observed target lookup's caller 0x1e604e
va=0x5e5ff0
code=exe.__data__[exe.get_offset_from_rva(va-b):][:260]
print("S42_VARIABLE_CALLER_BODY"," | ".join(f"{hex(x.address)} {x.mnemonic} {x.op_str}" for x in md.disasm(code,va))[:9500])
print("S42_STATIC_PASS",len(targets))
