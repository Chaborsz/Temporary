// ShironoYakata DEMO native multi-clone proxy.
// Experimental build; exact executable fingerprint required before patching.
// Uses the game's own agtk::Object::execActionObjectCreate (x86 thiscall).
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winver.h>
#include <wincrypt.h>
#include <cstdio>
#include <cstring>
#include <cwchar>
#include "clone_policy.h"

#pragma comment(lib, "advapi32.lib")

namespace {
HMODULE g_self = nullptr;
HMODULE g_realVersion = nullptr;
using NativeCreate = void (__thiscall *)(void* owner, void* command);
NativeCreate g_nativeCreate = nullptr;
void* g_trampoline = nullptr;
int g_extraClones = 2;
volatile LONG g_cloneCommands = 0;
wchar_t g_logPath[MAX_PATH] = {};
wchar_t g_configPath[MAX_PATH] = {};

void Log(const char* message) {
    if (!g_logPath[0]) return;
    HANDLE h = CreateFileW(g_logPath, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE,
                           nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) return;
    DWORD written = 0;
    WriteFile(h, message, static_cast<DWORD>(strlen(message)), &written, nullptr);
    WriteFile(h, "\r\n", 2, &written, nullptr);
    CloseHandle(h);
}

bool BuildSiblingPath(const wchar_t* filename, wchar_t* output, DWORD cap) {
    DWORD n = GetModuleFileNameW(nullptr, output, cap);
    if (n == 0 || n >= cap) return false;
    wchar_t* slash = wcsrchr(output, L'\\');
    if (!slash) return false;
    *(slash + 1) = L'\0';
    return wcscat_s(output, cap, filename) == 0;
}

HMODULE GetRealVersion() {
    HMODULE existing = static_cast<HMODULE>(
        InterlockedCompareExchangePointer(reinterpret_cast<void* volatile*>(&g_realVersion), nullptr, nullptr));
    if (existing) return existing;
    wchar_t path[MAX_PATH] = {};
    const UINT n = GetSystemDirectoryW(path, MAX_PATH);
    if (!n || n >= MAX_PATH) return nullptr;
    if (wcscat_s(path, MAX_PATH, L"\\version.dll") != 0) return nullptr;
    HMODULE loaded = LoadLibraryW(path);
    if (!loaded) return nullptr;
    HMODULE prior = static_cast<HMODULE>(InterlockedCompareExchangePointer(
        reinterpret_cast<void* volatile*>(&g_realVersion), loaded, nullptr));
    if (prior) {
        FreeLibrary(loaded);
        return prior;
    }
    return loaded;
}

template<typename Func>
Func Real(const char* name) {
    HMODULE lib = GetRealVersion();
    return lib ? reinterpret_cast<Func>(GetProcAddress(lib, name)) : nullptr;
}

bool MatchExeHash() {
    wchar_t filename[MAX_PATH] = {};
    const DWORD n = GetModuleFileNameW(nullptr, filename, MAX_PATH);
    if (!n || n >= MAX_PATH) return false;
    HANDLE file = CreateFileW(filename, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
                              nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) return false;
    HCRYPTPROV provider = 0;
    HCRYPTHASH hash = 0;
    bool match = false;
    if (CryptAcquireContextW(&provider, nullptr, nullptr, PROV_RSA_AES, CRYPT_VERIFYCONTEXT) &&
        CryptCreateHash(provider, CALG_SHA_256, 0, 0, &hash)) {
        BYTE bytes[65536];
        DWORD read = 0;
        bool good = true;
        while (ReadFile(file, bytes, sizeof(bytes), &read, nullptr) && read) {
            if (!CryptHashData(hash, bytes, read, 0)) {good = false; break;}
        }
        if (GetLastError() != ERROR_SUCCESS && read != 0) good = false;
        BYTE digest[32] = {};
        DWORD digestSize = sizeof(digest);
        if (good && CryptGetHashParam(hash, HP_HASHVAL, digest, &digestSize, 0) &&
            digestSize == sizeof(digest)) {
            char actual[65] = {};
            static constexpr char hex[] = "0123456789abcdef";
            for (unsigned i = 0; i < 32; ++i) {
                actual[i * 2] = hex[digest[i] >> 4];
                actual[i * 2 + 1] = hex[digest[i] & 15];
            }
            match = strcmp(actual, shirono::kExpectedExeSha256) == 0;
        }
    }
    if (hash) CryptDestroyHash(hash);
    if (provider) CryptReleaseContext(provider, 0);
    CloseHandle(file);
    return match;
}

int GetCreateObjectId(void* command) {
    if (!command) return -1;
    __try {
        void** vtable = *reinterpret_cast<void***>(command);
        if (!vtable) return -1;
        using GetObjectId = int(__thiscall*)(void*);
        GetObjectId getter = reinterpret_cast<GetObjectId>(vtable[0x28 / sizeof(void*)]);
        return getter ? getter(command) : -1;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return -1;
    }
}

void __fastcall HookCreate(void* owner, void* /*edx*/, void* command) {
    NativeCreate original = g_nativeCreate;
    if (!original) return;
    const int objectId = GetCreateObjectId(command);
    original(owner, command);
    const int extras = shirono::ExtraSpawnsFor(objectId, g_extraClones);
    if (!extras) return;
    for (int i = 0; i < extras; ++i) {
        original(owner, command);
    }
    const LONG count = InterlockedIncrement(&g_cloneCommands);
    if (count <= 4) {
        char message[128] = {};
        sprintf_s(message, "NATIVE_CLONE_COMMAND id=19 copies=%d sequence=%ld", 1+extras, count);
        Log(message);
    }
}

bool InstallHook() {
    HMODULE exe = GetModuleHandleW(nullptr);
    if (!exe) return false;
    BYTE* target = reinterpret_cast<BYTE*>(exe) + shirono::kObjectCreateRva;
    if (memcmp(target, shirono::kOriginalPrologue, sizeof(shirono::kOriginalPrologue)) != 0) {
        Log("HOOK_ABORT: method preimage mismatch");
        return false;
    }
    constexpr SIZE_T patchLength = sizeof(shirono::kOriginalPrologue);
    BYTE* gateway = reinterpret_cast<BYTE*>(VirtualAlloc(nullptr, 64,
          MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE));
    if (!gateway) {
        Log("HOOK_ABORT: trampoline allocation failure");
        return false;
    }
    memcpy(gateway, target, patchLength);
    gateway[patchLength] = 0xE9;
    const auto jumpBack = reinterpret_cast<intptr_t>(target + patchLength) -
                          reinterpret_cast<intptr_t>(gateway + patchLength + 5);
    *reinterpret_cast<int32_t*>(gateway + patchLength + 1) = static_cast<int32_t>(jumpBack);
    FlushInstructionCache(GetCurrentProcess(), gateway, patchLength + 5);
    g_trampoline = gateway;
    g_nativeCreate = reinterpret_cast<NativeCreate>(gateway);

    DWORD oldProtect = 0;
    if (!VirtualProtect(target, patchLength, PAGE_EXECUTE_READWRITE, &oldProtect)) {
        g_nativeCreate = nullptr;
        g_trampoline = nullptr;
        VirtualFree(gateway, 0, MEM_RELEASE);
        Log("HOOK_ABORT: unable to change target page permissions");
        return false;
    }
    target[0] = 0xE9;
    const auto offset = reinterpret_cast<intptr_t>(&HookCreate) -
                        reinterpret_cast<intptr_t>(target + 5);
    *reinterpret_cast<int32_t*>(target + 1) = static_cast<int32_t>(offset);
    FlushInstructionCache(GetCurrentProcess(), target, patchLength);
    DWORD ignored = 0;
    VirtualProtect(target, patchLength, oldProtect, &ignored);
    Log("HOOK_READY: native object-create calls intercepted only for clone object ID 19");
    return true;
}

DWORD WINAPI Bootstrap(LPVOID) {
    if (!BuildSiblingPath(L"ShironoMulticlone.log", g_logPath, MAX_PATH) ||
        !BuildSiblingPath(L"ShironoMulticlone.ini", g_configPath, MAX_PATH)) return 1;
    Log("SHIRONO_MULTICLONE experimental v0.1 x86");
    if (!MatchExeHash()) {
        Log("HOOK_DISABLED: player.exe SHA-256 is not the analyzed release");
        return 2;
    }
    Log("EXE_SHA256_MATCH: verified exact DEMO binary");
    const int value = GetPrivateProfileIntW(L"ShironoMulticlone", L"ExtraClones", 2, g_configPath);
    if (value < 0 || value > 6) {
        Log("HOOK_DISABLED: ExtraClones must be between 0 and 6");
        return 3;
    }
    g_extraClones = value;
    if (value == 0) {
        Log("HOOK_DISABLED: ExtraClones=0");
        return 0;
    }
    return InstallHook() ? 0 : 4;
}
}

