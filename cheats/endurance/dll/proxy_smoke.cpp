#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winver.h>
#include <cstdio>
#include <vector>
#include <cwchar>

int wmain() {
    HMODULE proxy=LoadLibraryW(L".\\version.dll");
    if(!proxy){std::printf("FAIL PROXY_LOAD %lu\n",GetLastError());return 2;}
    const char* names[]={
        "GetFileVersionInfoSizeW","GetFileVersionInfoW","VerQueryValueW",
        "GetFileVersionInfoSizeA","GetFileVersionInfoA","VerQueryValueA",
        "GetFileVersionInfoSizeExW","GetFileVersionInfoSizeExA",
        "GetFileVersionInfoExW","GetFileVersionInfoExA"
    };
    for(const char* name:names){
        if(!GetProcAddress(proxy,name)){
            std::printf("FAIL EXPORT %s\n",name);return 3;
        }
    }
    typedef DWORD(WINAPI *SizeFn)(LPCWSTR,LPDWORD);
    typedef BOOL(WINAPI *InfoFn)(LPCWSTR,DWORD,DWORD,LPVOID);
    typedef BOOL(WINAPI *QueryFn)(LPCVOID,LPCWSTR,LPVOID*,PUINT);
    SizeFn size=reinterpret_cast<SizeFn>(GetProcAddress(proxy,"GetFileVersionInfoSizeW"));
    InfoFn info=reinterpret_cast<InfoFn>(GetProcAddress(proxy,"GetFileVersionInfoW"));
    QueryFn query=reinterpret_cast<QueryFn>(GetProcAddress(proxy,"VerQueryValueW"));
    WCHAR system[MAX_PATH]={};
    GetSystemDirectoryW(system,MAX_PATH);
    wcscat_s(system,L"\\kernel32.dll");
    DWORD handle=0;
    DWORD bytes=size(system,&handle);
    if(bytes==0 || bytes>1024*1024){
        std::printf("FAIL VERSION_SIZE size=%lu error=%lu\n",bytes,GetLastError());return 4;
    }
    std::vector<BYTE> buffer(bytes);
    if(!info(system,handle,bytes,buffer.data())){
        std::printf("FAIL VERSION_INFO err=%lu\n",GetLastError());return 5;
    }
    LPVOID value=nullptr;
    UINT length=0;
    if(!query(buffer.data(),L"\\",&value,&length)||!value||length<sizeof(VS_FIXEDFILEINFO)){
        std::printf("FAIL VERSION_QUERY err=%lu\n",GetLastError());return 6;
    }
    if(reinterpret_cast<VS_FIXEDFILEINFO*>(value)->dwSignature!=0xfeef04bd){
        std::printf("FAIL FIXED_INFO_SIGNATURE\n");return 7;
    }
    std::printf("VERSION_PROXY_FORWARD_SMOKE_PASS exports=10 version_length=%u\n",length);
    Sleep(600);
    FreeLibrary(proxy);
    return 0;
}
