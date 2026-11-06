// Endurance Stage47 + independent clone mode — guarded x86 VERSION.dll proxy.
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
#include <intrin.h>
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
static BYTE* g_trampolineMove = nullptr;static BYTE* g_trampolinePlayerLookup=nullptr;
static BYTE* g_trampolineInstanceLookup=nullptr;
static BYTE* g_trampolineTargetByInstance=nullptr;
static BYTE* g_trampolineTargetList=nullptr;
static BYTE* g_trampolineDamaged=nullptr;
static BYTE* g_trampolineHp=nullptr;static BYTE* g_trampolineActionTarget=nullptr;
static BYTE* g_trampolineActionExec=nullptr;
static BYTE* g_trampolineScriptExec=nullptr;
static BYTE* g_trampolineVarExec=nullptr;
static BYTE* g_trampolineObjectChange=nullptr;
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
    wcscpy_s(slash+1, MAX_PATH-(slash+1-path), L"EnduranceCloneStage47.log");
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
typedef void* (__thiscall *GetScenePlayerObject)(void*);
typedef void* (__thiscall *FindObjectByInstance)(void*,int);
typedef int (__thiscall *GetObjectInstanceId)(void*);
typedef void (__thiscall *NativeDisappear)(void*,bool);
// ObjectMovement::move(float) returns cocos2d::Vec2 by hidden sret pointer.
// Machine entry: ECX=movement; [ESP+4]=Vec2* output; [ESP+8]=float delta.
typedef GameVec2* (__thiscall *MovementOriginal)(void*,GameVec2*,float);
typedef int (__thiscall *GetObjectControllerId)(void*);
// The active player and newly created clone each need their own instance
// data; controller IDs are NOT reliable evidence of physical movement input
// in this game's scenes (both often report -1).
static bool CheckCloneSeparateData(void* original,void* clone,
                                  GetObjectControllerId getter){
    if(!original||!clone||original==clone||!getter){
        Log("CLONE_IDENTITY_REFUSED: object pointers invalid.");return false;
    }
    void* originalPlay=*reinterpret_cast<void**>(static_cast<BYTE*>(original)+0x310);
    void* clonePlay=*reinterpret_cast<void**>(static_cast<BYTE*>(clone)+0x310);
    if(!originalPlay||!clonePlay||originalPlay==clonePlay){
        Log("CLONE_IDENTITY_REFUSED: runtime data missing or shared.");return false;
    }
    char line[170]={};
    sprintf_s(line,sizeof(line),
       "CLONE_IDENTITIES_SEPARATE original_controller=%d clone_controller=%d",
       getter(original),getter(clone));
    Log(line);
    return true;
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

static const char* TargetName(void* object); // defined with the existing Stage41 victim helpers
static bool PlayerClassId1(void* object); // defined below with existing native player validation
// Stage47 event action traces: log command owners and exact selected targets.
// No mutation or return-value redirection. All native calls run unchanged.
typedef void* (__thiscall *NativeActionTarget)(void*,int,int);
typedef bool (__thiscall *NativeBoolAction)(void*,void*);
typedef int (__thiscall *NativeIntAction)(void*,void*);
typedef void (__thiscall *NativeVoidAction)(void*,void*);
static volatile LONG g_actionTotals[5]={};
static volatile LONG g_cloneTargetRedirects=0;
struct ActionSite {volatile LONG key;volatile LONG count;};
static ActionSite g_actionSites[128]={};
static bool EventTraceActive(){
    return g_clonedObject && g_cloneInstance>0 && g_playerObject &&
           g_cloneScene && g_cloneScene==g_playerScene;
}
// Stage47: owner-aware variable write telemetry; NEVER changes variable values.
// The game uses global and per-player switches, so frame-local pointer rewrites
// alone cannot demonstrate which actor receives the scene event.
struct VariableTraceEntry { volatile LONG key; volatile LONG count; };
static VariableTraceEntry g_variableTrace[1024]={};
static volatile LONG g_varGlobal=0,g_varPlayer=0,g_varClone=0;
static int VariableOwnerKind(const void* owner){
    if(!owner)return 0;
    if(g_playerObject){
        const void* playerPlay=*reinterpret_cast<void* const*>(
          static_cast<BYTE*>(g_playerObject)+0x310);
        if(owner==g_playerObject || owner==playerPlay)return 1;
    }
    if(g_clonedObject){
        const void* clonePlay=*reinterpret_cast<void* const*>(
          static_cast<BYTE*>(g_clonedObject)+0x310);
        if(owner==g_clonedObject || owner==clonePlay)return 2;
    }
    return 3;
}
static void TraceVariableWrite(const void* variable,uint32_t id,
                               const void* owner,double requested){
    if(!variable || !EventTraceActive())return;
    const int kind=VariableOwnerKind(owner);
    const bool local=(kind==1||kind==2);
    if(!local && kind!=0)return;
    if(!((id>=2000&&id<=2400)||
         (local&&id<=64)))return;
    if(kind==0)InterlockedIncrement(&g_varGlobal);
    if(kind==1)InterlockedIncrement(&g_varPlayer);
    if(kind==2)InterlockedIncrement(&g_varClone);
    const LONG key=static_cast<LONG>(id*8u+static_cast<uint32_t>(kind)+1u);
    const uint32_t slot=(static_cast<uint32_t>(key)*2654435761u)&1023u;
    LONG count=0;
    for(unsigned probe=0;probe<12;++probe){
        auto& e=g_variableTrace[(slot+probe)&1023u];
        LONG found=InterlockedCompareExchange(&e.key,0,0);
        if(!found)found=InterlockedCompareExchange(&e.key,key,0);
        if(found==key){count=InterlockedIncrement(&e.count);break;}
    }
    if(!(count<=3 && count>0) &&
       !(count==8||count==32||count==128||count==512||count==2048))return;
    const double before=*reinterpret_cast<const double*>(
       static_cast<const BYTE*>(variable)+0x28);
    const char* who=kind==0?"global":kind==1?"original":"clone";
    char line[224]={};
    sprintf_s(line,sizeof(line),
       "VARIABLE_WRITE id=%lu owner=%s old=%.4f requested=%.4f count=%ld",
       static_cast<unsigned long>(id),who,before,requested,count);
    Log(line);
}
static void* EventActionOwner(void* action) {
    return action?*reinterpret_cast<void**>(static_cast<BYTE*>(action)+0x50):nullptr;
}
static unsigned EventOwnerId(void* actor){
    if(!actor)return 0;
    void* d=*reinterpret_cast<void**>(static_cast<BYTE*>(actor)+0x28c);
    return d?*reinterpret_cast<unsigned*>(static_cast<BYTE*>(d)+0x18):0;
}
static DWORD EventRva(void* caller){
    return static_cast<DWORD>(reinterpret_cast<uintptr_t>(caller)-
        reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr)));
}
static void EventRecord(int kind,void* action,void* target,int arg1,int arg2,void* caller) {
    if(!EventTraceActive() || kind<0 || kind>=5)return;
    void* owner=EventActionOwner(action);
    if(!owner)return;
    // The ObjectAction::owner is stored at +0x50 in all command executors.
    const DWORD at=EventRva(caller);
    const unsigned ownerId=EventOwnerId(owner);
    const int instance=*reinterpret_cast<int*>(static_cast<BYTE*>(owner)+0x40c);
    const LONG total=InterlockedIncrement(&g_actionTotals[kind]);
    const LONG key=static_cast<LONG>(
       ((at*16777619u)^static_cast<DWORD>(kind*271u)^
        static_cast<DWORD>(instance*31u) ^ static_cast<DWORD>(arg1))|1u);
    LONG seen=0;
    for(unsigned k=0;k<128;++k){
        LONG prev=InterlockedCompareExchange(&g_actionSites[k].key,0,0);
        if(!prev)prev=InterlockedCompareExchange(&g_actionSites[k].key,key,0);
        if(prev==key){seen=InterlockedIncrement(&g_actionSites[k].count);break;}
    }
    if(!(seen==1 || seen==2 || seen==8 || seen==64 || seen==512 ||
         (seen==0 && (total<=8 || (total&(total-1))==0))))return;
    const char* ownerName=TargetName(owner);
    const char* targetName=TargetName(target);
    char line[265]={};
    sprintf_s(line,sizeof(line),
        "EVENT_ACTION kind=%d owner_id=%u owner_field40c=%d owner=%s target=%s args=%d,%d caller_rva=0x%lx site=%ld total=%ld",
        kind,ownerId,instance,ownerName,targetName,arg1,arg2,
        static_cast<unsigned long>(at),seen,total);
    Log(line);
}
static void* __fastcall TraceActionTarget(void* action,void*,int a,int b){
    NativeActionTarget fn=reinterpret_cast<NativeActionTarget>(g_trampolineActionTarget);
    if(!fn)return nullptr;
    void* caller=_ReturnAddress();
    void* selected=fn(action,a,b);
    EventRecord(0,action,selected,a,b,caller);
    // Only the CLONE'S OWN command resolver may substitute an object.
    // Never redirect enemy scripts, scene actions, player-owned commands,
    // camera, arbitrary GameManager object/variable lookups or object lists.
    // Runtime Stage43 evidence: owner=clone, target=original,
    // args=(original instance,2), caller RVA=0x1533A7.
    if(EventTraceActive() && action && EventActionOwner(action)==g_clonedObject &&
       selected==g_playerObject && a>0 && b==2 &&
       g_clonedObject!=g_playerObject &&
       PlayerClassId1(g_clonedObject)) {
        const LONG hits=InterlockedIncrement(&g_cloneTargetRedirects);
        if(hits<=12 || (hits&(hits-1))==0) {
            char line[225]={};
            sprintf_s(line,sizeof(line),
              "CLONE_TARGET_REDIRECT owner=clone requested=%d scope=%d original_to_clone=1 caller_rva=0x%lx hits=%ld",
              a,b,static_cast<unsigned long>(EventRva(caller)),hits);
            Log(line);
        }
        return g_clonedObject;
    }
    return selected;
}
static bool __fastcall TraceActionExec(void* action,void*,void* command){
    NativeBoolAction fn=reinterpret_cast<NativeBoolAction>(g_trampolineActionExec);
    if(!fn)return false;
    EventRecord(1,action,nullptr,0,0,_ReturnAddress());
    return fn(action,command);
}
static int __fastcall TraceScriptExec(void* action,void*,void* command){
    NativeIntAction fn=reinterpret_cast<NativeIntAction>(g_trampolineScriptExec);
    if(!fn)return 0;
    EventRecord(2,action,nullptr,0,0,_ReturnAddress());
    return fn(action,command);
}
static void __fastcall TraceVarExec(void* action,void*,void* command){
    NativeVoidAction fn=reinterpret_cast<NativeVoidAction>(g_trampolineVarExec);
    if(!fn)return;
    EventRecord(3,action,nullptr,0,0,_ReturnAddress());
    fn(action,command);
}
static void __fastcall TraceObjectChange(void* action,void*,void* command){
    NativeVoidAction fn=reinterpret_cast<NativeVoidAction>(g_trampolineObjectChange);
    if(!fn)return;
    EventRecord(4,action,nullptr,0,0,_ReturnAddress());
    fn(action,command);
}


