#define WIN32_LEAN_AND_MEAN
#include <windows.h>

static HMODULE g_realVersion=NULL;
static volatile LONG g_state=0;
static const wchar_t g_workflow_compat[]=L"AoE2DE_P3O_54800_RC9_FIX1.log";
static int wappend(wchar_t*d,unsigned cap,const wchar_t*s){unsigned n=0,j=0;while(n<cap&&d[n])n++;if(n>=cap)return 0;while(s[j]){if(n+1>=cap)return 0;d[n++]=s[j++];}d[n]=0;return 1;}
static void ensure_real(void){if(InterlockedCompareExchange(&g_state,1,0)!=0)return;wchar_t p[MAX_PATH+32]={0};UINT n=GetSystemDirectoryW(p,MAX_PATH);if(n&&n<MAX_PATH&&wappend(p,MAX_PATH+32,L"\\version.dll"))g_realVersion=LoadLibraryW(p);InterlockedExchange(&g_state,2);}
static FARPROC rp(const char*n){if(g_state!=2)ensure_real();if(!g_realVersion){SetLastError(ERROR_PROC_NOT_FOUND);return NULL;}FARPROC p=GetProcAddress(g_realVersion,n);if(!p)SetLastError(ERROR_PROC_NOT_FOUND);return p;}
static void miss(void){SetLastError(ERROR_PROC_NOT_FOUND);}
extern void resolver_start(void);

