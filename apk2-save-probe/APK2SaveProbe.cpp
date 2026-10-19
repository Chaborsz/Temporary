#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <bcrypt.h>
#include <cstdio>
#include <cstdint>
#include <vector>
#include <string>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <array>
#pragma comment(lib, "bcrypt.lib")

static FILE* gLog=nullptr;
static void logf(const char* fmt, ...) {
    va_list ap; va_start(ap,fmt); vprintf(fmt,ap); va_end(ap);
    if(gLog){ va_start(ap,fmt); vfprintf(gLog,fmt,ap); va_end(ap); fflush(gLog); }
}

static DWORD find_process(const wchar_t* exe) {
    PROCESSENTRY32W e{sizeof(e)};
    HANDLE s=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
    if(s==INVALID_HANDLE_VALUE) return 0;
    DWORD pid=0;
    if(Process32FirstW(s,&e)) do { if(_wcsicmp(e.szExeFile,exe)==0){pid=e.th32ProcessID;break;} } while(Process32NextW(s,&e));
    CloseHandle(s); return pid;
}

static uintptr_t find_module_base(DWORD pid,const wchar_t* exe) {
    MODULEENTRY32W e{sizeof(e)};
    HANDLE s=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32,pid);
    if(s==INVALID_HANDLE_VALUE) return 0;
    uintptr_t b=0;
    if(Module32FirstW(s,&e)) do { if(_wcsicmp(e.szModule,exe)==0){b=(uintptr_t)e.modBaseAddr;break;} } while(Module32NextW(s,&e));
    CloseHandle(s); return b;
}

static bool readable(DWORD p){
    if(p & PAGE_GUARD) return false;
    p &= 0xff;
    return p==PAGE_READONLY || p==PAGE_READWRITE || p==PAGE_WRITECOPY || p==PAGE_EXECUTE_READ || p==PAGE_EXECUTE_READWRITE || p==PAGE_EXECUTE_WRITECOPY;
}

static std::string hex(const uint8_t* p,size_t n){
    std::ostringstream o; o<<std::hex<<std::setfill('0');
    for(size_t i=0;i<n;i++) o<<std::setw(2)<<(unsigned)p[i];
    return o.str();
}

static const uint8_t sbox[256] = {
0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16};
static const uint8_t rcon[8]={0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40};

static void aes256_expand(const uint8_t key[32], uint8_t out[240]){
    memcpy(out,key,32); int bytes=32; int rc=1; uint8_t t[4];
    while(bytes<240){
        memcpy(t,out+bytes-4,4);
        if(bytes%32==0){ uint8_t q=t[0]; t[0]=sbox[t[1]]^rcon[rc++]; t[1]=sbox[t[2]]; t[2]=sbox[t[3]]; t[3]=sbox[q]; }
        else if(bytes%32==16){ for(int i=0;i<4;i++) t[i]=sbox[t[i]]; }
        for(int i=0;i<4 && bytes<240;i++){ out[bytes]=out[bytes-32]^t[i]; bytes++; }
    }
}

static bool schedule_match(const uint8_t* p){
    uint8_t e[240]; aes256_expand(p,e); return memcmp(e,p,240)==0;
}

static bool bcrypt_decrypt_first(const uint8_t key[32], const uint8_t ct[16], uint8_t pt[16]){
    BCRYPT_ALG_HANDLE a=nullptr; BCRYPT_KEY_HANDLE k=nullptr; DWORD cb=0,objlen=0,outn=0; std::vector<uint8_t> obj;
    if(BCryptOpenAlgorithmProvider(&a,BCRYPT_AES_ALGORITHM,nullptr,0)<0) return false;
    BCryptSetProperty(a,BCRYPT_CHAINING_MODE,(PUCHAR)BCRYPT_CHAIN_MODE_ECB,sizeof(BCRYPT_CHAIN_MODE_ECB),0);
    if(BCryptGetProperty(a,BCRYPT_OBJECT_LENGTH,(PUCHAR)&objlen,sizeof(objlen),&cb,0)<0){BCryptCloseAlgorithmProvider(a,0);return false;}
    obj.resize(objlen);
    if(BCryptGenerateSymmetricKey(a,&k,obj.data(),objlen,(PUCHAR)key,32,0)<0){BCryptCloseAlgorithmProvider(a,0);return false;}
    NTSTATUS st=BCryptDecrypt(k,(PUCHAR)ct,16,nullptr,nullptr,0,pt,16,&outn,0);
    BCryptDestroyKey(k); BCryptCloseAlgorithmProvider(a,0); return st>=0 && outn==16;
}

static bool read_file(const wchar_t* p,std::vector<uint8_t>& b){
    std::ifstream f(p,std::ios::binary); if(!f)return false; b.assign(std::istreambuf_iterator<char>(f),{}); return true;
}

