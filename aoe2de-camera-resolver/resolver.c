#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#define CAMERA_X_RVA 0x04416E40u
#define CAMERA_Y_RVA 0x04416E44u
#define ZOOM_RVA     0x040957D8u
#define RC3_PATCH_RVA 0x000048C5u
#define FIXED_50_BITS 0x42480000u

static HMODULE g_exe=NULL;
static HMODULE g_backend=NULL;
static DWORD g_backendImage=0;
static BYTE* g_litX=NULL;
static BYTE* g_litY=NULL;
static HWND g_game=NULL;
static WNDPROC g_backendProc=NULL;
static volatile LONG g_started=0;
static wchar_t g_log[MAX_PATH+96]={0};

static int readable_protect(DWORD p){
    if(p&PAGE_GUARD)return 0;
    p&=0xff;
    return p==PAGE_READONLY||p==PAGE_READWRITE||p==PAGE_WRITECOPY||
           p==PAGE_EXECUTE_READ||p==PAGE_EXECUTE_READWRITE||p==PAGE_EXECUTE_WRITECOPY;
}
static int readable(const void*p,SIZE_T n){
    MEMORY_BASIC_INFORMATION m;
    if(!VirtualQuery(p,&m,sizeof(m)))return 0;
    if(m.State!=MEM_COMMIT||!readable_protect(m.Protect))return 0;
    uintptr_t a=(uintptr_t)p,e=a+n,b=(uintptr_t)m.BaseAddress,z=b+m.RegionSize;
    return e>=a&&a>=b&&e<=z;
}
static int map_ok(float v){return v==v&&v>-64.0f&&v<2048.0f;}
static int zoom_ok(float v){return v==v&&v>=0.15f&&v<=5.0f;}

