// Deterministic x86 test for read-only Endurance diagnostic interception.
#include "endurance_diagnostic_version.cpp"
#include <cstdio>
#include <cmath>

static volatile LONG g_originalCallCount=0;
static int g_lastOp=-1;
static double g_lastValue=0.0;
static void* g_lastVariable=nullptr;
static void __fastcall MockAssign(void*,void*,int op,void* variable,double value){
    InterlockedIncrement(&g_originalCallCount);
    g_lastOp=op;
    g_lastValue=value;
    g_lastVariable=variable;
}
static bool Trial(unsigned id,bool associated,int op,double amount) {
    BYTE variable[0x70]={};
    *reinterpret_cast<uint32_t*>(variable+0x18)=id;
    *reinterpret_cast<void**>(variable+0x60)=associated?
        reinterpret_cast<void*>(static_cast<uintptr_t>(0x4000)):nullptr;
    const LONG before=g_originalCallCount;
    InterceptAssign(reinterpret_cast<void*>(static_cast<uintptr_t>(0x2345)),
                    nullptr,op,variable,amount);
    return g_originalCallCount==before+1 && g_lastVariable==variable &&
        g_lastOp==op && std::fabs(g_lastValue-amount)<0.0001;
}
int main() {
    g_self=GetModuleHandleW(nullptr); // Logs written next to test executable.
    g_trampoline=reinterpret_cast<BYTE*>(&MockAssign);
    if(!Trial(2047,false,1,7.0))return 2;
    if(!Trial(2047,false,2,3.0))return 3;
    if(!Trial(2047,true,1,17.0))return 4;
    if(!Trial(2003,false,1,5.0))return 5;
    if(!Trial(2386,false,0,25.0))return 6;
    if(!Trial(2054,false,0,1.0))return 7;
    if(!Trial(91,false,3,4.0))return 8;
    if(g_seenTotal!=7 || g_seen2047!=3 || g_global2047!=2 ||
       g_object2047!=1 || g_seen2003!=1 || g_seen2386!=1 ||
       g_seen2054!=1 || g_seenOther!=1)return 9;
    std::printf("ENDURANCE_DIAG_PASSTHROUGH_PASS cases=7 global2047=2 object2047=1\n");
    return 0;
}
