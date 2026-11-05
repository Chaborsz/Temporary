// Headless x86 ABI + logic test, no game required and no runtime hook installed.
// Includes production source to test EXACT same InterceptAssign implementation.
#include "endurance2047_version.cpp"
#include <cstdio>
#include <cmath>

static void* observedThis=nullptr;
static void* observedVariable=nullptr;
static int observedOperator=-999;
static double observedValue=-999.0;
static int observedCalls=0;

static void __fastcall MockOriginal(void* manager,void* /*unused edx*/,
                                     int op,void* variable,double value) {
    observedThis=manager;
    observedVariable=variable;
    observedOperator=op;
    observedValue=value;
    observedCalls++;
}

static bool Test(void* self,void* var,int inputOp,double inputValue,
                 int expectedOp,double expectedValue) {
    observedOperator=-999;observedValue=-999.0;
    int before=observedCalls;
    InterceptAssign(self,nullptr,inputOp,var,inputValue);
    return observedCalls==before+1 && observedThis==self &&
           observedVariable==var && observedOperator==expectedOp &&
           std::fabs(observedValue-expectedValue)<1e-10;
}

int main() {
    g_trampoline=reinterpret_cast<BYTE*>(&MockOriginal);
    BYTE block[0x70]={};
    void* self=reinterpret_cast<void*>(static_cast<uintptr_t>(0x12345678));
    *reinterpret_cast<uint32_t*>(block+0x18)=2047;
    *reinterpret_cast<void**>(block+0x60)=nullptr;

    if(!Test(self,block,1,16.0,0,0.0)) {std::puts("FAIL global_2047_add");return 2;}
    if(!Test(self,block,2,16.0,0,0.0)) {std::puts("FAIL global_2047_subtract");return 3;}
    if(!Test(self,block,0,76.0,0,0.0)) {std::puts("FAIL global_2047_set");return 4;}
    *reinterpret_cast<uint32_t*>(block+0x18)=2003;
    if(!Test(self,block,1,16.0,1,16.0)) {std::puts("FAIL unrelated_2003");return 5;}
    *reinterpret_cast<uint32_t*>(block+0x18)=2054;
    if(!Test(self,block,2,16.0,2,16.0)) {std::puts("FAIL unrelated_2054");return 6;}
    *reinterpret_cast<uint32_t*>(block+0x18)=2047;
    *reinterpret_cast<void**>(block+0x60)=reinterpret_cast<void*>(static_cast<uintptr_t>(0x87654321));
    if(!Test(self,block,1,16.0,1,16.0)) {std::puts("FAIL object_scoped_2047");return 7;}
    if(!Test(self,nullptr,1,16.0,1,16.0)) {std::puts("FAIL null_variable_forward");return 8;}
    std::printf("ENDURANCE2047_HOOK_ABI_LOGIC_PASS scenarios=7 calls=%d\n",observedCalls);
    return 0;
}
