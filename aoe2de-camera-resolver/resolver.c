#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <wchar.h>

#define TARGET_TS       0x6AA0F114u
#define TARGET_EP       0x02D6CBF4u
#define TARGET_IMAGE    0x04F22000u
#define WORLD_RVA       0x04353698u
#define CAMERA_X_RVA    0x04416E40u
#define CAMERA_Y_RVA    0x04416E44u
#define ZOOM_RVA        0x040957D8u
#define XSCREATE_RVA    0x01812E50u
#define MAX_UNITS       512
#define VISIBLE_ROWS    8
#define HEADER_H        38
#define ROW_H           34
#define OVERLAY_W       340
#define OVERLAY_X       500
#define OVERLAY_Y       8
#define IDC_HEADER      100
#define IDC_ROW0        200

typedef struct { int id; wchar_t name[96]; } UnitEntry;
typedef struct { float x,y,z,w; } Vec4;
typedef int (__fastcall *XsCreateUnitFn)(int,int,Vec4*,int,int,int);

static HMODULE g_exe=NULL;
static UnitEntry g_units[MAX_UNITS];
static int g_unitCount=0;
static volatile LONG g_selected=0;
static volatile LONG g_scroll=0;
static HWND g_game=NULL,g_overlay=NULL,g_header=NULL,g_rows[VISIBLE_ROWS]={0};
static WNDPROC g_oldGameProc=NULL;
static volatile LONG g_started=0,g_bound=0,g_open=0;
static wchar_t g_ini[MAX_PATH+64]={0};
static wchar_t g_log[MAX_PATH+96]={0};

static int readable_protect(DWORD p){if(p&PAGE_GUARD)return 0;p&=0xff;return p==PAGE_READONLY||p==PAGE_READWRITE||p==PAGE_WRITECOPY||p==PAGE_EXECUTE_READ||p==PAGE_EXECUTE_READWRITE||p==PAGE_EXECUTE_WRITECOPY;}
static int readable(const void*p,SIZE_T n){MEMORY_BASIC_INFORMATION m;if(!VirtualQuery(p,&m,sizeof(m)))return 0;if(m.State!=MEM_COMMIT||!readable_protect(m.Protect))return 0;uintptr_t a=(uintptr_t)p,e=a+n,b=(uintptr_t)m.BaseAddress,z=b+m.RegionSize;return e>=a&&a>=b&&e<=z;}
static int ptr_ok(uintptr_t p){return p>=0x10000ULL&&p<0x0000800000000000ULL;}
static int map_ok(float v){return v==v&&v>-64.0f&&v<2048.0f;}
static int zoom_ok(float v){return v==v&&v>=0.15f&&v<=5.0f;}

static void logf0(const char*fmt,...){if(!g_log[0])return;FILE*f=_wfopen(g_log,L"a");if(!f)return;va_list a;va_start(a,fmt);vfprintf(f,fmt,a);va_end(a);fclose(f);}
static void init_log(void){wchar_t t[MAX_PATH];DWORD n=GetTempPathW(MAX_PATH,t);if(!n||n>=MAX_PATH)return;lstrcpynW(g_log,t,MAX_PATH+96);lstrcatW(g_log,L"AoE2DE_P3O_54800_RC9_FIX1.log");DeleteFileW(g_log);FILE*f=_wfopen(g_log,L"w");if(!f)return;fprintf(f,"AOE2DE 101.103.54800.0 P3O OVERLAY + POINT-AT-MOUSE RC9 FIX1\n");fprintf(f,"WORLD=0x%08X CAMERA_X=0x%08X CAMERA_Y=0x%08X ZOOM=0x%08X XSCREATE=0x%08X\n",WORLD_RVA,CAMERA_X_RVA,CAMERA_Y_RVA,ZOOM_RVA,XSCREATE_RVA);fclose(f);}