static void dump_module_metadata(HANDLE hp,uintptr_t base){
    const uintptr_t rvas[]={0xa1d45f8,0xa1dead0,0xa1dea78,0xa1dee08,0xb1edee0,0xa1d45d0};
    logf("\n[metadata]\n");
    for(auto r:rvas){ uint8_t b[128]{}; SIZE_T got=0; bool ok=ReadProcessMemory(hp,(LPCVOID)(base+r-32),b,sizeof(b),&got)!=0; logf("RVA 0x%llx VA 0x%llx read=%d bytes=%llu\n",(unsigned long long)r,(unsigned long long)(base+r),ok?1:0,(unsigned long long)got); if(ok) logf("  around=%s\n",hex(b,got).c_str()); }
}

int wmain(int argc,wchar_t** argv){
    const wchar_t* save = argc>=2 ? argv[1] : L"DefaultData.sav";
    gLog=_wfopen(L"APK2_SaveProbe.txt",L"wb");
    logf("APK2 Save Probe v1 - read-only process inspection\n");
    std::vector<uint8_t> sav; if(!read_file(save,sav) || sav.size()<16){logf("ERROR: cannot read save path or <16 bytes. Pass path as first argument.\n");return 2;}
    uint8_t ct[16]; memcpy(ct,sav.data(),16); logf("save_size=%llu first16=%s\n",(unsigned long long)sav.size(),hex(ct,16).c_str());
    DWORD pid=find_process(L"APK2-Win64-Shipping.exe"); if(!pid){logf("ERROR: game process not found. Start game first.\n");return 3;}
    uintptr_t base=find_module_base(pid,L"APK2-Win64-Shipping.exe"); logf("pid=%lu module_base=0x%llx\n",pid,(unsigned long long)base);
    HANDLE hp=OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ,FALSE,pid); if(!hp){logf("ERROR OpenProcess=%lu (try Run as Administrator)\n",GetLastError());return 4;}
    if(base) dump_module_metadata(hp,base);

    SYSTEM_INFO si{}; GetSystemInfo(&si); uintptr_t p=(uintptr_t)si.lpMinimumApplicationAddress, max=(uintptr_t)si.lpMaximumApplicationAddress;
    MEMORY_BASIC_INFORMATION mbi{}; size_t regions=0,bytes=0,gvas=0,cthits=0,schedules=0,validkeys=0; const size_t MAXREG=256ull<<20;
    while(p<max && VirtualQueryEx(hp,(LPCVOID)p,&mbi,sizeof(mbi))==sizeof(mbi)){
        uintptr_t next=p+mbi.RegionSize; if(next<=p)break;
        if(mbi.State==MEM_COMMIT && readable(mbi.Protect) && mbi.RegionSize>0 && mbi.RegionSize<=MAXREG){
            std::vector<uint8_t> b((size_t)mbi.RegionSize); SIZE_T got=0;
            if(ReadProcessMemory(hp,mbi.BaseAddress,b.data(),b.size(),&got) && got){ b.resize(got); regions++; bytes+=got;
                for(size_t i=0;i+4<=b.size();i++){ if(b[i]=='G'&&b[i+1]=='V'&&b[i+2]=='A'&&b[i+3]=='S'){gvas++; logf("GVAS_HIT va=0x%llx protect=0x%lx regionType=0x%lx prefix=%s\n",(unsigned long long)((uintptr_t)mbi.BaseAddress+i),mbi.Protect,mbi.Type,hex(b.data()+i,std::min<size_t>(64,b.size()-i)).c_str());} }
                for(size_t i=0;i+16<=b.size();i++){ if(memcmp(b.data()+i,ct,16)==0){cthits++; logf("CIPHERTEXT_HIT va=0x%llx protect=0x%lx type=0x%lx\n",(unsigned long long)((uintptr_t)mbi.BaseAddress+i),mbi.Protect,mbi.Type);} }
                // AES-256 expanded schedules are normally 16-byte aligned; also test 4-byte alignment for robustness.
                for(size_t i=0;i+240<=b.size();i+=4){ if(schedule_match(b.data()+i)){ schedules++; uint8_t pt[16]{}; bool ok=bcrypt_decrypt_first(b.data()+i,ct,pt); logf("AES256_SCHEDULE va=0x%llx key=%s firstdec=%s\n",(unsigned long long)((uintptr_t)mbi.BaseAddress+i),hex(b.data()+i,32).c_str(), ok?hex(pt,16).c_str():"<bcrypt-failed>"); if(ok&&memcmp(pt,"GVAS",4)==0){validkeys++; logf("*** VALID_SAVE_KEY key=%s ***\n",hex(b.data()+i,32).c_str());} } }
            }
        }
        p=next;
    }
    logf("\nSUMMARY regions=%llu bytes=%llu GVAS_hits=%llu ciphertext_hits=%llu AES256_schedules=%llu valid_save_keys=%llu\n",(unsigned long long)regions,(unsigned long long)bytes,(unsigned long long)gvas,(unsigned long long)cthits,(unsigned long long)schedules,(unsigned long long)validkeys);
    CloseHandle(hp); if(gLog)fclose(gLog); return 0;
}
