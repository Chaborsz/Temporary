#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>

#define CAM_CENTER 0x0435A2F8ULL
#define CAM_RADIUS 0x00020000ULL
#define ZOOM_CENTER 0x040957D8ULL
#define ZOOM_RADIUS 0x00010000ULL
#define MAX_CAM 2048
#define MAX_ZOOM 8192

typedef struct{DWORD rva;float x[3],y[3];BYTE ok[3];}Cam;
typedef struct{DWORD rva;float v[3];BYTE ok[3];}Zoom;
static Cam cams[MAX_CAM];static DWORD camCount=0;
static Zoom zooms[MAX_ZOOM];static DWORD zoomCount=0;
static HMODULE exeBase=NULL;static wchar_t logPath[MAX_PATH+96];static volatile LONG started=0,done=0;static int sampleNo=0;

static int readable(const void*p,SIZE_T n){MEMORY_BASIC_INFORMATION m;if(!VirtualQuery(p,&m,sizeof(m)))return 0;if(m.State!=MEM_COMMIT)return 0;if(m.Protect&PAGE_GUARD)return 0;if((m.Protect&0xff)==PAGE_NOACCESS)return 0;uintptr_t a=(uintptr_t)p,e=a+n,b=(uintptr_t)m.BaseAddress,z=b+m.RegionSize;return e>=a&&a>=b&&e<=z;}
static int ru64(uintptr_t p,uintptr_t*out){if(!readable((void*)p,sizeof(uintptr_t)))return 0;*out=*(uintptr_t*)p;return 1;}
static int rf32(uintptr_t p,float*out){if(!readable((void*)p,4))return 0;*out=*(float*)p;return 1;}
static float ab(float v){return v<0?-v:v;}
static int mapish(float v){return v==v&&v>-32.0f&&v<1024.0f;}
static int zoomish(float v){return v==v&&v>=0.35f&&v<=2.5f;}
static int camread(DWORD rva,float*x,float*y){uintptr_t b=(uintptr_t)exeBase,p0=0,c=0;if(!ru64(b+rva,&p0))return 0;if(p0<0x10000ULL||p0>=0x0000800000000000ULL)return 0;if(!ru64(p0+0x28,&c))return 0;if(c<0x10000ULL||c>=0x0000800000000000ULL)return 0;if(!rf32(c+0x2F0,x)||!rf32(c+0x2F4,y))return 0;return mapish(*x)&&mapish(*y);}