extern "C" {

DWORD WINAPI Proxy_GetFileVersionInfoSizeW(LPCWSTR name, LPDWORD handle) {
    using Fn = DWORD(WINAPI*)(LPCWSTR, LPDWORD);
    Fn f=Real<Fn>("GetFileVersionInfoSizeW");
    if (f) return f(name,handle);
    SetLastError(ERROR_PROC_NOT_FOUND);return 0;
}
BOOL WINAPI Proxy_GetFileVersionInfoW(LPCWSTR name,DWORD h,DWORD sz,LPVOID data) {
    using Fn=BOOL(WINAPI*)(LPCWSTR,DWORD,DWORD,LPVOID);
    Fn f=Real<Fn>("GetFileVersionInfoW");
    if(f)return f(name,h,sz,data);
    SetLastError(ERROR_PROC_NOT_FOUND);return FALSE;
}
BOOL WINAPI Proxy_VerQueryValueW(LPCVOID block,LPCWSTR sub,LPVOID* buf,PUINT len) {
    using Fn=BOOL(WINAPI*)(LPCVOID,LPCWSTR,LPVOID*,PUINT);
    Fn f=Real<Fn>("VerQueryValueW");
    if(f)return f(block,sub,buf,len);
    SetLastError(ERROR_PROC_NOT_FOUND);return FALSE;
}
DWORD WINAPI Proxy_GetFileVersionInfoSizeA(LPCSTR name,LPDWORD handle) {
    using Fn=DWORD(WINAPI*)(LPCSTR,LPDWORD);
    Fn f=Real<Fn>("GetFileVersionInfoSizeA");
    if(f)return f(name,handle);
    SetLastError(ERROR_PROC_NOT_FOUND);return 0;
}
BOOL WINAPI Proxy_GetFileVersionInfoA(LPCSTR name,DWORD h,DWORD sz,LPVOID data) {
    using Fn=BOOL(WINAPI*)(LPCSTR,DWORD,DWORD,LPVOID);
    Fn f=Real<Fn>("GetFileVersionInfoA");
    if(f)return f(name,h,sz,data);
    SetLastError(ERROR_PROC_NOT_FOUND);return FALSE;
}
BOOL WINAPI Proxy_VerQueryValueA(LPCVOID block,LPCSTR sub,LPVOID* buf,PUINT len) {
    using Fn=BOOL(WINAPI*)(LPCVOID,LPCSTR,LPVOID*,PUINT);
    Fn f=Real<Fn>("VerQueryValueA");
    if(f)return f(block,sub,buf,len);
    SetLastError(ERROR_PROC_NOT_FOUND);return FALSE;
}
DWORD WINAPI Proxy_GetFileVersionInfoSizeExW(DWORD flags,LPCWSTR name,LPDWORD handle) {
    using Fn=DWORD(WINAPI*)(DWORD,LPCWSTR,LPDWORD);
    Fn f=Real<Fn>("GetFileVersionInfoSizeExW");
    if(f)return f(flags,name,handle);
    SetLastError(ERROR_PROC_NOT_FOUND);return 0;
}
DWORD WINAPI Proxy_GetFileVersionInfoSizeExA(DWORD flags,LPCSTR name,LPDWORD handle) {
    using Fn=DWORD(WINAPI*)(DWORD,LPCSTR,LPDWORD);
    Fn f=Real<Fn>("GetFileVersionInfoSizeExA");
    if(f)return f(flags,name,handle);
    SetLastError(ERROR_PROC_NOT_FOUND);return 0;
}
BOOL WINAPI Proxy_GetFileVersionInfoExW(DWORD flags,LPCWSTR name,DWORD h,DWORD sz,LPVOID data) {
    using Fn=BOOL(WINAPI*)(DWORD,LPCWSTR,DWORD,DWORD,LPVOID);
    Fn f=Real<Fn>("GetFileVersionInfoExW");
    if(f)return f(flags,name,h,sz,data);
    SetLastError(ERROR_PROC_NOT_FOUND);return FALSE;
}
BOOL WINAPI Proxy_GetFileVersionInfoExA(DWORD flags,LPCSTR name,DWORD h,DWORD sz,LPVOID data) {
    using Fn=BOOL(WINAPI*)(DWORD,LPCSTR,DWORD,DWORD,LPVOID);
    Fn f=Real<Fn>("GetFileVersionInfoExA");
    if(f)return f(flags,name,h,sz,data);
    SetLastError(ERROR_PROC_NOT_FOUND);return FALSE;
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID) {
    if (reason==DLL_PROCESS_ATTACH) {
        g_self = module;
        HANDLE thread = CreateThread(nullptr,0,&Bootstrap,nullptr,0,nullptr);
        if (thread) CloseHandle(thread);
    }
    return TRUE;
}
}
