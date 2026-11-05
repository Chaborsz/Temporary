// x86 ABI safety test of the exact read-only Stage12 Endurance writer interceptors.
#include "endurance_writers_diagnostic.cpp"
#include <cstdio>
#include <cmath>
static double observedSet=-999.;
static double observedRequest=-999.;
static float observedDelay=-999.0f;
static int setCalls=0,reqCalls=0;
static void* lastObject=nullptr;
static double __fastcall MockSet(void* obj,void*,double v){
    ++setCalls;lastObject=obj;observedSet=v;return v+0.25;
}
static void __fastcall MockRequest(void* obj,void*,double v,float delay){
    ++reqCalls;lastObject=obj;observedRequest=v;observedDelay=delay;
}
static void configure(BYTE* buf,uint32_t id,bool hasObject){
    memset(buf,0,0x70);
    *reinterpret_cast<uint32_t*>(buf+0x18)=id;
    *reinterpret_cast<void**>(buf+0x60)=hasObject?
      reinterpret_cast<void*>(static_cast<uintptr_t>(0xC0FFEEu)):nullptr;
}
int main(){
    g_self=GetModuleHandleW(nullptr);
    g_trampolineSet=reinterpret_cast<BYTE*>(&MockSet);
    g_trampolineRequest=reinterpret_cast<BYTE*>(&MockRequest);
    BYTE data[0x70]={};
    configure(data,2047,false);
    double result=InterceptSetValue(data,nullptr,33.75);
    if(setCalls!=1||lastObject!=data||std::fabs(observedSet-33.75)>0.00001||
       std::fabs(result-34.0)>0.00001)return 2;
    InterceptRequestValue(data,nullptr,17.5,0.125f);
    if(reqCalls!=1||lastObject!=data||std::fabs(observedRequest-17.5)>0.00001||
       std::fabs(observedDelay-0.125f)>0.0001)return 3;
    configure(data,2047,true);
    InterceptSetValue(data,nullptr,5.);
    InterceptRequestValue(data,nullptr,6.,0.1f);
    configure(data,2003,false);
    InterceptSetValue(data,nullptr,100.);
    InterceptRequestValue(data,nullptr,50.,0.4f);
    configure(data,2386,false);
    InterceptSetValue(data,nullptr,12.);
    configure(data,2054,false);
    InterceptRequestValue(data,nullptr,1.,0.5f);
    configure(data,909,false);
    InterceptSetValue(data,nullptr,3.);
    InterceptRequestValue(data,nullptr,4.,0.2f);
    if(g_totalSet!=5||g_totalRequest!=5||g_set2047!=2||g_request2047!=2||
       g_set2047Global!=1||g_set2047Object!=1||
       g_request2047Global!=1||g_request2047Object!=1||
       g_set2003!=1||g_request2003!=1||g_set2386!=1||
       g_request2054!=1||g_setOther!=1||g_requestOther!=1)return 4;
    std::printf("ENDURANCE_WRITERS_READONLY_ABI_PASS set=5 request=5 input_preserved=10\n");
    return 0;
}
