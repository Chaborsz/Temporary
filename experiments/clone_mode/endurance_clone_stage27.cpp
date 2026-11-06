// Endurance Stage27 + independent clone mode — guarded x86 VERSION.dll proxy.
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
#include <cmath>
#pragma comment(lib, "User32.lib")
#pragma comment(lib, "Advapi32.lib")

static HMODULE g_self = nullptr;
static HMODULE g_originalVersion = nullptr;
static volatile LONG g_hookInstalled = 0;
static BYTE* g_originalMethod = nullptr;
static BYTE* g_trampoline = nullptr;
static BYTE* g_trampolineSet = nullptr;
static BYTE* g_trampolineAdd = nullptr;
static BYTE* g_trampolineRemove = nullptr;
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
    wcscpy_s(slash+1, MAX_PATH-(slash+1-path), L"EnduranceCloneStage27.log");
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

// Stage13 experimental Endurance 2047 freeze-to-zero patch.
// This is the runtime setter observed by the user with 85 ID2047 global writes.
// All other AGTK variable IDs and object-scoped ID2047 are passed through.
static volatile LONG g_seenSet=0;
static volatile LONG g_frozen2047=0;

// Stage22 clone controller. The Endurance 2047 filter remains unchanged.
// All AGTK operations execute from the same thread that registers the player.
struct GameVec2 { float x,y; };
typedef void (__thiscall *AddObjectOriginal)(void*,void*);
typedef void (__thiscall *RemoveObjectOriginal)(void*,void*,bool,int,bool);
typedef int (__cdecl *CreateObjectForScript)(int,int,int,int);
typedef const GameVec2* (__thiscall *GetObjectPosition)(void*);
typedef void* (__cdecl *GetManagerInstance)();
typedef void* (__thiscall *GetCurrentScene)(void*);
typedef void* (__thiscall *FindObjectByInstance)(void*,int);
typedef int (__thiscall *GetObjectInstanceId)(void*);
typedef void (__thiscall *NativeDisappear)(void*,bool);
typedef void (__thiscall *SetPlayControllerId)(void*,int);
typedef int (__thiscall *GetObjectControllerId)(void*);
static bool DisableCloneController(void* original,void* clone,
                                   SetPlayControllerId setter,GetObjectControllerId getter){
    if(!original||!clone||original==clone||!setter||!getter){
        Log("CLONE_CONTROLLER_REFUSED: invalid distinct objects/callbacks.");return false;
    }
    void* originalPlay=*reinterpret_cast<void**>(static_cast<BYTE*>(original)+0x310);
    void* clonePlay=*reinterpret_cast<void**>(static_cast<BYTE*>(clone)+0x310);
    if(!originalPlay||!clonePlay||originalPlay==clonePlay){
        Log("CLONE_CONTROLLER_REFUSED: PlayObjectData missing or shared.");return false;
    }
    const int origBefore=getter(original);
    const int cloneBefore=getter(clone);
    if(origBefore<0){
        Log("CLONE_CONTROLLER_REFUSED: original player has no active controller.");return false;
    }
    // Use the motor's own per-instance PlayObjectData::setControllerId.
    // It assigns system variable ID22 only in the newly created object.
    setter(clonePlay,-1);
    const int cloneAfter=getter(clone);
    const int origAfter=getter(original);
    char line[180]={};
    sprintf_s(line,sizeof(line),
      "CLONE_CONTROLLER_STATE original=%d->%d clone=%d->%d",
      origBefore,origAfter,cloneBefore,cloneAfter);
    Log(line);
    return cloneAfter==-1 && origAfter==origBefore;
}


static void* g_playerObject=nullptr;
static void* g_playerLayer=nullptr;
static void* g_playerScene=nullptr;
static void* g_clonedObject=nullptr;
static void* g_newClone=nullptr;
static void* g_cloneScene=nullptr;
static int g_cloneInstance=-1;
static DWORD g_playerThread=0;
static volatile LONG g_cloneBusy=0;
static volatile LONG g_cloneEnabled=0;
static volatile LONG g_hotkeyPoll=0;
static bool g_prevF9=false,g_prevF10=false;
static bool ChordEdge(bool current,bool& previous){const bool fired=current&&!previous;previous=current;return fired;}

