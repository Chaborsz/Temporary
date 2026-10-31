#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>

#define DATA_START 0x03DA5000ULL
#define DATA_END   0x04F22000ULL
#define DATA_SIZE  (DATA_END-DATA_START)
#define ZOOM_RVA   0x040957D8u
#define REJECT_X   0x04416E40u
#define REJECT_Y   0x04416E44u
#define MAX_HITS   256

typedef struct { DWORD rva; float x[6],y[6]; float pan,mouse,bridge,score; } Hit;

static BYTE *snap[6]={0,0,0,0,0,0};
static HMODULE exeBase=NULL;
static wchar_t logPath[MAX_PATH+96];
static volatile LONG started=0,done=0;
static int sampleNo=0;

static float ab(float v){return v<0?-v:v;}
static int mapish(float v){return v==v && v>-64.0f && v<2048.0f;}
static int readable_protect(DWORD p){
    if(p&PAGE_GUARD) return 0;
    p&=0xff;
    return p==PAGE_READONLY || p==PAGE_READWRITE || p==PAGE_WRITECOPY ||
           p==PAGE_EXECUTE_READ || p==PAGE_EXECUTE_READWRITE || p==PAGE_EXECUTE_WRITECOPY;
}
static float pairdist(float ax,float ay,float bx,float by){return ab(ax-bx)+ab(ay-by);}

static void initlog(void){
    wchar_t t[MAX_PATH]; DWORD n=GetTempPathW(MAX_PATH,t);
    if(!n||n>=MAX_PATH) return;
    lstrcpynW(logPath,t,MAX_PATH+96);
    lstrcatW(logPath,L"AoE2DE_P3O_54800_CameraDiscriminator_RC8.txt");
    DeleteFileW(logPath);
    FILE*f=_wfopen(logPath,L"w"); if(!f) return;
    fprintf(f,"AOE2DE 101.103.54800.0 CAMERA DISCRIMINATOR RC8\n");
    fprintf(f,"MODE=READ_ONLY_SIX_SAMPLE_PAN_VS_MOUSE\nBASE=0x%llX\n",(unsigned long long)(uintptr_t)exeBase);
    fprintf(f,"DATA_SCAN=0x%llX..0x%llX size=0x%llX\n",(unsigned long long)DATA_START,(unsigned long long)DATA_END,(unsigned long long)DATA_SIZE);
    fprintf(f,"ZOOM_RVA=0x%08X KNOWN_REJECTED_MOUSE_COUPLED_PAIR=0x%08X/0x%08X\n",ZOOM_RVA,REJECT_X,REJECT_Y);
    fprintf(f,"PROTOCOL=S1-S3 pan_camera_recenter_mouse; S4-S6 camera_fixed_mouse_only; zoom_fixed_all\n\n");
    fclose(f);
}