static int valid_target(void){if(!g_exe)return 0;IMAGE_DOS_HEADER*d=(IMAGE_DOS_HEADER*)g_exe;if(!readable(d,sizeof(*d))||d->e_magic!=IMAGE_DOS_SIGNATURE||d->e_lfanew<=0||d->e_lfanew>0x100000)return 0;IMAGE_NT_HEADERS64*n=(IMAGE_NT_HEADERS64*)((BYTE*)g_exe+d->e_lfanew);if(!readable(n,sizeof(*n)))return 0;return n->Signature==IMAGE_NT_SIGNATURE&&n->FileHeader.Machine==IMAGE_FILE_MACHINE_AMD64&&n->FileHeader.TimeDateStamp==TARGET_TS&&n->OptionalHeader.Magic==IMAGE_NT_OPTIONAL_HDR64_MAGIC&&n->OptionalHeader.AddressOfEntryPoint==TARGET_EP&&n->OptionalHeader.ImageBase==0x140000000ULL&&n->OptionalHeader.SizeOfImage==TARGET_IMAGE;}

static int sibling_path(wchar_t*out,unsigned cap,const wchar_t*name){DWORD n=GetModuleFileNameW(NULL,out,cap);if(!n||n>=cap)return 0;int i=(int)n-1;while(i>=0&&out[i]!=L'\\'&&out[i]!=L'/')i--;if(i<0)return 0;out[i+1]=0;if(lstrlenW(out)+lstrlenW(name)+1>=(int)cap)return 0;lstrcatW(out,name);return 1;}
static void choose_ini(void){wchar_t p[MAX_PATH+64];if(sibling_path(p,MAX_PATH+64,L"AoE2DE_P3N.ini")&&GetFileAttributesW(p)!=INVALID_FILE_ATTRIBUTES){lstrcpynW(g_ini,p,MAX_PATH+64);return;}if(sibling_path(p,MAX_PATH+64,L"AoE2DE_P3O.ini")&&GetFileAttributesW(p)!=INVALID_FILE_ATTRIBUTES){lstrcpynW(g_ini,p,MAX_PATH+64);return;}sibling_path(g_ini,MAX_PATH+64,L"AoE2DE_P3N.ini");}

static void add_unit(int id,const wchar_t*name){if(g_unitCount>=MAX_UNITS||id<=0)return;for(int i=0;i<g_unitCount;i++)if(g_units[i].id==id)return;g_units[g_unitCount].id=id;if(name&&*name)lstrcpynW(g_units[g_unitCount].name,name,96);else wsprintfW(g_units[g_unitCount].name,L"Unidad %d",id);g_unitCount++;}
static void fallback_catalog(void){g_unitCount=0;add_unit(2721,L"Harald");add_unit(2722,L"Ulf Ospaksson");add_unit(2723,L"Halldor Snorrason");add_unit(2725,L"Finn Arnason");add_unit(2726,L"Kalf Arnason");add_unit(2724,L"Tostig Godwinson");add_unit(2727,L"Einar Paunch-Shaker");add_unit(2728,L"Dreki");}
static wchar_t* trimw(wchar_t*s){while(*s==L' '||*s==L'\t')s++;wchar_t*e=s+lstrlenW(s);while(e>s&&(e[-1]==L' '||e[-1]==L'\t'||e[-1]==L'\r'||e[-1]==L'\n'))*--e=0;return s;}
static void parse_named(wchar_t*buf){wchar_t*p=buf;while(*p&&g_unitCount<MAX_UNITS){wchar_t*end=wcschr(p,L'|');if(end)*end=0;wchar_t*t=trimw(p);wchar_t*colon=wcschr(t,L':');if(colon){*colon=0;int id=(int)wcstol(trimw(t),NULL,10);add_unit(id,trimw(colon+1));}else{wchar_t*comma=t;while(*comma){wchar_t*next=wcschr(comma,L',');if(next)*next=0;int id=(int)wcstol(trimw(comma),NULL,10);if(id>0)add_unit(id,NULL);if(!next)break;comma=next+1;}}if(!end)break;p=end+1;}}
static int ini_int(const wchar_t*key,int def){if(!g_ini[0])return def;int v=(int)GetPrivateProfileIntW(L"P3N",key,0x7ffffffe,g_ini);if(v!=0x7ffffffe)return v;v=(int)GetPrivateProfileIntW(L"P3O",key,0x7ffffffe,g_ini);return v==0x7ffffffe?def:v;}
static void load_catalog(void){choose_ini();g_unitCount=0;wchar_t buf[32768]={0};DWORD n=0;if(g_ini[0]){n=GetPrivateProfileStringW(L"P3N",L"unit_cycle",L"",buf,32768,g_ini);if(!n)n=GetPrivateProfileStringW(L"P3O",L"unit_cycle",L"",buf,32768,g_ini);}if(n)parse_named(buf);if(!g_unitCount)fallback_catalog();int initial=ini_int(L"unit_id",g_units[0].id);for(int i=0;i<g_unitCount;i++)if(g_units[i].id==initial){g_selected=i;break;}logf0("CATALOG count=%d ini=%ls selected_id=%d\n",g_unitCount,g_ini,g_units[(int)g_selected].id);}