template<class T> static T GameFn(DWORD rva){
    BYTE* exe=reinterpret_cast<BYTE*>(GetModuleHandleW(nullptr));
    return reinterpret_cast<T>(exe+rva);
}
static void* GetCurrentGameScene(){
    GetManagerInstance instance=GameFn<GetManagerInstance>(0x1d32d0);
    void* manager=instance();
    if(!manager)return nullptr;
    void** vtable=*reinterpret_cast<void***>(manager);
    if(!vtable)return nullptr;
    return reinterpret_cast<GetCurrentScene>(vtable[0x18/4])(manager);
}
static bool PlayerClassId1(void* object) {
    if(!object)return false;
    BYTE* o=static_cast<BYTE*>(object);
    void* data=*reinterpret_cast<void**>(o+0x28c);
    if(!data)return false;
    return *reinterpret_cast<uint32_t*>(static_cast<BYTE*>(data)+0x18)==1u;
}
static void CapturePlayer(void* object,void* layer) {
    if(!object||!layer||!PlayerClassId1(object))return;
    void* scene=*reinterpret_cast<void**>(static_cast<BYTE*>(layer)+0x290);
    if(InterlockedCompareExchange(&g_cloneBusy,0,0)){
        g_newClone=object; // Never accidentally replace the actual player with the spawned copy.
        return;
    }
    if(!scene)return;
    if(g_playerObject==nullptr || scene!=g_playerScene){
        g_playerObject=object;
        g_playerLayer=layer;
        g_playerScene=scene;
        g_playerThread=GetCurrentThreadId();
        g_clonedObject=nullptr;
        g_cloneInstance=-1;
        g_cloneScene=nullptr;
        char msg[165]={};
        sprintf_s(msg,sizeof(msg),
          "PLAYER_CAPTURED object_id=1 layer_id=%ld thread=%lu",
          *reinterpret_cast<LONG*>(static_cast<BYTE*>(layer)+0x2b8),
          static_cast<unsigned long>(g_playerThread));
        Log(msg);
    }
}
static void __fastcall InterceptAddObject(void* layer,void* /*edx*/,void* object){
    AddObjectOriginal original=reinterpret_cast<AddObjectOriginal>(g_trampolineAdd);
    if(original)original(layer,object);
    CapturePlayer(object,layer);
}
static void __fastcall InterceptRemoveObject(void* layer,void* /*edx*/,
                                             void* object,bool destroy,int flag,bool finalFlag){
    RemoveObjectOriginal original=reinterpret_cast<RemoveObjectOriginal>(g_trampolineRemove);
    if(original)original(layer,object,destroy,flag,finalFlag);
    if(object==g_clonedObject){
        g_clonedObject=nullptr;
        g_cloneInstance=-1;
        g_cloneScene=nullptr;
        Log("CLONE_REMOVED_BY_ENGINE");
    }
    if(object==g_playerObject){
        g_playerObject=nullptr;
        g_playerLayer=nullptr;
        g_playerScene=nullptr;
        g_playerThread=0;
        Log("PLAYER_REMOVED_BY_ENGINE");
    }
}
static void SpawnCloneOnGameThread(){
    if(!g_playerObject || !g_playerLayer || !g_playerScene){
        Log("CLONE_REFUSED: player actor not captured yet. Enter/reload a gameplay scene.");
        return;
    }
    void* scene=GetCurrentGameScene();
    if(!scene || scene!=g_playerScene){
        Log("CLONE_REFUSED: player scene is no longer active.");
        return;
    }
    if(g_cloneInstance>0){
        Log("CLONE_REFUSED: an instance is already active; press F9 again or F10 to remove it.");
        return;
    }
    const GameVec2* vec=GameFn<GetObjectPosition>(0x127d50)(g_playerObject);
    if(!vec || !std::isfinite(vec->x) || !std::isfinite(vec->y) ||
       std::fabs(vec->x)>1000000.0f || std::fabs(vec->y)>1000000.0f){
        Log("CLONE_REFUSED: player coordinates invalid.");
        return;
    }
    const int layerId=*reinterpret_cast<int*>(static_cast<BYTE*>(g_playerLayer)+0x2b8);
    if(layerId<0 || layerId>64){
        Log("CLONE_REFUSED: unexpected scene layer ID.");
        return;
    }
    const int x=static_cast<int>(std::lround(vec->x+56.0f));
    const int y=static_cast<int>(std::lround(vec->y));
    g_newClone=nullptr;
    const int instance=GameFn<CreateObjectForScript>(0x13fcf0)(1,x,y,layerId);
    if(instance<=0){
        char msg[135]={};
        sprintf_s(msg,sizeof(msg),"CLONE_SPAWN_REJECTED: engine returned instance=%d",instance);
        Log(msg);
        return;
    }
    g_cloneInstance=instance;
    g_clonedObject=g_newClone;
    if(!g_clonedObject){
        GetManagerInstance getManager=GameFn<GetManagerInstance>(0x1d32d0);
        void* gm=getManager();
        if(gm){
            g_clonedObject=GameFn<FindObjectByInstance>(0x1e8470)(gm,instance);
        }
    }
    g_cloneScene=scene;
    // Disassociate just this clone from the player controller; preserve its
    // own collision, event object identity, actions and scene registration.
    if(!DisableCloneController(g_playerObject,g_clonedObject,
        GameFn<SetPlayControllerId>(0x6c500),
        GameFn<GetObjectControllerId>(0x128aa0))) {
        Log("CLONE_ISOLATION_FAILED: removing newly spawned copy.");
        if(g_clonedObject && g_clonedObject!=g_playerObject){
            void** vt=*reinterpret_cast<void***>(g_clonedObject);
            if(vt && vt[0x55c/4]) {
                reinterpret_cast<NativeDisappear>(vt[0x55c/4])(g_clonedObject,true);
                Log("CLONE_ISOLATION_CLEANUP_REQUESTED");
            }
        }
        return;
    }
    Log("CLONE_INPUT_INDEPENDENT: original retains controller; clone controller=-1.");
    char msg[205]={};
    sprintf_s(msg,sizeof(msg),
      "CLONE_CREATED object_id=1 instance=%d x=%d y=%d layer=%d object_captured=%u",
      instance,x,y,layerId,g_clonedObject?1u:0u);
    Log(msg);
}
static void RemoveCloneOnGameThread(){
    if(g_cloneInstance<=0 || !g_cloneScene){
        Log("CLONE_REMOVE_SKIPPED: no recorded clone.");
        return;
    }
    if(GetCurrentGameScene()!=g_cloneScene){
        g_cloneInstance=-1;
        g_clonedObject=nullptr;
        g_cloneScene=nullptr;
        Log("CLONE_REMOVE_SKIPPED: scene changed, stale clone forgotten.");
        return;
    }
    void* object=g_clonedObject;
    if(!object){
        void* manager=GameFn<GetManagerInstance>(0x1d32d0)();
        if(manager)object=GameFn<FindObjectByInstance>(0x1e8470)(manager,g_cloneInstance);
    }
    if(!object || object==g_playerObject){
        Log("CLONE_REMOVE_REFUSED: clone object unavailable or equals original player.");
        return;
    }
    // Same Object::disappear(bool=true) virtual dispatch as the native
    // ObjectAction::execActionDisappear command at 0x00543B20.
    void** vt=*reinterpret_cast<void***>(object);
    if(!vt || !vt[0x55c/4]){
        Log("CLONE_REMOVE_REFUSED: disappearance virtual missing.");
        return;
    }
    const int removedId=g_cloneInstance;
    reinterpret_cast<NativeDisappear>(vt[0x55c/4])(object,true);
    char msg[145]={};
    sprintf_s(msg,sizeof(msg),"CLONE_DISAPPEAR_REQUESTED instance=%d",removedId);
    Log(msg);
}
static void PollCloneHotkeys(){
    if(!InterlockedCompareExchange(&g_cloneEnabled,0,0))return;
    if(InterlockedCompareExchange(&g_cloneBusy,0,0))return;
    if(g_playerThread && GetCurrentThreadId()!=g_playerThread)return;
    const DWORD now=GetTickCount();
    const LONG last=InterlockedCompareExchange(&g_hotkeyPoll,0,0);
    if(static_cast<DWORD>(now-static_cast<DWORD>(last))<40u)return;
    if(InterlockedCompareExchange(&g_hotkeyPoll,static_cast<LONG>(now),last)!=last)return;
    // F9 toggles clone creation/removal; F10 is explicit emergency removal.
    // Neither F key is mapped by the canonical project's pcInput bindings.
    const bool f9=(GetAsyncKeyState(VK_F9)&0x8000)!=0;
    const bool f10=(GetAsyncKeyState(VK_F10)&0x8000)!=0;
    const bool doToggle=ChordEdge(f9,g_prevF9);
    const bool doRemove=ChordEdge(f10,g_prevF10);
    const bool doSpawn=doToggle;
    if(!doSpawn&&!doRemove)return;
    if(InterlockedCompareExchange(&g_cloneBusy,1,0)!=0)return;
    if(doRemove || (doSpawn && g_cloneInstance>0))RemoveCloneOnGameThread();
    else if(doSpawn)SpawnCloneOnGameThread();
    InterlockedExchange(&g_cloneBusy,0);
}

