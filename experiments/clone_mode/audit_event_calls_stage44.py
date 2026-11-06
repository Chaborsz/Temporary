#!/usr/bin/env python3
"""Stage44: static correlate observed EVENT_ACTION call-site RVAs, hook relocations and event script routing."""
from pathlib import Path
import hashlib,pefile,capstone,bisect,struct
p=Path("cheats/endurance/input/player.exe")
assert hashlib.sha256(p.read_bytes()).hexdigest()=="02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea"
pe=pefile.PE(str(p),fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"],pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_BASERELOC"]])
b=pe.OPTIONAL_HEADER.ImageBase
syms=sorted((b+e.address,e.name.decode("utf-8","replace")) for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name)
addrs=[a for a,n in syms]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for rva in (0x1533a7,0x147087,0x14725e,0x153826,0x13e691):
 va=b+rva
 i=bisect.bisect_right(addrs,va)-1
 print("S44_CALLSITE",hex(rva),hex(va),"owner",hex(syms[i][0]),syms[i][1],"distance",hex(va-syms[i][0]))
 for _,name in syms[max(0,i-2):i+4]:print("S44_NEAR",name[:160])
 raw=pe.__data__[pe.get_offset_from_rva(va-54):][:135]
 ins=list(md.disasm(raw,va-54))
 print("S44_SITE_DISASM",hex(rva)," | ".join(f"{hex(x.address)} {x.mnemonic} {x.op_str}" for x in ins)[:4800])
reloc={entry.rva for blk in getattr(pe,"DIRECTORY_ENTRY_BASERELOC",[])
       for entry in blk.entries if entry.type==pefile.RELOCATION_TYPE["IMAGE_REL_BASED_HIGHLOW"]}
for va in (0x549980,0x546470):
 rva=va-b
 data=pe.__data__[pe.get_offset_from_rva(rva):][:30]
 imm=struct.unpack_from("<I",data,6)[0]
 print("S44_RELOCATION",hex(va),"entry",data.hex(),"embedded_va",hex(imm),"immediate_rva",hex(imm-b),"fixup_at",hex(rva+6),"has_fixup",rva+6 in reloc)
 print("S44_ENTRY_INSTRUCTIONS"," | ".join(f"{i.mnemonic} {i.op_str}" for i in md.disasm(data,va))[:700])
print("S44_RELOCATION_TOTAL",len(reloc))
print("STAGE44_CALLSITE_AUDIT_PASS")