static int live_world(uintptr_t*outWorld){uintptr_t b=(uintptr_t)g_exe,m=0,w=0;if(!readable((void*)(b+WORLD_RVA),8))return 0;m=*(uintptr_t*)(b+WORLD_RVA);if(!ptr_ok(m)||!readable((void*)(m+0x5C0),8))return 0;w=*(uintptr_t*)(m+0x5C0);if(!ptr_ok(w)||!readable((void*)(w+0x6A8),8)||!readable((void*)(w+0x88),4))return 0;if(*(int*)(w+0x88)==2||*(uintptr_t*)(w+0x6A8)==0)return 0;if(outWorld)*outWorld=w;return 1;}
static int foreground_game(HWND*out){HWND h=GetForegroundWindow();if(!h)return 0;DWORD pid=0;GetWindowThreadProcessId(h,&pid);if(pid!=GetCurrentProcessId())return 0;if(out)*out=h;return 1;}

static int target_from_mouse(HWND h,float*x,float*y,float*camx,float*camy,float*zoom,POINT*mouse){POINT p;RECT r;if(!GetCursorPos(&p)||!ScreenToClient(h,&p)||!GetClientRect(h,&r))return 0;int cw=r.right-r.left,ch=r.bottom-r.top;if(cw<=0||ch<=0)return 0;uintptr_t b=(uintptr_t)g_exe;if(!readable((void*)(b+CAMERA_X_RVA),8)||!readable((void*)(b+ZOOM_RVA),4))return 0;float cx=*(volatile float*)(b+CAMERA_X_RVA),cy=*(volatile float*)(b+CAMERA_Y_RVA),z=*(volatile float*)(b+ZOOM_RVA);if(!map_ok(cx)||!map_ok(cy)||!zoom_ok(z))return 0;float dx=(float)p.x-(float)cw*0.5f,dy=(float)p.y-(float)ch*0.5f;float pan=0.0341f/z;float sx=dx*pan*0.42f,sy=dy*pan*0.86f;float wx=cx+(sx-sy)*0.70710678f,wy=cy+(sx+sy)*0.70710678f;if(!map_ok(wx)||!map_ok(wy))return 0;*x=wx;*y=wy;if(camx)*camx=cx;if(camy)*camy=cy;if(zoom)*zoom=z;if(mouse)*mouse=p;return 1;}

static int spawn_selected(HWND h){if(!live_world(NULL)){logf0("SPAWN fail=world_not_ready\n");return 0;}LONG si=InterlockedCompareExchange(&g_selected,0,0);if(si<0||si>=g_unitCount)return 0;int unit=g_units[si].id,player=ini_int(L"player_id",1),foundation=ini_int(L"foundation",0),sound=ini_int(L"play_sound",0),collision=ini_int(L"check_collision",1);float x,y,cx,cy,z;POINT mp;if(!target_from_mouse(h,&x,&y,&cx,&cy,&z,&mp)){logf0("SPAWN fail=mouse_target\n");return 0;}static const float ring[13][2]={{0,0},{1,0},{-1,0},{0,1},{0,-1},{2,2},{-2,2},{2,-2},{-2,-2},{3,0},{-3,0},{0,3},{0,-3}};XsCreateUnitFn fn=(XsCreateUnitFn)((uintptr_t)g_exe+XSCREATE_RVA);if(!readable((void*)fn,16))return 0;int tries=collision?13:1;for(int i=0;i<tries;i++){float wx=x+ring[i][0],wy=y+ring[i][1];Vec4 loc={wx,wy,0.0f,0.0f};int r=fn(unit,player,&loc,foundation,sound,collision);if(r!=-1){logf0("P3O_SPAWN=SUCCESS id=%d name=%ls result=%d attempt=%d mouse=(%ld,%ld) camera=(%.4f,%.4f) zoom=%.6f target=(%.4f,%.4f) actual=(%.4f,%.4f)\n",unit,g_units[si].name,r,i+1,mp.x,mp.y,cx,cy,z,x,y,wx,wy);MessageBeep(MB_OK);return 1;}}logf0("P3O_SPAWN=FAIL id=%d mouse=(%ld,%ld) camera=(%.4f,%.4f) zoom=%.6f target=(%.4f,%.4f)\n",unit,mp.x,mp.y,cx,cy,z,x,y);MessageBeep(MB_ICONHAND);return 0;}

