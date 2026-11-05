// Endurance 2047 - 32-bit VERSION.dll proxy for the canonical AGTK player.exe.
// Target: global AGTK Variable ID 2047 (temptation gauge), NOT HP/MP.
// Standalone test candidate; never modifies the game's project.json or player.exe.
// Windows 10+, x86 MSVC, static CRT. No downloading, networking or persistence.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <winver.h>
#include <tlhelp32.h>
#include <wincrypt.h>
#include <stdint.h>
#include <cstring>
#include <cstdio>
#pragma comment(lib, "Advapi32.lib")

static HMODULE g_self = nullptr;
static HMODULE g_originalVersion = nullptr;
static volatile LONG g_hookInstalled = 0;
static BYTE* g_originalMethod = nullptr;
static BYTE* g_trampoline = nullptr;
static BYTE* g_trampolineSet = nullptr;
static BYTE* g_trampolineRequest = nullptr;

static HMODULE RealVersionModule() {
    HMODULE already = reinterpret_cast<HMODULE>(
        InterlockedCompareExchangePointer(
            reinterpret_cast<void* volatile*>(&g_originalVersion),
            nullptr, nullptr));
    if (already) return already;
    WCHAR path[MAX_PATH] = {};
    const UINT len = GetSystemDirectoryW(path, MAX_PATH);
    if (len == 0 || len > MAX_PATH - 14) return nullptr;
    wcscat_s(path, L"\\version.dll");
    HMODULE loaded = LoadLibraryW(path);
    if (!loaded || loaded == g_self) return nullptr;
    HMODULE prior = reinterpret_cast<HMODULE>(
        InterlockedCompareExchangePointer(
            reinterpret_cast<void* volatile*>(&g_originalVersion),
            loaded, nullptr));
    if (prior) {
        FreeLibrary(loaded);
        return prior;
    }
    return loaded;
}
static FARPROC RealProc(const char* name) {
    HMODULE h = RealVersionModule();
    return h ? GetProcAddress(h, name) : nullptr;
}

extern "C" DWORD WINAPI Proxy_GetFileVersionInfoSizeW(LPCWSTR filename, LPDWORD handle) {
    typedef DWORD (WINAPI *Fn)(LPCWSTR, LPDWORD);
    Fn f = reinterpret_cast<Fn>(RealProc("GetFileVersionInfoSizeW"));
    if (!f) { SetLastError(ERROR_PROC_NOT_FOUND); return 0; }
    return f(filename, handle);
}
extern "C" BOOL WINAPI Proxy_GetFileVersionInfoW(LPCWSTR filename, DWORD handle, DWORD len, LPVOID data) {
    typedef BOOL (WINAPI *Fn)(LPCWSTR, DWORD, DWORD, LPVOID);
    Fn f = reinterpret_cast<Fn>(RealProc("GetFileVersionInfoW"));
    if (!f) { SetLastError(ERROR_PROC_NOT_FOUND); return FALSE; }
    return f(filename, handle, len, data);
}
extern "C" BOOL WINAPI Proxy_VerQueryValueW(LPCVOID block, LPCWSTR name, LPVOID* result, PUINT count) {
    typedef BOOL (WINAPI *Fn)(LPCVOID, LPCWSTR, LPVOID*, PUINT);
    Fn f = reinterpret_cast<Fn>(RealProc("VerQueryValueW"));
    if (!f) { SetLastError(ERROR_PROC_NOT_FOUND); return FALSE; }
    return f(block, name, result, count);
}