typedef void* (__thiscall *NativeTargetList)(void*,int);
typedef void (__thiscall *NativeDamaged)(void*,void*,void*,void*);
typedef double (__thiscall *NativeAddHp)(void*,double);
static volatile LONG g_targetListCount=0;
struct TargetListSite { volatile LONG key; volatile LONG count; };
static TargetListSite g_targetListSites[72]={};
static volatile LONG g_damagedCount=0;
static volatile LONG g_hpCount=0;
static bool TargetOwner(void* object){return object && (object==g_playerObject || object==g_clonedObject);}
static const char* TargetName(void* object){
    if(object && object==g_playerObject)return "original";
    if(object && object==g_clonedObject)return "clone";
    return object?"other":"null";
}
static const char* PlayDataName(void* play){
    if(!play)return "null";
    if(g_playerObject &&
       *reinterpret_cast<void**>(static_cast<BYTE*>(g_playerObject)+0x310)==play)return "original";
    if(g_clonedObject &&
       *reinterpret_cast<void**>(static_cast<BYTE*>(g_clonedObject)+0x310)==play)return "clone";
    return "other";
}
static DWORD SourceRva(void* caller){
    return static_cast<DWORD>(reinterpret_cast<uintptr_t>(caller)-
        reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr)));
}
// GameManager::getTargetObjectListByObjectId provides an autoreleased cocos2d::__Array.
// It is read-only: return value and array are never changed.
static void* __fastcall TraceTargetList(void* manager,void*,int objectId){
    NativeTargetList original=reinterpret_cast<NativeTargetList>(g_trampolineTargetList);
    if(!original)return nullptr;
    void* caller=_ReturnAddress();
    void* result=original(manager,objectId);
    if(!g_clonedObject || g_cloneInstance<=0)return result;
    const LONG total=InterlockedIncrement(&g_targetListCount);
    const DWORD rva=SourceRva(caller);
    const LONG key=static_cast<LONG>((rva ^ (static_cast<DWORD>(objectId)*0x9e3779b9u))|1u);
    LONG siteCalls=0;
    for(unsigned i=0;i<72;i++){
        LONG found=InterlockedCompareExchange(&g_targetListSites[i].key,0,0);
        if(!found)found=InterlockedCompareExchange(&g_targetListSites[i].key,key,0);
        if(found==key){
            siteCalls=InterlockedIncrement(&g_targetListSites[i].count);
            break;
        }
    }
    const bool record=(siteCalls==1||siteCalls==2||siteCalls==16||
                       siteCalls==128||siteCalls==1024||
                       (siteCalls==0 && (total<=8 || (total&(total-1))==0)));
    if(record){
        unsigned count=0;
        bool hasOriginal=false,hasClone=false;
        if(result){
            void* array=*reinterpret_cast<void**>(static_cast<BYTE*>(result)+0x1c);
            if(array){
                const unsigned sz=*reinterpret_cast<unsigned*>(array);
                if(sz<8192u){
                    count=sz;
                    void** items=*reinterpret_cast<void***>(static_cast<BYTE*>(array)+8);
                    if(items){
                        for(unsigned k=0;k<count;++k){
                            if(items[k]==g_playerObject)hasOriginal=true;
                            if(items[k]==g_clonedObject)hasClone=true;
                        }
                    }
                }
            }
        }
        char msg[240]={};
        sprintf_s(msg,sizeof(msg),
          "TARGET_LIST id=%d count=%u original=%u clone=%u caller_rva=0x%lx site_calls=%ld total=%ld",
          objectId,count,hasOriginal?1:0,hasClone?1:0,
          static_cast<unsigned long>(rva),siteCalls,total);
        Log(msg);
    }
    return result;
}
static void __fastcall TraceDamaged(void* victim,void*,void* attacker,void* data1,void* data2){
    NativeDamaged original=reinterpret_cast<NativeDamaged>(g_trampolineDamaged);
    if(!original)return;
    if(g_clonedObject && g_cloneInstance>0 && (TargetOwner(victim)||TargetOwner(attacker))){
        const LONG n=InterlockedIncrement(&g_damagedCount);
        if(n<=64 || (n& (n-1))==0){
            char line[240]={};
            sprintf_s(line,sizeof(line),
              "DAMAGE_CALL victim=%s attacker=%s data1=%s data2=%s caller_rva=0x%lx count=%ld",
              TargetName(victim),TargetName(attacker),PlayDataName(data1),PlayDataName(data2),
              static_cast<unsigned long>(SourceRva(_ReturnAddress())),n);
            Log(line);
        }
    }
    original(victim,attacker,data1,data2);
}
static double __fastcall TraceAddHp(void* play,void*,double amount){
    NativeAddHp original=reinterpret_cast<NativeAddHp>(g_trampolineHp);
    if(!original)return amount;
    if(g_clonedObject && g_cloneInstance>0){
        const char* who=PlayDataName(play);
        if(strcmp(who,"other")!=0 && strcmp(who,"null")!=0){
            const LONG n=InterlockedIncrement(&g_hpCount);
            if(n<=64 || (n& (n-1))==0){
                char line[210]={};
                sprintf_s(line,sizeof(line),
                  "HP_CHANGE target=%s input=%.4f caller_rva=0x%lx count=%ld",
                  who,amount,static_cast<unsigned long>(SourceRva(_ReturnAddress())),n);
                Log(line);
            }
        }
    }
    return original(play,amount);
}

