import pefile,hashlib,capstone
p=pefile.PE("cheats/endurance/input/player.exe",fast_load=True)
p.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for e in p.DIRECTORY_ENTRY_EXPORT.symbols:
 if not e.name:continue
 name=e.name.decode("utf-8","replace")
 if any(x in name for x in ("getScene@SceneLayer@","disappear@Object@","disappear@ObjectAction@","removeObject@SceneLayer@","getId@Object@","getObjectData@Object@","getLayerId@Object@","getPosition@Object@","getSceneLayer@Object@","getScene@GameManager@")):
  va=p.OPTIONAL_HEADER.ImageBase+e.address
  code=p.__data__[p.get_offset_from_rva(e.address):][:95]
  dis=[]
  for i in md.disasm(code,va):
   dis.append(i.mnemonic+" "+i.op_str)
   if len(dis)>=12 or i.mnemonic.startswith("ret"):break
  print("CLONE21_SYMBOL",hex(va),name," | ".join(dis))