static int alloc_snap(int idx){
    if(snap[idx]) return 1;
    snap[idx]=(BYTE*)VirtualAlloc(NULL,(SIZE_T)DATA_SIZE,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    return snap[idx]!=NULL;
}

static int capture_snapshot(int idx){
    if(!alloc_snap(idx)) return 0;
    ZeroMemory(snap[idx],(SIZE_T)DATA_SIZE);
    uintptr_t base=(uintptr_t)exeBase,start=base+DATA_START,end=base+DATA_END,p=start;
    while(p<end){
        MEMORY_BASIC_INFORMATION m;
        if(!VirtualQuery((void*)p,&m,sizeof(m))) return 0;
        uintptr_t rb=(uintptr_t)m.BaseAddress,re=rb+m.RegionSize;
        uintptr_t a=p>rb?p:rb,z=end<re?end:re;
        if(z>a && m.State==MEM_COMMIT && readable_protect(m.Protect))
            CopyMemory(snap[idx]+(a-start),(void*)a,(SIZE_T)(z-a));
        if(re<=p) break;
        p=re;
    }
    return 1;
}

static void keep(Hit *h,int *n,DWORD rva,float *x,float *y,float pan,float mouse,float bridge,float score){
    int k;
    if(*n<MAX_HITS) k=(*n)++;
    else{
        k=0; for(int i=1;i<MAX_HITS;i++) if(h[i].score<h[k].score) k=i;
        if(score<=h[k].score) return;
    }
    h[k].rva=rva; for(int i=0;i<6;i++){h[k].x[i]=x[i];h[k].y[i]=y[i];}
    h[k].pan=pan;h[k].mouse=mouse;h[k].bridge=bridge;h[k].score=score;
}
static void sort_hits(Hit*h,int n){for(int i=0;i<n;i++)for(int j=i+1;j<n;j++)if(h[j].score>h[i].score){Hit t=h[i];h[i]=h[j];h[j]=t;}}

static void finish(FILE*f){
    Hit strict[MAX_HITS],ranked[MAX_HITS]; int ns=0,nr=0; DWORD strictTotal=0,rankedTotal=0;
    for(uint64_t off=0;off+8<=DATA_SIZE;off+=4){
        float x[6],y[6]; int ok=1;
        for(int s=0;s<6;s++){
            x[s]=*(float*)(snap[s]+off); y[s]=*(float*)(snap[s]+off+4);
            if(!mapish(x[s])||!mapish(y[s])){ok=0;break;}
        }
        if(!ok) continue;
        float pan=pairdist(x[0],y[0],x[1],y[1])+pairdist(x[1],y[1],x[2],y[2]);
        float mouse=pairdist(x[3],y[3],x[4],y[4])+pairdist(x[4],y[4],x[5],y[5]);
        float bridge=pairdist(x[2],y[2],x[3],y[3]);
        if(pan>1.0f){
            float score=pan/(1.0f+20.0f*mouse+8.0f*bridge);
            rankedTotal++; keep(ranked,&nr,(DWORD)(DATA_START+off),x,y,pan,mouse,bridge,score);
            if(pan>2.0f && mouse<0.20f && bridge<0.30f){
                strictTotal++; keep(strict,&ns,(DWORD)(DATA_START+off),x,y,pan,mouse,bridge,score);
            }
        }
    }
    sort_hits(strict,ns); sort_hits(ranked,nr);
    fprintf(f,"\n=== STRICT_CAMERA_PAIRS ===\nSTRICT_TOTAL=%u\n",strictTotal);
    for(int i=0;i<ns;i++){
        Hit*q=&strict[i];
        fprintf(f,"PAIR rva=0x%08X pan=%.6f mouse=%.6f bridge=%.6f score=%.6f S1=(%.6f,%.6f) S2=(%.6f,%.6f) S3=(%.6f,%.6f) S4=(%.6f,%.6f) S5=(%.6f,%.6f) S6=(%.6f,%.6f)\n",
            q->rva,q->pan,q->mouse,q->bridge,q->score,q->x[0],q->y[0],q->x[1],q->y[1],q->x[2],q->y[2],q->x[3],q->y[3],q->x[4],q->y[4],q->x[5],q->y[5]);
    }
    fprintf(f,"STRICT_TOP_COUNT=%d\n\n=== RANKED_PAN_STABLE_MOUSE_TOP ===\nRANKED_TOTAL=%u\n",rankedTotal);
    for(int i=0;i<nr;i++){
        Hit*q=&ranked[i];
        fprintf(f,"PAIR rva=0x%08X pan=%.6f mouse=%.6f bridge=%.6f score=%.6f S1=(%.6f,%.6f) S2=(%.6f,%.6f) S3=(%.6f,%.6f) S4=(%.6f,%.6f) S5=(%.6f,%.6f) S6=(%.6f,%.6f)\n",
            q->rva,q->pan,q->mouse,q->bridge,q->score,q->x[0],q->y[0],q->x[1],q->y[1],q->x[2],q->y[2],q->x[3],q->y[3],q->x[4],q->y[4],q->x[5],q->y[5]);
    }
    fprintf(f,"RANKED_TOP_COUNT=%d\nSTATUS=COMPLETE_SEND_THIS_FILE\n",nr);
}

static void sample_now(void){
    if(done||sampleNo>=6) return;
    DWORD t=GetTickCount(); int ok=capture_snapshot(sampleNo);
    uintptr_t b=(uintptr_t)exeBase; float zoom=*(volatile float*)(b+ZOOM_RVA);
    float rx=*(volatile float*)(b+REJECT_X),ry=*(volatile float*)(b+REJECT_Y);
    HWND h=GetForegroundWindow();DWORD pid=0;GetWindowThreadProcessId(h,&pid);POINT p={0,0};RECT r={0,0,0,0};
    int mok=(h&&pid==GetCurrentProcessId()&&GetCursorPos(&p)&&ScreenToClient(h,&p)&&GetClientRect(h,&r));
    FILE*f=_wfopen(logPath,L"a");
    if(f){
        if(mok) fprintf(f,"SAMPLE_%d=%s elapsed_ms=%u mouse=(%ld,%ld) client=%dx%d zoom=%.9f rejected_pair=(%.6f,%.6f)\n",sampleNo+1,ok?"PASS":"FAIL",GetTickCount()-t,p.x,p.y,r.right-r.left,r.bottom-r.top,zoom,rx,ry);
        else fprintf(f,"SAMPLE_%d=%s elapsed_ms=%u mouse=FAIL zoom=%.9f rejected_pair=(%.6f,%.6f)\n",sampleNo+1,ok?"PASS":"FAIL",GetTickCount()-t,zoom,rx,ry);
        if(ok&&sampleNo==5) finish(f);
        fclose(f);
    }
    MessageBeep(sampleNo==5?MB_ICONASTERISK:MB_OK); sampleNo++;
    if(sampleNo>=6) InterlockedExchange(&done,1);
}

static DWORD WINAPI worker(LPVOID x){
    (void)x;exeBase=GetModuleHandleW(NULL);initlog();SHORT prev=0;
    for(;;){SHORT s=GetAsyncKeyState(VK_F11);if((s&0x8000)&&!(prev&0x8000)&&!done)sample_now();prev=s;Sleep(40);}return 0;
}
void resolver_start(void){
    if(InterlockedCompareExchange(&started,1,0)!=0)return;
    HANDLE h=CreateThread(NULL,0,worker,NULL,0,NULL);if(h)CloseHandle(h);
}