typedef void* (__thiscall *NativePlayerLookup)(void*);
typedef void* (__thiscall *NativeInstanceLookup)(void*,int,int,int);
typedef void* (__thiscall *NativeTargetByInstance)(void*,int);
static volatile LONG g_resolverTotals[3]={};
struct ResolveSite {volatile LONG key; volatile LONG calls;};
static ResolveSite g_resolveSites[72]={};
static void RecordTargetLookup(int kind,int requested,void* returned,void* scene,void* returnAddress){
    if(!g_clonedObject || g_cloneInstance<=0 || scene!=g_cloneScene)return;
    if(kind<0 || kind>2)return;
    InterlockedIncrement(&g_resolverTotals[kind]);
    const LONG caller=static_cast<LONG>(reinterpret_cast<uintptr_t>(returnAddress)-
                                      reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr)));
    const LONG key=((caller & 0x1fffffff)<<2) | (kind+1);
    if(!key)return;
    LONG count=0;
    for(unsigned i=0;i<72;++i){
        LONG existing=InterlockedCompareExchange(&g_resolveSites[i].key,0,0);
        if(!existing)existing=InterlockedCompareExchange(&g_resolveSites[i].key,key,0);
        if(existing==key){count=InterlockedIncrement(&g_resolveSites[i].calls);break;}
    }
    if(count!=1 && count!=2 && count!=16 && count!=128) return;
    const char* dest=returned==g_playerObject?"original":
                     returned==g_clonedObject?"clone":
                     returned?"other":"null";
    char log[235]={};
    sprintf_s(log,sizeof(log),
      "TARGET_RESOLVE kind=%d request=%d result=%s caller_rva=0x%lx site_calls=%ld",
      kind,requested,dest,static_cast<unsigned long>(caller),count);
    Log(log);
}
static void* __fastcall TraceScenePlayer(void* scene,void*){
    NativePlayerLookup original=reinterpret_cast<NativePlayerLookup>(g_trampolinePlayerLookup);
    if(!original)return nullptr;
    void* caller=_ReturnAddress();
    void* ret=original(scene);
    RecordTargetLookup(0,0,ret,scene,caller);
    return ret;
}
static void* __fastcall TraceSceneInstance(void* scene,void*,int objectId,int instanceId,int scope){
    NativeInstanceLookup original=reinterpret_cast<NativeInstanceLookup>(g_trampolineInstanceLookup);
    if(!original)return nullptr;
    void* caller=_ReturnAddress();
    void* ret=original(scene,objectId,instanceId,scope);
    if(objectId==1) RecordTargetLookup(1,instanceId,ret,scene,caller);
    return ret;
}
static void* __fastcall TraceTargetByInstance(void* manager,void*,int instanceId){
    NativeTargetByInstance original=reinterpret_cast<NativeTargetByInstance>(g_trampolineTargetByInstance);
    if(!original)return nullptr;
    void* caller=_ReturnAddress();
    void* ret=original(manager,instanceId);
    if(g_cloneScene)RecordTargetLookup(2,instanceId,ret,g_cloneScene,caller);
    return ret;
}


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
static bool AdoptScenePlayer(void* scene,void* actor) {
    if(!scene || !actor || actor==g_clonedObject || !PlayerClassId1(actor)) {
        Log("PLAYER_REACQUIRE_PENDING: scene player not available or rejected.");
        return false;
    }
    void* layer=*reinterpret_cast<void**>(static_cast<BYTE*>(actor)+0x308);
    if(!layer || *reinterpret_cast<void**>(static_cast<BYTE*>(layer)+0x290)!=scene) {
        Log("PLAYER_REACQUIRE_REFUSED: layer/scene mismatch.");
        return false;
    }
    g_playerObject=actor;
    g_playerLayer=layer;
    g_playerScene=scene;
    g_playerThread=GetCurrentThreadId();
    if(g_cloneScene && g_cloneScene!=scene) {
        g_cloneInstance=-1;g_clonedObject=nullptr;g_cloneScene=nullptr;g_newClone=nullptr;
    }
    char line[180]={};
    sprintf_s(line,sizeof(line),"PLAYER_REACQUIRED_FROM_SCENE object_id=1 layer=%d",
        *reinterpret_cast<int*>(static_cast<BYTE*>(layer)+0x2b8));
    Log(line);
    return true;
}
static bool ReacquirePlayerForScene(void* scene) {
    if(!scene)return false;
    void* actor=GameFn<GetScenePlayerObject>(0x197780)(scene);
    return AdoptScenePlayer(scene,actor);
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
// Clone-only movement gate. Does not disable the object or event processing.
// ObjectMovement+0x18 is the owning Object* (confirmed from native move body).
static volatile LONG g_cloneMoveSuppressed=0;
static volatile LONG g_originalMoveForwarded=0;
static GameVec2* __fastcall InterceptMovement(void* movement,void* /*edx*/,
                                              GameVec2* output,float deltaSeconds){
    MovementOriginal original=reinterpret_cast<MovementOriginal>(g_trampolineMove);
    if(!original || !output)return output;
    void* owner=movement?
        *reinterpret_cast<void**>(static_cast<BYTE*>(movement)+0x18):nullptr;
    if(owner && owner==g_clonedObject && g_cloneInstance>0){
        output->x=0.0f;
        output->y=0.0f;
        const LONG n=InterlockedIncrement(&g_cloneMoveSuppressed);
        if(n<=3){
            char msg[140]={};
            sprintf_s(msg,sizeof(msg),
                "CLONE_MOVEMENT_BLOCKED count=%ld instance=%d",n,g_cloneInstance);
            Log(msg);
        }
        return output;
    }
    InterlockedIncrement(&g_originalMoveForwarded);
    return original(movement,output,deltaSeconds);
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
        // Keep known game-thread ID; only actor references are invalidated.
        Log("PLAYER_REMOVED_BY_ENGINE: actor references cleared; game thread retained.");
    }
}
static void SpawnCloneOnGameThread(){
    void* scene=GetCurrentGameScene();
    if(!scene){Log("CLONE_REFUSED: no current scene.");return;}
    if(!g_playerObject || !g_playerLayer || g_playerScene!=scene) {
        if(!ReacquirePlayerForScene(scene)) {
            Log("CLONE_REFUSED: player not yet available after scene transition.");
            return;
        }
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
    // No mutation of controller IDs. Their -1 value is already shared by
    // real protagonist and clone in the user's logs, so it cannot unlink input.
    // Our per-instance ObjectMovement::move hook suppresses clone motion.
    if(!CheckCloneSeparateData(g_playerObject,g_clonedObject,
        GameFn<GetObjectControllerId>(0x128aa0))) {
        Log("CLONE_IDENTITY_FAILED: removing newly spawned copy.");
        if(g_clonedObject && g_clonedObject!=g_playerObject){
            void** vt=*reinterpret_cast<void***>(g_clonedObject);
            if(vt && vt[0x55c/4]) {
                reinterpret_cast<NativeDisappear>(vt[0x55c/4])(g_clonedObject,true);
                Log("CLONE_ISOLATION_CLEANUP_REQUESTED");
            }
        }
        return;
    }
    Log("CLONE_MOVEMENT_GATE_READY: clone owned-movement suppressed, original untouched.");
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
        TraceVariableWrite(variable,id,object,requested);
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
    sprintf_s(line,sizeof(line),"HOOK_INSTALLED %s RVA=0x%lx (guarded x86 hook)",label,
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
    // AGTK ObjectMovement::move (VA 0x0051A020): first 6-byte instruction-aligned
    // prologue is push ebx; mov ebx,esp; sub esp,8.
    const BYTE movementPrologue[6]={0x53,0x8b,0xdc,0x83,0xec,0x08};
    const bool moveOk=InstallHook("ObjectMovement::move",0x11a020,
                                 movementPrologue,sizeof(movementPrologue),
                                 reinterpret_cast<const void*>(&InterceptMovement),
                                 &g_trampolineMove);
    const BYTE playerLookupBytes[8]={0x55,0x8b,0xec,0x8b,0x01,0x83,0xec,0x08};
    const BYTE instanceLookupBytes[6]={0x55,0x8b,0xec,0x83,0xe4,0xf8};
    const BYTE targetLookupBytes[6]={0x55,0x8b,0xec,0x8b,0x01,0x53};
    bool pOk=InstallHook("Scene::getObjectPlayer",0x197780,playerLookupBytes,8,
         reinterpret_cast<const void*>(&TraceScenePlayer),&g_trampolinePlayerLookup);
    bool iOk=InstallHook("Scene::getObjectInstance",0x19be80,instanceLookupBytes,6,
         reinterpret_cast<const void*>(&TraceSceneInstance),&g_trampolineInstanceLookup);
    bool tOk=InstallHook("GameManager::getTargetObjectByInstanceId",0x1e8470,targetLookupBytes,6,
         reinterpret_cast<const void*>(&TraceTargetByInstance),&g_trampolineTargetByInstance);
    if(pOk && iOk && tOk)Log("TARGET_TRACE_READY: read-only resolver tracing; no targeting changes.");
    else Log("TARGET_TRACE_PARTIAL: some optional resolver hooks unavailable.");
    // Stage47: read-only victim, HP and object-list diagnostic hooks.
    const BYTE listBytes[6]={0x55,0x8b,0xec,0x51,0x8b,0x01};
    const BYTE damagedBytes[6]={0x55,0x8b,0xec,0x83,0xe4,0xf8};
    const BYTE hpBytes[6]={0x55,0x8b,0xec,0x83,0xe4,0xc0};
    bool listOk=InstallHook("GameManager::getTargetObjectListByObjectId",0x1e8500,
      listBytes,sizeof(listBytes),reinterpret_cast<const void*>(&TraceTargetList),&g_trampolineTargetList);
    bool damagedOk=InstallHook("Object::damaged",0x12f760,
      damagedBytes,sizeof(damagedBytes),reinterpret_cast<const void*>(&TraceDamaged),&g_trampolineDamaged);
    bool hpOk=InstallHook("PlayObjectData::addHp",0x6c670,
      hpBytes,sizeof(hpBytes),reinterpret_cast<const void*>(&TraceAddHp),&g_trampolineHp);
    if(listOk && damagedOk && hpOk)
       Log("EVENT_EFFECT_TRACE_READY: target lists, damaged, HP are observed; no recipient altered.");
    else Log("EVENT_EFFECT_TRACE_PARTIAL: one or more optional hooks failed.");
    // Native action hooks are optional and diagnostic only.
    // Entry bytes are checked before any hook is installed.
    const BYTE actionTargetBytes[7]={0x55,0x8b,0xec,0x51,0x8b,0x41,0x50};
    const BYTE actionExecBytes[6]={0x55,0x8b,0xec,0x83,0xec,0x18};
    // Both procedures begin with push -1; push <absolute SEH handler>.
    // The immediate at +6 is HIGHLOW relocated if player.exe loads with ASLR.
    // Verify the exact instruction bytes and expected relocated address.
    BYTE scriptExecBytes[10]={0x55,0x8b,0xec,0x6a,0xff,0x68,0,0,0,0};
    BYTE varExecBytes[10]={0x55,0x8b,0xec,0x6a,0xff,0x68,0,0,0,0};
    const uintptr_t imageBase=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    const uint32_t scriptSeh=static_cast<uint32_t>(imageBase+0x4bca9c);
    const uint32_t varSeh=static_cast<uint32_t>(imageBase+0x4bc894);
    memcpy(scriptExecBytes+6,&scriptSeh,sizeof(scriptSeh));
    memcpy(varExecBytes+6,&varSeh,sizeof(varSeh));
    const BYTE objectChangeBytes[6]={0x53,0x8b,0xdc,0x83,0xec,0x08};
    bool e0=InstallHook("ObjectAction::getTargetObjectInstanceId",0x14d420,
      actionTargetBytes,sizeof(actionTargetBytes),
      reinterpret_cast<const void*>(&TraceActionTarget),&g_trampolineActionTarget);
    bool e1=InstallHook("ObjectAction::execActionActionExec",0x148530,
      actionExecBytes,sizeof(actionExecBytes),
      reinterpret_cast<const void*>(&TraceActionExec),&g_trampolineActionExec);
    bool e2=InstallHook("ObjectAction::execActionScriptEvaluate",0x149980,
      scriptExecBytes,sizeof(scriptExecBytes),
      reinterpret_cast<const void*>(&TraceScriptExec),&g_trampolineScriptExec);
    bool e3=InstallHook("ObjectAction::execActionSwitchVariableChange",0x146470,
      varExecBytes,sizeof(varExecBytes),
      reinterpret_cast<const void*>(&TraceVarExec),&g_trampolineVarExec);
    bool e4=InstallHook("ObjectAction::execActionObjectChange",0x1401a0,
      objectChangeBytes,sizeof(objectChangeBytes),
      reinterpret_cast<const void*>(&TraceObjectChange),&g_trampolineObjectChange);
    if(e0&&e1&&e2&&e3&&e4)Log("EVENT_ACTION_TRACE_READY: clone-owned action resolver may redirect original to clone; all other action owners unchanged.");
    else Log("EVENT_ACTION_TRACE_PARTIAL: optional event command hooks not all available.");
    if(setOk && addOk && removeOk && moveOk){
        InterlockedExchange(&g_cloneEnabled,1);
        Log("CLONE_MODE_READY F9=toggle clone F10=remove; clone-only ObjectMovement gate active.");
    } else Log("CLONE_MODE_DISABLED: 4-hook validation incomplete; Endurance filter may still work.");
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