static double __fastcall InterceptSetValue(void* variable,void* /*edx*/,double requested) {
    SetValueOriginal original=reinterpret_cast<SetValueOriginal>(g_trampolineSet);
    if(!original)return requested;
    InterlockedIncrement(&g_seenSet);
    if(variable) {
        const BYTE* raw=reinterpret_cast<const BYTE*>(variable);
        uint32_t id=*reinterpret_cast<const uint32_t*>(raw+0x18);
        const void* object=*reinterpret_cast<void* const*>(raw+0x60);
        if(id==2047 && object==nullptr) {
            const LONG total=InterlockedIncrement(&g_frozen2047);
            if(total<=4) {
                char msg[180]={};
                sprintf_s(msg,sizeof(msg),
                  "FREEZE_2047_WRITE count=%ld requested=%.4f passed=0.0",total,requested);
                Log(msg);
            }
            double outcome=original(variable,0.0);
            PollCloneHotkeys();
            return outcome;
        }
    }
    double outcome=original(variable,requested);
    PollCloneHotkeys();
    return outcome;
}
static DWORD WINAPI ReportCounters(LPVOID) {
    LONG oldCount=-1;
    while(true) {
        Sleep(2500);
        LONG count=InterlockedCompareExchange(&g_frozen2047,0,0);
        if(count==oldCount)continue;
        oldCount=count;
        char msg[180]={};
        sprintf_s(msg,sizeof(msg),"COUNTERS set_calls=%ld frozen_global_2047=%ld",
          InterlockedCompareExchange(&g_seenSet,0,0),count);
        Log(msg);
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
    const bool setOk=InstallHook("PlayVariableData::setValue",0x6ab90,
                                 setPrologue,sizeof(setPrologue),
                                 reinterpret_cast<const void*>(&InterceptSetValue),
                                 &g_trampolineSet);
    const BYTE addPrologue[6]={0x55,0x8b,0xec,0x53,0x8b,0xd9};
    const BYTE removePrologue[6]={0x55,0x8b,0xec,0x83,0xe4,0xf8};
    bool addOk=InstallHook("SceneLayer::addObject",0x18b380,
                           addPrologue,sizeof(addPrologue),
                           reinterpret_cast<const void*>(&InterceptAddObject),
                           &g_trampolineAdd);
    bool removeOk=InstallHook("SceneLayer::removeObject",0x18b5c0,
                              removePrologue,sizeof(removePrologue),
                              reinterpret_cast<const void*>(&InterceptRemoveObject),
                              &g_trampolineRemove);
    if(setOk && addOk && removeOk){
        InterlockedExchange(&g_cloneEnabled,1);
        Log("CLONE_MODE_READY F9=toggle clone F10=remove; clone controller detached from player.");
    } else Log("CLONE_MODE_DISABLED: hook validation incomplete; Endurance filter may still work.");
    if(setOk){
        Log("FREEZE2047_READY: global ID2047 writes will be set to 0.0; other IDs pass unchanged.");
        Log("COUNTERS set_calls=0 frozen_global_2047=0");
        HANDLE h=CreateThread(nullptr,0,ReportCounters,nullptr,0,nullptr);
        if(h)CloseHandle(h);
        else Log("WARNING: periodic counter thread unavailable.");
    } else Log("HOOK_FAILED: no changes installed.");
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