static void overlay_refresh(void){if(!g_overlay||!g_unitCount)return;LONG s=InterlockedCompareExchange(&g_selected,0,0);if(s<0)s=0;if(s>=g_unitCount)s=g_unitCount-1;wchar_t t[160];wsprintfW(t,L"%ls  [%d]   ▼",g_units[s].name,g_units[s].id);SetWindowTextW(g_header,t);LONG sc=InterlockedCompareExchange(&g_scroll,0,0);if(sc<0)sc=0;if(sc>g_unitCount-1)sc=g_unitCount-1;for(int i=0;i<VISIBLE_ROWS;i++){int ix=(int)sc+i;if(ix<g_unitCount){wsprintfW(t,L"%ls  [%d]",g_units[ix].name,g_units[ix].id);SetWindowTextW(g_rows[i],t);ShowWindow(g_rows[i],SW_SHOWNOACTIVATE);}else ShowWindow(g_rows[i],SW_HIDE);}int opened=(int)InterlockedCompareExchange(&g_open,0,0);for(int i=0;i<VISIBLE_ROWS;i++)if(!opened)ShowWindow(g_rows[i],SW_HIDE);SetWindowPos(g_overlay,HWND_TOPMOST,0,0,OVERLAY_W,opened?HEADER_H+VISIBLE_ROWS*ROW_H:HEADER_H,SWP_NOMOVE|SWP_NOACTIVATE);}
static LRESULT CALLBACK overlay_proc(HWND h,UINT m,WPARAM w,LPARAM l){if(m==WM_CREATE){g_header=CreateWindowExW(0,L"BUTTON",L"P3O",WS_CHILD|WS_VISIBLE|BS_PUSHBUTTON,0,0,OVERLAY_W,HEADER_H,h,(HMENU)(INT_PTR)IDC_HEADER,NULL,NULL);for(int i=0;i<VISIBLE_ROWS;i++)g_rows[i]=CreateWindowExW(0,L"BUTTON",L"",WS_CHILD|BS_PUSHBUTTON,0,HEADER_H+i*ROW_H,OVERLAY_W,ROW_H,h,(HMENU)(INT_PTR)(IDC_ROW0+i),NULL,NULL);overlay_refresh();return 0;}if(m==WM_MOUSEACTIVATE)return MA_NOACTIVATE;if(m==WM_COMMAND){int id=LOWORD(w);if(id==IDC_HEADER){InterlockedExchange(&g_open,!InterlockedCompareExchange(&g_open,0,0));overlay_refresh();return 0;}if(id>=IDC_ROW0&&id<IDC_ROW0+VISIBLE_ROWS){LONG sc=InterlockedCompareExchange(&g_scroll,0,0);int ix=(int)sc+(id-IDC_ROW0);if(ix>=0&&ix<g_unitCount){InterlockedExchange(&g_selected,ix);InterlockedExchange(&g_open,0);logf0("P3O_UI_SELECT=SUCCESS index=%d unit_id=%d name=%ls\n",ix,g_units[ix].id,g_units[ix].name);overlay_refresh();}return 0;}}if(m==WM_MOUSEWHEEL&&InterlockedCompareExchange(&g_open,0,0)){int d=GET_WHEEL_DELTA_WPARAM(w);LONG sc=InterlockedCompareExchange(&g_scroll,0,0);if(d<0&&sc<g_unitCount-VISIBLE_ROWS)sc++;if(d>0&&sc>0)sc--;InterlockedExchange(&g_scroll,sc);overlay_refresh();return 0;}if(m==WM_CLOSE){ShowWindow(h,SW_HIDE);return 0;}return DefWindowProcW(h,m,w,l);}

