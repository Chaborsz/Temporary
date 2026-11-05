// Stage13: test ONLY global 2047 is frozen; all other writes pass through.
#include "endurance_freeze2047_stage13.cpp"
#include <cstdio>
#include <cmath>

static volatile LONG g_calls=0;
static double g_lastValue=-1.0;
static void* g_lastVar=nullptr;
static double __fastcall MockOriginal(void* variable,void*,double requested){
    InterlockedIncrement(&g_calls);
    g_lastVar=variable;
    g_lastValue=requested;
    return requested+0.125;
}
static bool Check(uint32_t id,bool isObject,double supplied,double expected){
    BYTE var[0x70]={};
    *reinterpret_cast<uint32_t*>(var+0x18)=id;
    *reinterpret_cast<void**>(var+0x60)=isObject?
      reinterpret_cast<void*>(static_cast<uintptr_t>(0x1234)):nullptr;
    LONG before=g_calls;
    double returned=InterceptSetValue(var,nullptr,supplied);
    bool ok=g_calls==before+1 && g_lastVar==var &&
      std::fabs(g_lastValue-expected)<0.0000001 &&
      std::fabs(returned-(expected+0.125))<0.0000001;
    return ok;
}
int main(){
    g_self=GetModuleHandleW(nullptr);
    g_trampolineSet=reinterpret_cast<BYTE*>(&MockOriginal);
    if(!Check(2047,false,75.0,0.0))return 2;
    if(!Check(2047,false,76.0,0.0))return 3;
    if(!Check(2047,false,0.0,0.0))return 4;
    if(!Check(2047,true,75.0,75.0))return 5;
    if(!Check(2003,false,101.0,101.0))return 6;
    if(!Check(2386,false,-2.0,-2.0))return 7;
    if(!Check(2054,false,1.0,1.0))return 8;
    if(!Check(91,false,6.125,6.125))return 9;
    if(g_calls!=8 || g_seenSet!=8 || g_frozen2047!=3)return 10;
    std::printf("STAGE13_FREEZE2047_FILTER_PASS 8/8 writes, 3 frozen, 5 passthrough\n");
    return 0;
}