// Also forward common ANSI and Ex variants, for other game libraries if needed.
extern "C" DWORD WINAPI Proxy_GetFileVersionInfoSizeA(LPCSTR file, LPDWORD handle) {
    typedef DWORD (WINAPI *Fn)(LPCSTR,LPDWORD);
    Fn f=reinterpret_cast<Fn>(RealProc("GetFileVersionInfoSizeA"));
    if (!f) {SetLastError(ERROR_PROC_NOT_FOUND);return 0;}
    return f(file,handle);
}
extern "C" BOOL WINAPI Proxy_GetFileVersionInfoA(LPCSTR file,DWORD handle,DWORD size,LPVOID data) {
    typedef BOOL (WINAPI *Fn)(LPCSTR,DWORD,DWORD,LPVOID);
    Fn f=reinterpret_cast<Fn>(RealProc("GetFileVersionInfoA"));
    if (!f) {SetLastError(ERROR_PROC_NOT_FOUND);return FALSE;}
    return f(file,handle,size,data);
}
extern "C" BOOL WINAPI Proxy_VerQueryValueA(LPCVOID block,LPCSTR subblock,LPVOID* data,PUINT count) {
    typedef BOOL (WINAPI *Fn)(LPCVOID,LPCSTR,LPVOID*,PUINT);
    Fn f=reinterpret_cast<Fn>(RealProc("VerQueryValueA"));
    if (!f) {SetLastError(ERROR_PROC_NOT_FOUND);return FALSE;}
    return f(block,subblock,data,count);
}
extern "C" DWORD WINAPI Proxy_GetFileVersionInfoSizeExW(DWORD flags,LPCWSTR file,LPDWORD handle) {
    typedef DWORD (WINAPI *Fn)(DWORD,LPCWSTR,LPDWORD);
    Fn f=reinterpret_cast<Fn>(RealProc("GetFileVersionInfoSizeExW"));
    if (!f) {SetLastError(ERROR_PROC_NOT_FOUND);return 0;}
    return f(flags,file,handle);
}
extern "C" DWORD WINAPI Proxy_GetFileVersionInfoSizeExA(DWORD flags,LPCSTR file,LPDWORD handle) {
    typedef DWORD (WINAPI *Fn)(DWORD,LPCSTR,LPDWORD);
    Fn f=reinterpret_cast<Fn>(RealProc("GetFileVersionInfoSizeExA"));
    if (!f) {SetLastError(ERROR_PROC_NOT_FOUND);return 0;}
    return f(flags,file,handle);
}
extern "C" BOOL WINAPI Proxy_GetFileVersionInfoExW(DWORD flags,LPCWSTR file,DWORD handle,DWORD size,LPVOID data) {
    typedef BOOL (WINAPI *Fn)(DWORD,LPCWSTR,DWORD,DWORD,LPVOID);
    Fn f=reinterpret_cast<Fn>(RealProc("GetFileVersionInfoExW"));
    if (!f) {SetLastError(ERROR_PROC_NOT_FOUND);return FALSE;}
    return f(flags,file,handle,size,data);
}
extern "C" BOOL WINAPI Proxy_GetFileVersionInfoExA(DWORD flags,LPCSTR file,DWORD handle,DWORD size,LPVOID data) {
    typedef BOOL (WINAPI *Fn)(DWORD,LPCSTR,DWORD,DWORD,LPVOID);
    Fn f=reinterpret_cast<Fn>(RealProc("GetFileVersionInfoExA"));
    if (!f) {SetLastError(ERROR_PROC_NOT_FOUND);return FALSE;}
    return f(flags,file,handle,size,data);
}