static void logf0(const char*fmt,...){
    if(!g_log[0])return;
    FILE*f=_wfopen(g_log,L"a");if(!f)return;
    va_list a;va_start(a,fmt);vfprintf(f,fmt,a);va_end(a);fclose(f);
}
static void init_log(void){
    wchar_t t[MAX_PATH];DWORD n=GetTempPathW(MAX_PATH,t);if(!n||n>=MAX_PATH)return;
    lstrcpynW(g_log,t,MAX_PATH+96);lstrcatW(g_log,L"AoE2DE_P3O_54800_EXACT_OVERLAY_BRIDGE_RC10.log");
    DeleteFileW(g_log);
    FILE*f=_wfopen(g_log,L"w");if(!f)return;
    fprintf(f,"AOE2DE 101.103.54800.0 EXACT P3O OVERLAY BRIDGE RC10\n");
    fprintf(f,"BACKEND=RC3_FIXEDPOINT exact migrated old overlay\n");
    fprintf(f,"CAMERA_X=0x%08X CAMERA_Y=0x%08X ZOOM=0x%08X RC3_PATCH=0x%08X\n",CAMERA_X_RVA,CAMERA_Y_RVA,ZOOM_RVA,RC3_PATCH_RVA);
    fclose(f);
}
static int sibling_path(wchar_t*out,unsigned cap,const wchar_t*name){
    DWORD n=GetModuleFileNameW(NULL,out,cap);if(!n||n>=cap)return 0;
    int i=(int)n-1;while(i>=0&&out[i]!=L'\\'&&out[i]!=L'/')i--;if(i<0)return 0;
    out[i+1]=0;if(lstrlenW(out)+lstrlenW(name)+1>=(int)cap)return 0;lstrcatW(out,name);return 1;
}
static DWORD image_size(HMODULE h){
    if(!h||!readable(h,sizeof(IMAGE_DOS_HEADER)))return 0;
    IMAGE_DOS_HEADER*d=(IMAGE_DOS_HEADER*)h;if(d->e_magic!=IMAGE_DOS_SIGNATURE||d->e_lfanew<=0||d->e_lfanew>0x100000)return 0;
    IMAGE_NT_HEADERS64*n=(IMAGE_NT_HEADERS64*)((BYTE*)h+d->e_lfanew);
    if(!readable(n,sizeof(*n))||n->Signature!=IMAGE_NT_SIGNATURE)return 0;
    return n->OptionalHeader.SizeOfImage;
}
static int ptr_in_backend(const void*p){
    uintptr_t a=(uintptr_t)p,b=(uintptr_t)g_backend;
    return g_backend&&g_backendImage&&a>=b&&a<b+g_backendImage;
}
static int load_backend(void){
    wchar_t p[MAX_PATH+64];if(!sibling_path(p,MAX_PATH+64,L"P3OBackend.dll")){logf0("BACKEND_PATH=FAIL\n");return 0;}
    g_backend=LoadLibraryW(p);
    if(!g_backend){logf0("BACKEND_LOAD=FAIL gle=%lu path=%ls\n",GetLastError(),p);return 0;}
    g_backendImage=image_size(g_backend);
    logf0("BACKEND_LOAD=PASS base=0x%llX image=0x%08X path=%ls\n",(unsigned long long)(uintptr_t)g_backend,g_backendImage,p);
    return g_backendImage!=0;
}
static int locate_fixedpoint_literals(void){
    if(!g_backend||g_backendImage<RC3_PATCH_RVA+16)return 0;
    BYTE*src=(BYTE*)g_backend+RC3_PATCH_RVA;
    if(!readable(src,9)){logf0("RC3_PATCH=UNREADABLE\n");return 0;}
    if(src[0]!=0xE9){logf0("RC3_PATCH=BAD_OPCODE got=%02X expected=E9\n",src[0]);return 0;}
    int32_t rel=0;memcpy(&rel,src+1,4);
    BYTE*target=src+5+rel;
    uintptr_t tb=(uintptr_t)target,bb=(uintptr_t)g_backend;
    if(tb<bb||tb+256>bb+g_backendImage){logf0("RC3_TRAMPOLINE=OUTSIDE target_rva=0x%llX\n",(unsigned long long)(tb-bb));return 0;}
    int found=0;
    for(int i=0;i<=252;i++){
        uint32_t v=0;memcpy(&v,target+i,4);
        if(v==FIXED_50_BITS){
            if(found==0)g_litX=target+i;
            else if(found==1)g_litY=target+i;
            found++;
        }
    }
    logf0("RC3_TRAMPOLINE rva=0x%llX fixed50_count=%d lit1_rva=0x%llX lit2_rva=0x%llX\n",
          (unsigned long long)(tb-bb),found,
          g_litX?(unsigned long long)((uintptr_t)g_litX-bb):0ULL,
          g_litY?(unsigned long long)((uintptr_t)g_litY-bb):0ULL);
    return found>=2;
}
static int read_camera(float*cx,float*cy,float*z){
    uintptr_t b=(uintptr_t)g_exe;
    if(!readable((void*)(b+CAMERA_X_RVA),8)||!readable((void*)(b+ZOOM_RVA),4))return 0;
    float x=*(volatile float*)(b+CAMERA_X_RVA),y=*(volatile float*)(b+CAMERA_Y_RVA),q=*(volatile float*)(b+ZOOM_RVA);
    if(!map_ok(x)||!map_ok(y)||!zoom_ok(q))return 0;
    if(cx)*cx=x;if(cy)*cy=y;if(z)*z=q;return 1;
}
static int target_from_mouse(HWND h,float*x,float*y,float*camx,float*camy,float*zoom,POINT*mouse){
    POINT p;RECT r;if(!GetCursorPos(&p)||!ScreenToClient(h,&p)||!GetClientRect(h,&r))return 0;
    int cw=r.right-r.left,ch=r.bottom-r.top;if(cw<=0||ch<=0)return 0;
    float cx,cy,z;if(!read_camera(&cx,&cy,&z))return 0;
    float dx=(float)p.x-(float)cw*0.5f,dy=(float)p.y-(float)ch*0.5f;
    float pan=0.0341f/z,sx=dx*pan*0.42f,sy=dy*pan*0.86f;
    float wx=cx+(sx-sy)*0.70710678f,wy=cy+(sx+sy)*0.70710678f;
    if(!map_ok(wx)||!map_ok(wy))return 0;
    *x=wx;*y=wy;if(camx)*camx=cx;if(camy)*camy=cy;if(zoom)*zoom=z;if(mouse)*mouse=p;return 1;
}
static int write_float_literal(BYTE*p,float v){
    if(!p)return 0;DWORD old=0,tmp=0;if(!VirtualProtect(p,4,PAGE_EXECUTE_READWRITE,&old))return 0;
    uint32_t u=0;memcpy(&u,&v,4);memcpy(p,&u,4);FlushInstructionCache(GetCurrentProcess(),p,4);
    VirtualProtect(p,4,old,&tmp);return 1;
}
static int patch_target(float x,float y){
    if(!g_litX||!g_litY)return 0;
    if(!write_float_literal(g_litX,x))return 0;
    if(!write_float_literal(g_litY,y))return 0;
    return 1;
}
static LRESULT CALLBACK bridge_proc(HWND h,UINT m,WPARAM w,LPARAM l){
    if((m==WM_KEYDOWN||m==WM_SYSKEYDOWN)&&w==VK_F12&&!(l&(1u<<30))){
        int ctrl=(GetKeyState(VK_CONTROL)&0x8000)!=0,shift=(GetKeyState(VK_SHIFT)&0x8000)!=0;
        if(!ctrl&&!shift){
            float x,y,cx,cy,z;POINT p;
            if(!target_from_mouse(h,&x,&y,&cx,&cy,&z,&p)){
                logf0("TARGET_PATCH=FAIL reason=mouse_or_camera\n");MessageBeep(MB_ICONHAND);return 0;
            }
            if(!patch_target(x,y)){
                logf0("TARGET_PATCH=FAIL reason=literal_write target=(%.4f,%.4f)\n",x,y);MessageBeep(MB_ICONHAND);return 0;
            }
            logf0("TARGET_PATCH=PASS mouse=(%ld,%ld) camera=(%.4f,%.4f) zoom=%.6f target=(%.4f,%.4f)\n",p.x,p.y,cx,cy,z,x,y);
        }
    }
    return g_backendProc?CallWindowProcW(g_backendProc,h,m,w,l):DefWindowProcW(h,m,w,l);
}
static int foreground_game(HWND*out){
    HWND h=GetForegroundWindow();if(!h)return 0;DWORD pid=0;GetWindowThreadProcessId(h,&pid);if(pid!=GetCurrentProcessId())return 0;
    RECT r;if(!GetClientRect(h,&r))return 0;if(r.right-r.left<800||r.bottom-r.top<500)return 0;if(out)*out=h;return 1;
}
static void try_bind(void){
    HWND h=NULL;if(!foreground_game(&h))return;
    WNDPROC cur=(WNDPROC)GetWindowLongPtrW(h,GWLP_WNDPROC);
    if(h==g_game&&cur==bridge_proc)return;
    if(!ptr_in_backend((void*)cur))return;
    SetLastError(0);LONG_PTR old=SetWindowLongPtrW(h,GWLP_WNDPROC,(LONG_PTR)bridge_proc);
    if(!old){logf0("BRIDGE_BIND=FAIL hwnd=0x%llX gle=%lu\n",(unsigned long long)(uintptr_t)h,GetLastError());return;}
    g_game=h;g_backendProc=(WNDPROC)old;
    RECT r={0};GetClientRect(h,&r);
    logf0("BRIDGE_BIND=PASS hwnd=0x%llX client=%ldx%ld backend_wndproc=0x%llX\n",
          (unsigned long long)(uintptr_t)h,r.right-r.left,r.bottom-r.top,(unsigned long long)(uintptr_t)g_backendProc);
}
static DWORD WINAPI worker(LPVOID x){
    (void)x;g_exe=GetModuleHandleW(NULL);init_log();
    if(!load_backend())return 0;
    if(!locate_fixedpoint_literals()){logf0("BRIDGE_READY=FALSE reason=fixedpoint_literals\n");return 0;}
    logf0("BRIDGE_READY=TRUE waiting_for_RC3_game_wndproc\n");
    for(;;){try_bind();Sleep(50);}return 0;
}
void resolver_start(void){
    if(InterlockedCompareExchange(&g_started,1,0)!=0)return;
    HANDLE h=CreateThread(NULL,0,worker,NULL,0,NULL);
    if(h)CloseHandle(h);else InterlockedExchange(&g_started,0);
}