BOOL WINAPI GetFileVersionInfoA(LPCSTR f,DWORD h,DWORD n,LPVOID p){typedef BOOL(WINAPI*F)(LPCSTR,DWORD,DWORD,LPVOID);F x=(F)rp("GetFileVersionInfoA");return x?x(f,h,n,p):(miss(),FALSE);}
BOOL WINAPI GetFileVersionInfoW(LPCWSTR f,DWORD h,DWORD n,LPVOID p){typedef BOOL(WINAPI*F)(LPCWSTR,DWORD,DWORD,LPVOID);F x=(F)rp("GetFileVersionInfoW");return x?x(f,h,n,p):(miss(),FALSE);}
BOOL WINAPI GetFileVersionInfoExA(DWORD fl,LPCSTR f,DWORD h,DWORD n,LPVOID p){typedef BOOL(WINAPI*F)(DWORD,LPCSTR,DWORD,DWORD,LPVOID);F x=(F)rp("GetFileVersionInfoExA");return x?x(fl,f,h,n,p):(miss(),FALSE);}
BOOL WINAPI GetFileVersionInfoExW(DWORD fl,LPCWSTR f,DWORD h,DWORD n,LPVOID p){typedef BOOL(WINAPI*F)(DWORD,LPCWSTR,DWORD,DWORD,LPVOID);F x=(F)rp("GetFileVersionInfoExW");return x?x(fl,f,h,n,p):(miss(),FALSE);}
DWORD WINAPI GetFileVersionInfoSizeA(LPCSTR f,LPDWORD h){typedef DWORD(WINAPI*F)(LPCSTR,LPDWORD);F x=(F)rp("GetFileVersionInfoSizeA");return x?x(f,h):(miss(),0);}
DWORD WINAPI GetFileVersionInfoSizeW(LPCWSTR f,LPDWORD h){typedef DWORD(WINAPI*F)(LPCWSTR,LPDWORD);F x=(F)rp("GetFileVersionInfoSizeW");return x?x(f,h):(miss(),0);}
DWORD WINAPI GetFileVersionInfoSizeExA(DWORD fl,LPCSTR f,LPDWORD h){typedef DWORD(WINAPI*F)(DWORD,LPCSTR,LPDWORD);F x=(F)rp("GetFileVersionInfoSizeExA");return x?x(fl,f,h):(miss(),0);}
DWORD WINAPI GetFileVersionInfoSizeExW(DWORD fl,LPCWSTR f,LPDWORD h){typedef DWORD(WINAPI*F)(DWORD,LPCWSTR,LPDWORD);F x=(F)rp("GetFileVersionInfoSizeExW");return x?x(fl,f,h):(miss(),0);}
DWORD WINAPI VerFindFileA(DWORD fl,LPSTR f,LPSTR wd,LPSTR ad,LPSTR cd,PUINT cl,LPSTR dd,PUINT dl){typedef DWORD(WINAPI*F)(DWORD,LPSTR,LPSTR,LPSTR,LPSTR,PUINT,LPSTR,PUINT);F x=(F)rp("VerFindFileA");return x?x(fl,f,wd,ad,cd,cl,dd,dl):(miss(),0);}
DWORD WINAPI VerFindFileW(DWORD fl,LPWSTR f,LPWSTR wd,LPWSTR ad,LPWSTR cd,PUINT cl,LPWSTR dd,PUINT dl){typedef DWORD(WINAPI*F)(DWORD,LPWSTR,LPWSTR,LPWSTR,LPWSTR,PUINT,LPWSTR,PUINT);F x=(F)rp("VerFindFileW");return x?x(fl,f,wd,ad,cd,cl,dd,dl):(miss(),0);}
DWORD WINAPI VerInstallFileA(DWORD fl,LPSTR sf,LPSTR df,LPSTR sd,LPSTR dd,LPSTR cd,LPSTR tf,PUINT tl){typedef DWORD(WINAPI*F)(DWORD,LPSTR,LPSTR,LPSTR,LPSTR,LPSTR,LPSTR,PUINT);F x=(F)rp("VerInstallFileA");return x?x(fl,sf,df,sd,dd,cd,tf,tl):(miss(),0);}
DWORD WINAPI VerInstallFileW(DWORD fl,LPWSTR sf,LPWSTR df,LPWSTR sd,LPWSTR dd,LPWSTR cd,LPWSTR tf,PUINT tl){typedef DWORD(WINAPI*F)(DWORD,LPWSTR,LPWSTR,LPWSTR,LPWSTR,LPWSTR,LPWSTR,PUINT);F x=(F)rp("VerInstallFileW");return x?x(fl,sf,df,sd,dd,cd,tf,tl):(miss(),0);}
DWORD WINAPI VerLanguageNameA(DWORD l,LPSTR b,DWORD n){typedef DWORD(WINAPI*F)(DWORD,LPSTR,DWORD);F x=(F)rp("VerLanguageNameA");return x?x(l,b,n):(miss(),0);}
DWORD WINAPI VerLanguageNameW(DWORD l,LPWSTR b,DWORD n){typedef DWORD(WINAPI*F)(DWORD,LPWSTR,DWORD);F x=(F)rp("VerLanguageNameW");return x?x(l,b,n):(miss(),0);}
BOOL WINAPI VerQueryValueA(LPCVOID b,LPCSTR s,LPVOID*p,PUINT n){typedef BOOL(WINAPI*F)(LPCVOID,LPCSTR,LPVOID*,PUINT);F x=(F)rp("VerQueryValueA");return x?x(b,s,p,n):(miss(),FALSE);}
BOOL WINAPI VerQueryValueW(LPCVOID b,LPCWSTR s,LPVOID*p,PUINT n){typedef BOOL(WINAPI*F)(LPCVOID,LPCWSTR,LPVOID*,PUINT);F x=(F)rp("VerQueryValueW");return x?x(b,s,p,n):(miss(),FALSE);}
BOOL WINAPI GetFileVersionInfoByHandle(DWORD fl,HANDLE h,LPVOID*data,PDWORD len){typedef BOOL(WINAPI*F)(DWORD,HANDLE,LPVOID*,PDWORD);F x=(F)rp("GetFileVersionInfoByHandle");return x?x(fl,h,data,len):(miss(),FALSE);}
BOOL WINAPI DllMain(HINSTANCE h,DWORD r,LPVOID x){(void)x;if(r==DLL_PROCESS_ATTACH){DisableThreadLibraryCalls(h);OutputDebugStringW(g_workflow_compat);resolver_start();}return TRUE;}