static void Log(const char* message) {
    WCHAR path[MAX_PATH]={};
    DWORD length=GetModuleFileNameW(g_self,path,MAX_PATH);
    if (!length || length>=MAX_PATH-24) return;
    WCHAR* slash=wcsrchr(path,L'\\');
    if (!slash) return;
    wcscpy_s(slash+1, MAX_PATH-(slash+1-path), L"EnduranceWriters.log");
    HANDLE h=CreateFileW(path,FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,
                         OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if (h==INVALID_HANDLE_VALUE) return;
    DWORD written=0;
    WriteFile(h,message,static_cast<DWORD>(strlen(message)),&written,nullptr);
    WriteFile(h,"\r\n",2,&written,nullptr);
    CloseHandle(h);
}

static bool CanonicalExeMatch() {
    const BYTE wanted[32]={
        0x02,0xa5,0x9b,0xaa,0xb7,0xa4,0xc9,0x41,
        0xf9,0xa0,0x1f,0x48,0x50,0x82,0x39,0x6d,
        0x61,0xe7,0x50,0xa4,0x1d,0xc9,0x55,0xcf,
        0xf8,0x95,0xbe,0xf5,0x39,0x54,0x41,0xea
    };
    WCHAR path[MAX_PATH]={};
    if (!GetModuleFileNameW(nullptr,path,MAX_PATH)) return false;
    const WCHAR* basename=wcsrchr(path,L'\\');
    basename=basename ? basename+1 : path;
    if (_wcsicmp(basename,L"player.exe")!=0) return false;
    HANDLE h=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
                         nullptr,OPEN_EXISTING,FILE_FLAG_SEQUENTIAL_SCAN,nullptr);
    if (h==INVALID_HANDLE_VALUE) return false;
    LARGE_INTEGER size={};
    if (!GetFileSizeEx(h,&size) || size.QuadPart!=8757760) {CloseHandle(h);return false;}
    HCRYPTPROV prov=0;
    HCRYPTHASH hash=0;
    bool ok=false;
    if (CryptAcquireContextW(&prov,nullptr,nullptr,PROV_RSA_AES,CRYPT_VERIFYCONTEXT) &&
        CryptCreateHash(prov,CALG_SHA_256,0,0,&hash)) {
        BYTE chunk[32768]={};
        DWORD count=0;
        bool good=true;
        while(ReadFile(h,chunk,sizeof(chunk),&count,nullptr) && count>0) {
            if (!CryptHashData(hash,chunk,count,0)) {good=false;break;}
        }
        if (good) {
            BYTE digest[32]={};
            DWORD len=sizeof(digest);
            if (CryptGetHashParam(hash,HP_HASHVAL,digest,&len,0) &&
                len==sizeof(digest) && memcmp(digest,wanted,sizeof(digest))==0) {
                ok=true;
            }
        }
    }
    if(hash) CryptDestroyHash(hash);
    if(prov) CryptReleaseContext(prov,0);
    CloseHandle(h);
    return ok;
}

// AGTK PlayVariableData: observed ID at +0x18, value at +0x28,
// owner object pointer at +0x60. These were established by canonical PE disassembly.
typedef double (__thiscall *SetValueOriginal)(void*,double);
typedef void (__thiscall *RequestValueOriginal)(void*,double,float);

static volatile LONG g_totalSet=0,g_totalRequest=0;
static volatile LONG g_set2047=0,g_request2047=0;
static volatile LONG g_set2003=0,g_request2003=0;
static volatile LONG g_set2386=0,g_request2386=0;
static volatile LONG g_set2054=0,g_request2054=0;
static volatile LONG g_setOther=0,g_requestOther=0;
static volatile LONG g_set2047Global=0,g_request2047Global=0;
static volatile LONG g_set2047Object=0,g_request2047Object=0;

static void RecordValue(bool isSet,void* variable,double value) {
    volatile LONG* counter=nullptr;
    uint32_t id=0xffffffff;
    bool hasObject=false;
    if(variable){
        BYTE* p=static_cast<BYTE*>(variable);
        id=*reinterpret_cast<uint32_t*>(p+0x18);
        hasObject=(*reinterpret_cast<void**>(p+0x60)!=nullptr);
    }
    switch(id){
      case 2047:counter=isSet?&g_set2047:&g_request2047;break;
      case 2003:counter=isSet?&g_set2003:&g_request2003;break;
      case 2386:counter=isSet?&g_set2386:&g_request2386;break;
      case 2054:counter=isSet?&g_set2054:&g_request2054;break;
      default:counter=isSet?&g_setOther:&g_requestOther;break;
    }
    LONG hits=InterlockedIncrement(counter);
    if(id==2047){
        InterlockedIncrement(isSet?
             (hasObject?&g_set2047Object:&g_set2047Global):
             (hasObject?&g_request2047Object:&g_request2047Global));
    }
    if(hits<=2){
        char line[220]={};
        sprintf_s(line,sizeof(line),"FIRST_%s id=%lu object=%u input=%.4f",
          isSet?"SET":"REQUEST",static_cast<unsigned long>(id),hasObject?1u:0u,value);
        Log(line);
    }
}

