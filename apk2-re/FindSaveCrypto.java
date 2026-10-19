// Ghidra headless post-script for APK2 save crypto reverse engineering.
// Finds save-system strings/imports, follows references, and decompiles caller functions.

import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class FindSaveCrypto extends GhidraScript {
    private final Set<Address> emittedFunctions = new LinkedHashSet<>();
    private DecompInterface decomp;

    private final String[] TARGET_STRINGS = new String[] {
        "%sSaveGames/%s.sav",
        "SaveGames/",
        "SaveGamePipe",
        "SaveGameSystem.cpp(18)",
        "SaveGameSystem.cpp(45)",
        "SaveGameSystem.cpp(72)",
        "SaveGameSystem.cpp(100)",
        "SaveGameSystem.cpp(124)",
        "UAPKGameSaveDataHandler",
        "UAPKGameSaveDataVersionHandler",
        "UAPKGameSaveDataDebugMenu",
        "UAPKSaveDataDebugMenu",
        "UAPKSavedataDebugMenu",
        "APKSaveDataHierarchy_Parent",
        "RootSaveDirs",
        "GVAS",
        "DefaultData"
    };

    private final String[] TARGET_SYMBOLS = new String[] {
        "CryptDecrypt", "CryptCreateHash", "CryptSetHashParam", "CryptGetUserKey",
        "CryptExportKey", "BCryptGenRandom", "CreateFileW", "CreateFileA",
        "ReadFile", "WriteFile", "GetFileSizeEx", "SetFilePointer",
        "MoveFileW", "MoveFileA", "DeleteFileW", "DeleteFileA"
    };

    @Override
    public void run() throws Exception {
        println("PROGRAM=" + currentProgram.getName());
        println("IMAGE_BASE=" + currentProgram.getImageBase());
        println("LANG=" + currentProgram.getLanguageID());

        decomp = new DecompInterface();
        decomp.toggleCCode(true);
        decomp.toggleSyntaxTree(true);
        decomp.setSimplificationStyle("decompile");
        decomp.openProgram(currentProgram);

        for (String s : TARGET_STRINGS) {
            if (monitor.isCancelled()) break;
            findAsciiAndUtf16(s);
        }

        SymbolTable st = currentProgram.getSymbolTable();
        for (String name : TARGET_SYMBOLS) {
            if (monitor.isCancelled()) break;
            println("\n=== SYMBOL TARGET: " + name + " ===");
            SymbolIterator it = st.getSymbols(name);
            boolean any = false;
            while (it.hasNext()) {
                any = true;
                Symbol sym = it.next();
                Address a = sym.getAddress();
                println("SYMBOL " + sym.getName(true) + " @ " + a + " type=" + sym.getSymbolType());
                refsTo(a, "symbol:" + name);
            }
            if (!any) println("NO_SYMBOL " + name);
        }

        println("\n=== DECOMPILED FUNCTIONS TOTAL=" + emittedFunctions.size() + " ===");
    }

    private void findAsciiAndUtf16(String s) throws Exception {
        println("\n=== STRING TARGET: " + s + " ===");
        byte[] ascii = s.getBytes(StandardCharsets.UTF_8);
        byte[] utf16 = (s + "\0").getBytes(StandardCharsets.UTF_16LE);
        scanPattern(ascii, "ASCII", s);
        scanPattern(utf16, "UTF16LE", s);
    }

    private void scanPattern(byte[] pattern, String kind, String label) throws Exception {
        Memory mem = currentProgram.getMemory();
        Address start = mem.getMinAddress();
        int hits = 0;
        while (start != null && hits < 64 && !monitor.isCancelled()) {
            Address hit = mem.findBytes(start, pattern, null, true, monitor);
            if (hit == null) break;
            println(kind + " HIT " + label + " @ " + hit);
            refsTo(hit, "string:" + label);
            hits++;
            try { start = hit.add(1); } catch (AddressOutOfBoundsException e) { break; }
        }
        if (hits == 0) println(kind + " NO_HIT " + label);
    }

    private void refsTo(Address target, String why) {
        ReferenceManager rm = currentProgram.getReferenceManager();
        ReferenceIterator refs = rm.getReferencesTo(target);
        int n = 0;
        while (refs.hasNext() && n < 256 && !monitor.isCancelled()) {
            Reference r = refs.next();
            Address from = r.getFromAddress();
            println("REF " + why + " from=" + from + " type=" + r.getReferenceType());
            emitFunction(from, why);
            n++;
        }
        println("REF_COUNT " + why + " target=" + target + " count=" + n);
    }

    private void emitFunction(Address from, String why) {
        FunctionManager fm = currentProgram.getFunctionManager();
        Function f = fm.getFunctionContaining(from);
        if (f == null) f = fm.getFunctionAt(from);
        if (f == null) {
            println("NO_FUNCTION from=" + from + " why=" + why);
            return;
        }
        Address ep = f.getEntryPoint();
        println("FUNCTION_REF why=" + why + " entry=" + ep + " name=" + f.getName(true) + " size=" + f.getBody().getNumAddresses());
        if (!emittedFunctions.add(ep)) return;
        try {
            DecompileResults res = decomp.decompileFunction(f, 120, monitor);
            println("\n----- DECOMPILE BEGIN " + ep + " " + f.getName(true) + " -----");
            if (res != null && res.decompileCompleted() && res.getDecompiledFunction() != null) {
                println(res.getDecompiledFunction().getC());
            } else {
                println("DECOMPILE_FAILED " + (res == null ? "null" : res.getErrorMessage()));
            }
            println("----- DECOMPILE END " + ep + " -----\n");
        } catch (Throwable t) {
            println("DECOMPILE_EXCEPTION " + ep + " " + t);
        }
    }
}
