#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>

#define CAMERA_X_RVA 0x04416E40u
#define CAMERA_Y_RVA 0x04416E44u
#define ZOOM_RVA     0x040957D8u
#define WORLD_RVA    0x04353698u
#define XSCREATE_RVA 0x01812E50u
#define UNIT_ID      83
#define PLAYER_ID    1

typedef struct { float x,y,z,w; } Vec4;
typedef int (__fastcall *XsCreateUnitFn)(int,int,Vec4*,int,int,int);

static HMODULE exeBase=NULL;
static HWND gameHwnd=NULL;
static WNDPROC oldProc=NULL;
static volatile LONG started=0;
static volatile LONG installed=0;
static int f12Down=0;
static wchar_t logPath[MAX_PATH+96];

static int readable_protect(DWORD p){
    if(p&PAGE_GUARD) return 0;
    p&=0xff;
    return p==PAGE_READONLY || p==PAGE_READWRITE || p==PAGE_WRITECOPY ||
           p==PAGE_EXECUTE_READ || p==PAGE_EXECUTE_READWRITE || p==PAGE_EXECUTE_WRITECOPY;
}
static int readable(const void*p,SIZE_T n){
    MEMORY_BASIC_INFORMATION m;
    if(!VirtualQuery(p,&m,sizeof(m))) return 0;
    if(m.State!=MEM_COMMIT || !readable_protect(m.Protect)) return 0;
    uintptr_t a=(uintptr_t)p,e=a+n,b=(uintptr_t)m.BaseAddress,z=b+m.RegionSize;
    return e>=a && a>=b && e<=z;
}
static int ptr_ok(uintptr_t p){return p>=0x10000ULL && p<0x0000800000000000ULL && (p&7ULL)==0;}
static int map_ok(float v){return v==v && v>-64.0f && v<2048.0f;}
static int zoom_ok(float v){return v==v && v>=0.15f && v<=5.0f;}

static void logline(const char*fmt,...){
    FILE*f=_wfopen(logPath,L"a"); if(!f)return;
    va_list ap; va_start(ap,fmt); vfprintf(f,fmt,ap); va_end(ap); fclose(f);
}
static void initlog(void){
    wchar_t t[MAX_PATH];DWORD n=GetTempPathW(MAX_PATH,t);if(!n||n>=MAX_PATH)return;
    lstrcpynW(logPath,t,MAX_PATH+96);lstrcatW(logPath,L"AoE2DE_P3O_54800_PointAtMouse_RC9.txt");DeleteFileW(logPath);
    FILE*f=_wfopen(logPath,L"w");if(!f)return;
    fprintf(f,"AOE2DE 101.103.54800.0 POINT-AT-MOUSE RC9\nMODE=MINIMAL_VISUAL_PROOF\n");
    fprintf(f,"CAMERA_X_RVA=0x%08X CAMERA_Y_RVA=0x%08X ZOOM_RVA=0x%08X\n",CAMERA_X_RVA,CAMERA_Y_RVA,ZOOM_RVA);
    fprintf(f,"XSCREATE_RVA=0x%08X WORLD_RVA=0x%08X UNIT_ID=%d PLAYER_ID=%d\n\n",XSCREATE_RVA,WORLD_RVA,UNIT_ID,PLAYER_ID);
    fclose(f);
}

static BOOL CALLBACK enum_cb(HWND h,LPARAM lp){
    DWORD pid=0;GetWindowThreadProcessId(h,&pid);
    if(pid==GetCurrentProcessId() && IsWindowVisible(h) && GetWindow(h,GW_OWNER)==NULL){*(HWND*)lp=h;return FALSE;}
    return TRUE;
}
static HWND find_game_window(void){HWND h=NULL;EnumWindows(enum_cb,(LPARAM)&h);return h;}

static int world_ready(void){
    uintptr_t b=(uintptr_t)exeBase,m=0,w=0;
    if(!readable((void*)(b+WORLD_RVA),sizeof(uintptr_t)))return 0;
    m=*(uintptr_t*)(b+WORLD_RVA);if(!ptr_ok(m)||!readable((void*)(m+0x5C0),sizeof(uintptr_t)))return 0;
    w=*(uintptr_t*)(m+0x5C0);if(!ptr_ok(w)||!readable((void*)w,0x6B0))return 0;
    return 1;
}