static void initlog(void){wchar_t t[MAX_PATH];DWORD n=GetTempPathW(MAX_PATH,t);if(!n||n>=MAX_PATH)return;lstrcpynW(logPath,t,MAX_PATH+96);lstrcatW(logPath,L"AoE2DE_P3O_54800_InternalCameraResolver.txt");DeleteFileW(logPath);FILE*f=_wfopen(logPath,L"w");if(!f)return;fprintf(f,"AOE2DE 101.103.54800.0 INTERNAL CAMERA RESOLVER\nMODE=READ_ONLY_SELF_PROCESS\nBASE=0x%llX\nCAM_SCAN=0x%llX +/- 0x%llX\nZOOM_SCAN=0x%llX +/- 0x%llX\n\n",(unsigned long long)(uintptr_t)exeBase,(unsigned long long)CAM_CENTER,(unsigned long long)CAM_RADIUS,(unsigned long long)ZOOM_CENTER,(unsigned long long)ZOOM_RADIUS);fclose(f);}
static void baseline(void){uintptr_t b=(uintptr_t)exeBase;camCount=0;for(uintptr_t p=(b+CAM_CENTER-CAM_RADIUS+7)&~7ULL;p<b+CAM_CENTER+CAM_RADIUS&&camCount<MAX_CAM;p+=8){float x,y;DWORD r=(DWORD)(p-b);if(camread(r,&x,&y)){cams[camCount].rva=r;cams[camCount].x[0]=x;cams[camCount].y[0]=y;cams[camCount].ok[0]=1;camCount++;}}zoomCount=0;for(uintptr_t p=(b+ZOOM_CENTER-ZOOM_RADIUS+3)&~3ULL;p<b+ZOOM_CENTER+ZOOM_RADIUS&&zoomCount<MAX_ZOOM;p+=4){float v;if(rf32(p,&v)&&zoomish(v)){zooms[zoomCount].rva=(DWORD)(p-b);zooms[zoomCount].v[0]=v;zooms[zoomCount].ok[0]=1;zoomCount++;}}}
static void resample(int idx){uintptr_t b=(uintptr_t)exeBase;for(DWORD i=0;i<camCount;i++){float x,y;if(camread(cams[i].rva,&x,&y)){cams[i].x[idx]=x;cams[i].y[idx]=y;cams[i].ok[idx]=1;}}for(DWORD i=0;i<zoomCount;i++){float v;if(rf32(b+zooms[i].rva,&v)&&zoomish(v)){zooms[i].v[idx]=v;zooms[i].ok[idx]=1;}}}
static void finish(FILE*f){DWORD c=0,z=0;fprintf(f,"\n=== CAMERA_CHANGED ===\n");for(DWORD i=0;i<camCount;i++)if(cams[i].ok[0]&&cams[i].ok[1]&&cams[i].ok[2]){float d1=ab(cams[i].x[1]-cams[i].x[0])+ab(cams[i].y[1]-cams[i].y[0]);float d2=ab(cams[i].x[2]-cams[i].x[1])+ab(cams[i].y[2]-cams[i].y[1]);if(d1>.25f&&d2>.25f){fprintf(f,"CAM rva=0x%08X s1=(%.6f,%.6f) s2=(%.6f,%.6f) s3=(%.6f,%.6f)\n",cams[i].rva,cams[i].x[0],cams[i].y[0],cams[i].x[1],cams[i].y[1],cams[i].x[2],cams[i].y[2]);c++;}}fprintf(f,"CAMERA_CHANGED_COUNT=%u\n\n=== ZOOM_CHANGED ===\n",c);for(DWORD i=0;i<zoomCount;i++)if(zooms[i].ok[0]&&zooms[i].ok[1]&&zooms[i].ok[2]){float d1=ab(zooms[i].v[1]-zooms[i].v[0]),d2=ab(zooms[i].v[2]-zooms[i].v[1]);if(d1>.005f&&d2>.005f){fprintf(f,"ZOOM rva=0x%08X s1=%.9f s2=%.9f s3=%.9f\n",zooms[i].rva,zooms[i].v[0],zooms[i].v[1],zooms[i].v[2]);z++;}}fprintf(f,"ZOOM_CHANGED_COUNT=%u\nSTATUS=COMPLETE_SEND_THIS_FILE\n",z);}
static void snap(void){if(done||sampleNo>2)return;DWORD t=GetTickCount();if(sampleNo==0)baseline();else resample(sampleNo);FILE*f=_wfopen(logPath,L"a");if(f){fprintf(f,"SAMPLE_%d=PASS elapsed_ms=%u cam=%u zoom=%u\n",sampleNo+1,GetTickCount()-t,camCount,zoomCount);if(sampleNo==2)finish(f);fclose(f);}MessageBeep(sampleNo==2?MB_ICONASTERISK:MB_OK);sampleNo++;if(sampleNo>=3)InterlockedExchange(&done,1);}
static DWORD WINAPI worker(LPVOID x){(void)x;exeBase=GetModuleHandleW(NULL);initlog();SHORT prev=0;for(;;){SHORT s=GetAsyncKeyState(VK_F11);if((s&0x8000)&&!(prev&0x8000)&&!done)snap();prev=s;Sleep(40);}return 0;}
void resolver_start(void){if(InterlockedCompareExchange(&started,1,0)!=0)return;HANDLE h=CreateThread(NULL,0,worker,NULL,0,NULL);if(h)CloseHandle(h);}
