#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>

#define CAMERA_X_RVA 0x04416E40u
#define CAMERA_Y_RVA 0x04416E44u
#define ZOOM_RVA     0x040957D8u

static HMODULE exeBase=NULL;
static wchar_t logPath[MAX_PATH+96];
static volatile LONG started=0,done=0;
static int sampleNo=0;

static int mapish(float v){return v==v && v>-64.0f && v<2048.0f;}
static int zoomish(float v){return v==v && v>=0.15f && v<=5.0f;}

static void initlog(void){
    wchar_t t[MAX_PATH]; DWORD n=GetTempPathW(MAX_PATH,t);
    if(!n||n>=MAX_PATH) return;
    lstrcpynW(logPath,t,MAX_PATH+96);
    lstrcatW(logPath,L"AoE2DE_P3O_54800_CameraCandidate_RC7.txt");
    DeleteFileW(logPath);
    FILE*f=_wfopen(logPath,L"w"); if(!f) return;
    fprintf(f,"AOE2DE 101.103.54800.0 CAMERA CANDIDATE RC7\n");
    fprintf(f,"MODE=READ_ONLY_MOUSE_SEPARATION\nBASE=0x%llX\n",(unsigned long long)(uintptr_t)exeBase);
    fprintf(f,"CAMERA_X_RVA=0x%08X CAMERA_Y_RVA=0x%08X ZOOM_RVA=0x%08X\n",CAMERA_X_RVA,CAMERA_Y_RVA,ZOOM_RVA);
    fprintf(f,"PROJECTION=legacy_P3J dx/dy pan=0.0341/zoom iso=(0.42,0.86,0.70710678)\n\n");
    fclose(f);
}

static void sample_now(void){
    if(done||sampleNo>=3) return;
    uintptr_t b=(uintptr_t)exeBase;
    float cx=*(volatile float*)(b+CAMERA_X_RVA);
    float cy=*(volatile float*)(b+CAMERA_Y_RVA);
    float zoom=*(volatile float*)(b+ZOOM_RVA);
    HWND h=GetForegroundWindow(); DWORD pid=0; GetWindowThreadProcessId(h,&pid);
    POINT p={0,0}; RECT r={0,0,0,0};
    int mouseOk=(h && pid==GetCurrentProcessId() && GetCursorPos(&p) && ScreenToClient(h,&p) && GetClientRect(h,&r));
    FILE*f=_wfopen(logPath,L"a"); if(!f) return;
    if(!mouseOk){
        fprintf(f,"SAMPLE_%d=FAIL reason=foreground_or_mouse hwnd=0x%llX pid=%lu\n",sampleNo+1,(unsigned long long)(uintptr_t)h,pid);
    }else{
        int w=r.right-r.left,hh=r.bottom-r.top;
        float dx=(float)p.x-(float)w*0.5f;
        float dy=(float)p.y-(float)hh*0.5f;
        float pan=0.0341f/zoom;
        float sx=dx*pan*0.42f;
        float sy=dy*pan*0.86f;
        float wx=cx+(sx-sy)*0.70710678f;
        float wy=cy+(sx+sy)*0.70710678f;
        fprintf(f,"SAMPLE_%d=PASS mouse=(%ld,%ld) client=%dx%d camera=(%.9f,%.9f) zoom=%.9f target=(%.9f,%.9f) camera_ok=%d zoom_ok=%d\n",
            sampleNo+1,p.x,p.y,w,hh,cx,cy,zoom,wx,wy,mapish(cx)&&mapish(cy),zoomish(zoom));
    }
    fclose(f);
    MessageBeep(sampleNo==2?MB_ICONASTERISK:MB_OK);
    sampleNo++;
    if(sampleNo>=3){
        FILE*g=_wfopen(logPath,L"a"); if(g){fprintf(g,"STATUS=COMPLETE_SEND_THIS_FILE\n");fclose(g);} InterlockedExchange(&done,1);
    }
}

static DWORD WINAPI worker(LPVOID x){
    (void)x; exeBase=GetModuleHandleW(NULL); initlog(); SHORT prev=0;
    for(;;){SHORT s=GetAsyncKeyState(VK_F11);if((s&0x8000)&&!(prev&0x8000)&&!done)sample_now();prev=s;Sleep(40);} return 0;
}
void resolver_start(void){
    if(InterlockedCompareExchange(&started,1,0)!=0) return;
    HANDLE h=CreateThread(NULL,0,worker,NULL,0,NULL); if(h) CloseHandle(h);
}