static void select_delta(int d){if(!g_unitCount)return;LONG s=InterlockedCompareExchange(&g_selected,0,0);s=(s+d+g_unitCount)%g_unitCount;InterlockedExchange(&g_selected,s);LONG sc=InterlockedCompareExchange(&g_scroll,0,0);if(s<sc)sc=s;if(s>=sc+VISIBLE_ROWS)sc=s-VISIBLE_ROWS+1;InterlockedExchange(&g_scroll,sc);if(g_overlay)PostMessageW(g_overlay,WM_APP+1,0,0);logf0("P3O_KEY_SELECT index=%ld unit_id=%d name=%ls\n",s,g_units[s].id,g_units[s].name);}
static LRESULT CALLBACK game_proc(HWND h,UINT m,WPARAM w,LPARAM l){static int f12=0;if((m==WM_KEYDOWN||m==WM_SYSKEYDOWN)&&w==VK_F12){if(!f12&&!(l&(1u<<30))){f12=1;if(GetKeyState(VK_CONTROL)&0x8000)select_delta(+1);else if(GetKeyState(VK_SHIFT)&0x8000)select_delta(-1);else spawn_selected(h);}return 0;}if((m==WM_KEYUP||m==WM_SYSKEYUP)&&w==VK_F12){f12=0;return 0;}if(m==WM_ACTIVATEAPP&&!w)f12=0;WNDPROC p=g_oldGameProc;return p?CallWindowProcW(p,h,m,w,l):DefWindowProcW(h,m,w,l);}

static DWORD WINAPI overlay_thread(LPVOID x){(void)x;WNDCLASSW wc;ZeroMemory(&wc,sizeof(wc));wc.lpfnWndProc=overlay_proc;wc.hInstance=GetModuleHandleW(NULL);wc.lpszClassName=L"P3O54800OverlayRC9Fix1";wc.hCursor=LoadCursorW(NULL,IDC_ARROW);RegisterClassW(&wc);g_overlay=CreateWindowExW(WS_EX_TOPMOST|WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE,wc.lpszClassName,L"",WS_POPUP|WS_BORDER,0,0,OVERLAY_W,HEADER_H,NULL,NULL,wc.hInstance,NULL);MSG msg;for(;;){while(PeekMessageW(&msg,NULL,0,0,PM_REMOVE)){if(msg.message==WM_QUIT)return 0;TranslateMessage(&msg);DispatchMessageW(&msg);}if(g_overlay){int live=live_world(NULL);HWND fg=GetForegroundWindow();int show=live&&g_game&&IsWindow(g_game)&&fg==g_game;if(show){POINT p={0,0};ClientToScreen(g_game,&p);SetWindowPos(g_overlay,HWND_TOPMOST,p.x+OVERLAY_X,p.y+OVERLAY_Y,0,0,SWP_NOSIZE|SWP_NOACTIVATE|SWP_SHOWWINDOW);}else ShowWindow(g_overlay,SW_HIDE);}Sleep(30);}return 0;}

static void bind_game(HWND h){if(!h||h==g_game)return;if(g_game&&g_oldGameProc&&IsWindow(g_game))SetWindowLongPtrW(g_game,GWLP_WNDPROC,(LONG_PTR)g_oldGameProc);SetLastError(0);LONG_PTR p=SetWindowLongPtrW(h,GWLP_WNDPROC,(LONG_PTR)game_proc);if(p){g_game=h;g_oldGameProc=(WNDPROC)p;InterlockedExchange(&g_bound,1);RECT r;GetClientRect(h,&r);logf0("P3O_BIND_READY=TRUE hwnd=0x%llX client=%ldx%ld\n",(unsigned long long)(uintptr_t)h,r.right-r.left,r.bottom-r.top);}else logf0("P3O_BIND_FAIL gle=%lu\n",GetLastError());}
static DWORD WINAPI worker(LPVOID x){(void)x;g_exe=GetModuleHandleW(NULL);init_log();if(!valid_target()){logf0("TARGET_ID=FAIL\n");return 0;}logf0("TARGET_ID=PASS\n");load_catalog();HANDLE oh=CreateThread(NULL,0,overlay_thread,NULL,0,NULL);if(oh)CloseHandle(oh);for(;;){if(live_world(NULL)){HWND h=NULL;if(foreground_game(&h)&&h!=g_overlay)bind_game(h);}Sleep(100);}return 0;}
void resolver_start(void){if(InterlockedCompareExchange(&g_started,1,0)!=0)return;HANDLE h=CreateThread(NULL,0,worker,NULL,0,NULL);if(h)CloseHandle(h);}