static int compute_target(HWND h,float*outx,float*outy,float*outz,float*ocx,float*ocy,float*oz,POINT*omp,RECT*orct){
    POINT p;RECT r;
    if(!GetCursorPos(&p)||!ScreenToClient(h,&p)||!GetClientRect(h,&r))return 0;
    int w=r.right-r.left,hh=r.bottom-r.top;if(w<=0||hh<=0)return 0;
    uintptr_t b=(uintptr_t)exeBase;
    if(!readable((void*)(b+CAMERA_X_RVA),8)||!readable((void*)(b+ZOOM_RVA),4))return 0;
    float cx=*(volatile float*)(b+CAMERA_X_RVA),cy=*(volatile float*)(b+CAMERA_Y_RVA),z=*(volatile float*)(b+ZOOM_RVA);
    if(!map_ok(cx)||!map_ok(cy)||!zoom_ok(z))return 0;
    float dx=(float)p.x-(float)w*0.5f;
    float dy=(float)p.y-(float)hh*0.5f;
    float pan=0.0341f/z;
    float sx=dx*pan*0.42f;
    float sy=dy*pan*0.86f;
    float wx=cx+(sx-sy)*0.70710678f;
    float wy=cy+(sx+sy)*0.70710678f;
    if(!map_ok(wx)||!map_ok(wy))return 0;
    *outx=wx;*outy=wy;*outz=0.0f;if(ocx)*ocx=cx;if(ocy)*ocy=cy;if(oz)*oz=z;if(omp)*omp=p;if(orct)*orct=r;return 1;
}

static int do_spawn(HWND h){
    if(!world_ready()){logline("P3O_RC9_SPAWN=FAIL reason=world_not_ready\n");return 0;}
    float x,y,z,cx,cy,zoom;POINT mp;RECT rc;
    if(!compute_target(h,&x,&y,&z,&cx,&cy,&zoom,&mp,&rc)){logline("P3O_RC9_SPAWN=FAIL reason=target\n");return 0;}
    static const float ring[13][2]={{0,0},{1,0},{-1,0},{0,1},{0,-1},{2,2},{-2,2},{2,-2},{-2,-2},{3,0},{-3,0},{0,3},{0,-3}};
    XsCreateUnitFn fn=(XsCreateUnitFn)((uintptr_t)exeBase+XSCREATE_RVA);
    if(!readable((void*)fn,16)){logline("P3O_RC9_SPAWN=FAIL reason=xs_unreadable\n");return 0;}
    for(int i=0;i<13;i++){
        Vec4 v={x+ring[i][0],y+ring[i][1],z,0.0f};
        int result=fn(UNIT_ID,PLAYER_ID,&v,0,0,1);
        if(result!=-1){
            logline("P3O_RC9_SPAWN=SUCCESS result=%d attempt=%d mouse=(%ld,%ld) client=%ldx%ld camera=(%.6f,%.6f) zoom=%.6f target=(%.6f,%.6f) actual=(%.6f,%.6f)\n",result,i+1,mp.x,mp.y,rc.right-rc.left,rc.bottom-rc.top,cx,cy,zoom,x,y,v.x,v.y);
            MessageBeep(MB_OK);return 1;
        }
    }
    logline("P3O_RC9_SPAWN=NO_CREATE mouse=(%ld,%ld) camera=(%.6f,%.6f) zoom=%.6f target=(%.6f,%.6f)\n",mp.x,mp.y,cx,cy,zoom,x,y);
    MessageBeep(MB_ICONHAND);return 0;
}

static LRESULT CALLBACK our_proc(HWND h,UINT m,WPARAM w,LPARAM l){
    if((m==WM_KEYDOWN||m==WM_SYSKEYDOWN) && w==VK_F12){
        if(!f12Down && !(l&(1u<<30))){f12Down=1;do_spawn(h);}return 0;
    }
    if((m==WM_KEYUP||m==WM_SYSKEYUP) && w==VK_F12){f12Down=0;return 0;}
    if(m==WM_ACTIVATEAPP && !w)f12Down=0;
    return CallWindowProcW(oldProc,h,m,w,l);
}

static DWORD WINAPI worker(LPVOID x){
    (void)x;exeBase=GetModuleHandleW(NULL);initlog();
    for(int i=0;i<600 && !installed;i++){
        HWND h=find_game_window();
        if(h){
            SetLastError(0);LONG_PTR prev=SetWindowLongPtrW(h,GWLP_WNDPROC,(LONG_PTR)our_proc);
            if(prev){gameHwnd=h;oldProc=(WNDPROC)prev;InterlockedExchange(&installed,1);logline("P3O_RC9_READY=TRUE hwnd=0x%llX\n",(unsigned long long)(uintptr_t)h);break;}
            logline("P3O_RC9_WNDPROC_INSTALL=FAIL gle=%lu\n",GetLastError());
        }
        Sleep(100);
    }
    if(!installed)logline("P3O_RC9_READY=FALSE reason=no_window_or_subclass\n");
    return 0;
}

void resolver_start(void){
    if(InterlockedCompareExchange(&started,1,0)!=0)return;
    HANDLE h=CreateThread(NULL,0,worker,NULL,0,NULL);if(h)CloseHandle(h);
}
