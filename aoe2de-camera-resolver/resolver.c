#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>

#define DATA_START 0x03DA5000ULL
#define DATA_END   0x04F22000ULL
#define DATA_SIZE  (DATA_END-DATA_START)
#define MAX_CAM 32768
#define MAX_HITS 512

typedef struct { DWORD rva; float x[3], y[3]; BYTE ok[3]; } Cam;
typedef struct { DWORD rva; float v[3]; float score; } Hit;

static Cam cams[MAX_CAM];
static DWORD camCount=0;
static BYTE *snap[3]={0,0,0};
static HMODULE exeBase=NULL;
static wchar_t logPath[MAX_PATH+96];
static volatile LONG started=0,done=0;
static int sampleNo=0;

static float ab(float v){return v<0?-v:v;}
static int finiteish(float v){return v==v && v>-4096.0f && v<4096.0f;}
static int mapish(float v){return v==v && v>-64.0f && v<2048.0f;}
static int zoomish(float v){return v==v && v>=0.15f && v<=5.0f;}
static int plausible_ptr(uintptr_t p){return p>=0x10000ULL && p<0x0000800000000000ULL && (p&7ULL)==0;}
static int readable_protect(DWORD p){
    if(p&PAGE_GUARD) return 0;
    p &= 0xff;
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
static int ru64(uintptr_t p,uintptr_t*out){if(!readable((void*)p,sizeof(uintptr_t)))return 0;*out=*(uintptr_t*)p;return 1;}
static int rf32(uintptr_t p,float*out){if(!readable((void*)p,4))return 0;*out=*(float*)p;return 1;}
static int camread(DWORD rva,float*x,float*y){
    uintptr_t b=(uintptr_t)exeBase,p0=0,c=0;
    if(!ru64(b+rva,&p0) || !plausible_ptr(p0)) return 0;
    if(!ru64(p0+0x28,&c) || !plausible_ptr(c)) return 0;
    if(!rf32(c+0x2F0,x) || !rf32(c+0x2F4,y)) return 0;
    return mapish(*x)&&mapish(*y);
}

static void initlog(void){
    wchar_t t[MAX_PATH]; DWORD n=GetTempPathW(MAX_PATH,t);
    if(!n||n>=MAX_PATH) return;
    lstrcpynW(logPath,t,MAX_PATH+96);
    lstrcatW(logPath,L"AoE2DE_P3O_54800_InternalCameraResolver_RC6.txt");
    DeleteFileW(logPath);
    FILE*f=_wfopen(logPath,L"w"); if(!f) return;
    fprintf(f,"AOE2DE 101.103.54800.0 INTERNAL CAMERA RESOLVER RC6\n");
    fprintf(f,"MODE=READ_ONLY_SELF_PROCESS_WHOLE_DATA_SNAPSHOT\nBASE=0x%llX\n",(unsigned long long)(uintptr_t)exeBase);
    fprintf(f,"DATA_SCAN=0x%llX..0x%llX size=0x%llX\n",(unsigned long long)DATA_START,(unsigned long long)DATA_END,(unsigned long long)DATA_SIZE);
    fprintf(f,"CAM_CHAIN=global -> +0x28 -> camera +0x2F0/+0x2F4\nZOOM_MODE=WHOLE_DATA_FLOAT_DIFF\n\n");
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
    uintptr_t base=(uintptr_t)exeBase;
    uintptr_t start=base+DATA_START,end=base+DATA_END,p=start;
    while(p<end){
        MEMORY_BASIC_INFORMATION m;
        if(!VirtualQuery((void*)p,&m,sizeof(m))) return 0;
        uintptr_t rb=(uintptr_t)m.BaseAddress,re=rb+m.RegionSize;
        uintptr_t a=p>rb?p:rb, z=end<re?end:re;
        if(z>a && m.State==MEM_COMMIT && readable_protect(m.Protect)){
            CopyMemory(snap[idx]+(a-start),(void*)a,(SIZE_T)(z-a));
        }
        if(re<=p) break;
        p=re;
    }
    return 1;
}

static void baseline_cameras(void){
    uintptr_t b=(uintptr_t)exeBase;
    camCount=0;
    for(uint64_t off=0;off+8<=DATA_SIZE && camCount<MAX_CAM;off+=8){
        uintptr_t p0=*(uintptr_t*)(snap[0]+off);
        if(!plausible_ptr(p0)) continue;
        uintptr_t c=0;
        if(!ru64(p0+0x28,&c) || !plausible_ptr(c)) continue;
        float x=0,y=0;
        if(!rf32(c+0x2F0,&x)||!rf32(c+0x2F4,&y)||!mapish(x)||!mapish(y)) continue;
        Cam *q=&cams[camCount++];
        q->rva=(DWORD)(DATA_START+off); q->x[0]=x; q->y[0]=y; q->ok[0]=1; q->ok[1]=q->ok[2]=0;
    }
    (void)b;
}

static void resample_cameras(int idx){
    for(DWORD i=0;i<camCount;i++){
        float x,y;
        if(camread(cams[i].rva,&x,&y)){cams[i].x[idx]=x;cams[i].y[idx]=y;cams[i].ok[idx]=1;}
    }
}

static void keep_hit(Hit *arr,int *count,DWORD rva,float a,float b,float c,float score){
    if(*count<MAX_HITS){arr[*count].rva=rva;arr[*count].v[0]=a;arr[*count].v[1]=b;arr[*count].v[2]=c;arr[*count].score=score;(*count)++;return;}
    int mi=0; for(int i=1;i<MAX_HITS;i++) if(arr[i].score<arr[mi].score) mi=i;
    if(score>arr[mi].score){arr[mi].rva=rva;arr[mi].v[0]=a;arr[mi].v[1]=b;arr[mi].v[2]=c;arr[mi].score=score;}
}
static void sort_hits(Hit *a,int n){for(int i=0;i<n;i++)for(int j=i+1;j<n;j++)if(a[j].score>a[i].score){Hit t=a[i];a[i]=a[j];a[j]=t;}}

static void finish(FILE*f){
    DWORD cc=0;
    fprintf(f,"\n=== CAMERA_CHANGED ===\n");
    for(DWORD i=0;i<camCount;i++) if(cams[i].ok[0]&&cams[i].ok[1]&&cams[i].ok[2]){
        float d1=ab(cams[i].x[1]-cams[i].x[0])+ab(cams[i].y[1]-cams[i].y[0]);
        float d2=ab(cams[i].x[2]-cams[i].x[1])+ab(cams[i].y[2]-cams[i].y[1]);
        if(d1>.05f&&d2>.05f){
            fprintf(f,"CAM rva=0x%08X s1=(%.6f,%.6f) s2=(%.6f,%.6f) s3=(%.6f,%.6f) d1=%.6f d2=%.6f\n",
                cams[i].rva,cams[i].x[0],cams[i].y[0],cams[i].x[1],cams[i].y[1],cams[i].x[2],cams[i].y[2],d1,d2);
            cc++;
        }
    }
    fprintf(f,"CAMERA_BASELINE_COUNT=%u\nCAMERA_CHANGED_COUNT=%u\n",camCount,cc);

    Hit zh[MAX_HITS], gh[MAX_HITS]; int zn=0,gn=0; DWORD ztotal=0,gtotal=0;
    for(uint64_t off=0;off+4<=DATA_SIZE;off+=4){
        float a=*(float*)(snap[0]+off),b=*(float*)(snap[1]+off),c=*(float*)(snap[2]+off);
        if(!finiteish(a)||!finiteish(b)||!finiteish(c)) continue;
        float d1=b-a,d2=c-b,ad1=ab(d1),ad2=ab(d2);
        if(ad1>.002f&&ad2>.002f){
            float score=ad1+ad2;
            gtotal++; keep_hit(gh,&gn,(DWORD)(DATA_START+off),a,b,c,score);
            if(zoomish(a)&&zoomish(b)&&zoomish(c)&&d1*d2<0.0f){ztotal++;keep_hit(zh,&zn,(DWORD)(DATA_START+off),a,b,c,score);}
        }
    }
    sort_hits(zh,zn); sort_hits(gh,gn);
    fprintf(f,"\n=== ZOOM_REVERSAL_CANDIDATES_TOP ===\nZOOM_REVERSAL_TOTAL=%u\n",ztotal);
    for(int i=0;i<zn;i++) fprintf(f,"ZOOM rva=0x%08X s1=%.9f s2=%.9f s3=%.9f score=%.9f\n",zh[i].rva,zh[i].v[0],zh[i].v[1],zh[i].v[2],zh[i].score);
    fprintf(f,"ZOOM_TOP_COUNT=%d\n",zn);
    fprintf(f,"\n=== GENERAL_CHANGED_FLOATS_TOP ===\nGENERAL_CHANGED_TOTAL=%u\n",gtotal);
    for(int i=0;i<gn;i++) fprintf(f,"FLOAT rva=0x%08X s1=%.9f s2=%.9f s3=%.9f score=%.9f\n",gh[i].rva,gh[i].v[0],gh[i].v[1],gh[i].v[2],gh[i].score);
    fprintf(f,"GENERAL_TOP_COUNT=%d\nSTATUS=COMPLETE_SEND_THIS_FILE\n",gn);
}

static void snap_now(void){
    if(done||sampleNo>2) return;
    DWORD t=GetTickCount();
    int ok=capture_snapshot(sampleNo);
    if(ok){ if(sampleNo==0) baseline_cameras(); else resample_cameras(sampleNo); }
    FILE*f=_wfopen(logPath,L"a");
    if(f){
        fprintf(f,"SAMPLE_%d=%s elapsed_ms=%u cam=%u\n",sampleNo+1,ok?"PASS":"FAIL",GetTickCount()-t,camCount);
        if(ok&&sampleNo==2) finish(f);
        fclose(f);
    }
    MessageBeep(sampleNo==2?MB_ICONASTERISK:MB_OK);
    sampleNo++;
    if(sampleNo>=3) InterlockedExchange(&done,1);
}

static DWORD WINAPI worker(LPVOID x){
    (void)x; exeBase=GetModuleHandleW(NULL); initlog(); SHORT prev=0;
    for(;;){SHORT s=GetAsyncKeyState(VK_F11);if((s&0x8000)&&!(prev&0x8000)&&!done)snap_now();prev=s;Sleep(40);} return 0;
}
void resolver_start(void){
    if(InterlockedCompareExchange(&started,1,0)!=0) return;
    HANDLE h=CreateThread(NULL,0,worker,NULL,0,NULL); if(h) CloseHandle(h);
}
