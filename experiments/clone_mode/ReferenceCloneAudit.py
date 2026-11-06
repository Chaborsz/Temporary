# -*- coding: utf-8 -*-
# @category CloneReference
# Ghidra headless, read-only native symbol/function audit.
# Uses the Ghidra built-in Jython interpreter; no external Python modules.
from java.lang import System

print("REFERENCE_GHIDRA_START")
print("PROGRAM=" + str(currentProgram.getName()))
print("IMAGE_BASE=" + str(currentProgram.getImageBase()))
needles = ("clone","copy","duplicate","player","target","damag","hp","collision",
           "createobject","objectcreate","getobject","action","instance",
           "attack","spawn","projectile","switchvariable","hit","summon")
count=0
for function in currentProgram.getFunctionManager().getFunctions(True):
    name = str(function.getName())
    low=name.lower()
    if not any(x in low for x in needles):
        continue
    addr=str(function.getEntryPoint())
    print("REFERENCE_GHIDRA_FUNCTION " + addr + " " + name[:230])
    count+=1
    if count>=500:
        print("REFERENCE_GHIDRA_TRUNCATED")
        break
print("REFERENCE_GHIDRA_MATCHED_FUNCTIONS=" + str(count))
print("REFERENCE_GHIDRA_END")