// No changes to the original arguments/return value.
// The setValue method RETURNS double on x86/x87, requestValue returns void.
static double __fastcall InterceptSetValue(void* variable,void* /*edx*/,double value){
    SetValueOriginal original=reinterpret_cast<SetValueOriginal>(g_trampolineSet);
    if(!original)return value;
    InterlockedIncrement(&g_totalSet);
    RecordValue(true,variable,value);
    return original(variable,value);
}
static void __fastcall InterceptRequestValue(void* variable,void* /*edx*/,
                                              double value,float seconds){
    RequestValueOriginal original=reinterpret_cast<RequestValueOriginal>(g_trampolineRequest);
    if(!original)return;
    InterlockedIncrement(&g_totalRequest);
    RecordValue(false,variable,value);
    original(variable,value,seconds);
}
static DWORD WINAPI ReportCounters(LPVOID){
    LONG prevSet=-1,prevRequest=-1;
    while(true){
        Sleep(2500);
        LONG ns=InterlockedCompareExchange(&g_totalSet,0,0);
        LONG nr=InterlockedCompareExchange(&g_totalRequest,0,0);
        if(ns==prevSet&&nr==prevRequest)continue;
        prevSet=ns;prevRequest=nr;
        char line[360]={};
        sprintf_s(line,sizeof(line),
          "COUNTERS set=%ld request=%ld set2047=%ld request2047=%ld set2003=%ld request2003=%ld set2386=%ld request2386=%ld set2054=%ld request2054=%ld setOther=%ld requestOther=%ld set2047Global=%ld set2047Object=%ld request2047Global=%ld request2047Object=%ld",
          ns,nr,InterlockedCompareExchange(&g_set2047,0,0),
          InterlockedCompareExchange(&g_request2047,0,0),
          InterlockedCompareExchange(&g_set2003,0,0),
          InterlockedCompareExchange(&g_request2003,0,0),
          InterlockedCompareExchange(&g_set2386,0,0),
          InterlockedCompareExchange(&g_request2386,0,0),
          InterlockedCompareExchange(&g_set2054,0,0),
          InterlockedCompareExchange(&g_request2054,0,0),
          InterlockedCompareExchange(&g_setOther,0,0),
          InterlockedCompareExchange(&g_requestOther,0,0),
          InterlockedCompareExchange(&g_set2047Global,0,0),
          InterlockedCompareExchange(&g_set2047Object,0,0),
          InterlockedCompareExchange(&g_request2047Global,0,0),
          InterlockedCompareExchange(&g_request2047Object,0,0));
        Log(line);
    }
    return 0;
}
static void WriteAbsoluteJump(BYTE* p,const void* target){
    p[0]=0x68;
    *reinterpret_cast<uint32_t*>(p+1)=reinterpret_cast<uint32_t>(target);
    p[5]=0xC3;
}
static bool InstallHook(const char* label,DWORD rva,const BYTE* expected,
                        SIZE_T preimageSize,const void* hook,BYTE** trampOut){
    if(preimageSize<6||preimageSize>16)return false;
    BYTE* exe=reinterpret_cast<BYTE*>(GetModuleHandleW(nullptr));
    if(!exe)return false;
    BYTE* method=exe+rva;
    if(memcmp(method,expected,preimageSize)!=0){
        char line[120]={};
        sprintf_s(line,sizeof(line),"HOOK_REFUSED %s: prologue mismatch",label);
        Log(line);return false;
    }
    BYTE* trampoline=static_cast<BYTE*>(
        VirtualAlloc(nullptr,preimageSize+6,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    if(!trampoline)return false;
    memcpy(trampoline,method,preimageSize);
    WriteAbsoluteJump(trampoline+preimageSize,method+preimageSize);
    DWORD old=0;
    if(!VirtualProtect(trampoline,preimageSize+6,PAGE_EXECUTE_READ,&old)){
        VirtualFree(trampoline,0,MEM_RELEASE);return false;
    }
    HANDLE suspended[256]={};
    DWORD n=0;
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);
    if(snapshot==INVALID_HANDLE_VALUE){
        VirtualFree(trampoline,0,MEM_RELEASE);return false;
    }
    THREADENTRY32 t={};
    t.dwSize=sizeof(t);
    DWORD tid=GetCurrentThreadId(),pid=GetCurrentProcessId();
    bool safe=Thread32First(snapshot,&t)!=FALSE;
    if(safe)do{
        if(t.th32OwnerProcessID!=pid||t.th32ThreadID==tid)continue;
        if(n>=256){safe=false;break;}
        HANDLE h=OpenThread(THREAD_SUSPEND_RESUME,FALSE,t.th32ThreadID);
        if(!h){safe=false;break;}
        if(SuspendThread(h)==static_cast<DWORD>(-1)){CloseHandle(h);safe=false;break;}
        suspended[n++]=h;
    }while(Thread32Next(snapshot,&t));
    CloseHandle(snapshot);
    bool installed=false;
    if(safe){
        DWORD originalProtect=0;
        if(VirtualProtect(method,preimageSize,PAGE_EXECUTE_READWRITE,&originalProtect)){
            *trampOut=trampoline;
            MemoryBarrier();
            WriteAbsoluteJump(method,hook);
            if(preimageSize>6)memset(method+6,0x90,preimageSize-6);
            FlushInstructionCache(GetCurrentProcess(),method,preimageSize);
            DWORD ignored=0;
            VirtualProtect(method,preimageSize,originalProtect,&ignored);
            installed=true;
        }
    }
    for(DWORD i=n;i>0;--i){
        ResumeThread(suspended[i-1]);
        CloseHandle(suspended[i-1]);
    }
    if(!installed){
        *trampOut=nullptr;
        VirtualFree(trampoline,0,MEM_RELEASE);
        return false;
    }
    InterlockedIncrement(&g_hookInstalled);
    char line[128]={};
    sprintf_s(line,sizeof(line),"HOOK_INSTALLED %s RVA=0x%lx (read-only)",label,
              static_cast<unsigned long>(rva));
    Log(line);
    return true;
}
static DWORD WINAPI Startup(LPVOID) {
    if(sizeof(void*)!=4) {Log("ABORT: x86 DLL required.");return 0;}
    if(!CanonicalExeMatch()) {
        Log("GUARD_FAIL: player.exe size or SHA256 not canonical. DLL forwarding active; no hook.");
        return 0;
    }
    Log("SOURCE_OK: canonical player.exe SHA256 confirmed.");
    const BYTE setPrologue[6]={0x55,0x8b,0xec,0x83,0xe4,0xf8};
    const BYTE reqPrologue[8]={0x55,0x8b,0xec,0xf2,0x0f,0x10,0x45,0x08};
    bool setOk=InstallHook("PlayVariableData::setValue",0x6ab90,
                          setPrologue,sizeof(setPrologue),
                          reinterpret_cast<const void*>(&InterceptSetValue),
                          &g_trampolineSet);
    bool reqOk=InstallHook("PlayVariableData::requestValue",0x6acb0,
                          reqPrologue,sizeof(reqPrologue),
                          reinterpret_cast<const void*>(&InterceptRequestValue),
                          &g_trampolineRequest);
    if(setOk||reqOk){
        Log("DIAGNOSTIC_ONLY: no variable value, operator, or project file is changed.");
        Log("COUNTERS set=0 request=0 set2047=0 request2047=0");
        HANDLE h=CreateThread(nullptr,0,ReportCounters,nullptr,0,nullptr);
        if(h)CloseHandle(h);
        else Log("WARNING: periodic counters thread unavailable.");
    }else Log("HOOK_FAILED: neither write path installed.");
    return 0;
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID) {
    if(reason==DLL_PROCESS_ATTACH) {
        g_self=instance;
        DisableThreadLibraryCalls(instance);
        // Never wait in DllMain: the worker starts after the loader lock is released.
        HANDLE worker=CreateThread(nullptr,0,Startup,nullptr,0,nullptr);
        if(worker)CloseHandle(worker);
    }
    return TRUE;
}
