#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <wchar.h>

static volatile LONG g_started=0;
static wchar_t g_ini[MAX_PATH+64]={0};
static wchar_t g_log[MAX_PATH+96]={0};

static int sibling_path(wchar_t*out,unsigned cap,const wchar_t*name){
    DWORD n=GetModuleFileNameW(NULL,out,cap);
    if(!n||n>=cap)return 0;
    int i=(int)n-1;
    while(i>=0&&out[i]!=L'\\'&&out[i]!=L'/')i--;
    if(i<0)return 0;
    out[i+1]=0;
    if(lstrlenW(out)+lstrlenW(name)+1>=(int)cap)return 0;
    lstrcatW(out,name);
    return 1;
}

static void choose_ini(void){
    wchar_t p[MAX_PATH+64];
    if(sibling_path(p,MAX_PATH+64,L"AoE2DE_P3N.ini")&&GetFileAttributesW(p)!=INVALID_FILE_ATTRIBUTES){
        lstrcpynW(g_ini,p,MAX_PATH+64);return;
    }
    if(sibling_path(p,MAX_PATH+64,L"AoE2DE_P3O.ini")&&GetFileAttributesW(p)!=INVALID_FILE_ATTRIBUTES){
        lstrcpynW(g_ini,p,MAX_PATH+64);return;
    }
    sibling_path(g_ini,MAX_PATH+64,L"AoE2DE_P3N.ini");
}

static void init_log(void){
    wchar_t t[MAX_PATH];DWORD n=GetTempPathW(MAX_PATH,t);
    if(!n||n>=MAX_PATH)return;
    lstrcpynW(g_log,t,MAX_PATH+96);
    lstrcatW(g_log,L"AoE2DE_P3N_INI_SCHEMA_RC11_DIAG.txt");
    DeleteFileW(g_log);
}

static void write_utf8(FILE*f,const wchar_t*s){
    if(!f||!s)return;
    int need=WideCharToMultiByte(CP_UTF8,0,s,-1,NULL,0,NULL,NULL);
    if(need<=0)return;
    char*buf=(char*)HeapAlloc(GetProcessHeap(),0,(SIZE_T)need);
    if(!buf)return;
    if(WideCharToMultiByte(CP_UTF8,0,s,-1,buf,need,NULL,NULL)>0)fputs(buf,f);
    HeapFree(GetProcessHeap(),0,buf);
}

static void dump_one_section(FILE*f,const wchar_t*section){
    const DWORD CAP=262144;
    wchar_t*data=(wchar_t*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,(SIZE_T)CAP*sizeof(wchar_t));
    if(!data)return;
    DWORD n=GetPrivateProfileSectionW(section,data,CAP,g_ini);
    fputs("\n[",f);write_utf8(f,section);fputs("]\n",f);
    if(!n){fputs("<EMPTY_OR_UNREADABLE>\n",f);HeapFree(GetProcessHeap(),0,data);return;}
    unsigned count=0;
    for(wchar_t*p=data;*p;p+=lstrlenW(p)+1){
        write_utf8(f,p);fputc('\n',f);count++;
    }
    fprintf(f,";__ENTRY_COUNT=%u\n",count);
    HeapFree(GetProcessHeap(),0,data);
}

static DWORD WINAPI worker(LPVOID unused){
    (void)unused;
    Sleep(750);
    choose_ini();init_log();
    FILE*f=_wfopen(g_log,L"wb");
    if(!f)return 0;
    const unsigned char bom[3]={0xEF,0xBB,0xBF};fwrite(bom,1,3,f);
    fputs("AOE2DE 101.103.54800.0 P3N INI SCHEMA RC11 DIAG\n",f);
    fputs("MODE=READ_ONLY_CONFIG_DUMP\nONE_DLL=TRUE\nNO_GAME_MEMORY_WRITES=TRUE\n",f);
    fputs("INI_PATH=",f);write_utf8(f,g_ini);fputc('\n',f);
    DWORD attr=GetFileAttributesW(g_ini);
    fprintf(f,"INI_EXISTS=%d\n",attr!=INVALID_FILE_ATTRIBUTES);
    if(attr==INVALID_FILE_ATTRIBUTES){fclose(f);return 0;}

    const DWORD CAP=65536;
    wchar_t*sections=(wchar_t*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,(SIZE_T)CAP*sizeof(wchar_t));
    if(!sections){fclose(f);return 0;}
    DWORD n=GetPrivateProfileSectionNamesW(sections,CAP,g_ini);
    unsigned sectionCount=0;
    for(wchar_t*p=sections;*p;p+=lstrlenW(p)+1)sectionCount++;
    fprintf(f,"SECTION_COUNT=%u\n",sectionCount);
    fputs("SECTION_NAMES=",f);
    int first=1;
    for(wchar_t*p=sections;*p;p+=lstrlenW(p)+1){if(!first)fputs(" | ",f);write_utf8(f,p);first=0;}
    fputc('\n',f);
    for(wchar_t*p=sections;*p;p+=lstrlenW(p)+1)dump_one_section(f,p);
    HeapFree(GetProcessHeap(),0,sections);
    fputs("\nSTATUS=COMPLETE_SEND_THIS_FILE\n",f);
    fclose(f);
    MessageBeep(MB_OK);
    return 0;
}

void resolver_start(void){
    if(InterlockedCompareExchange(&g_started,1,0)!=0)return;
    HANDLE h=CreateThread(NULL,0,worker,NULL,0,NULL);
    if(h)CloseHandle(h);
}
