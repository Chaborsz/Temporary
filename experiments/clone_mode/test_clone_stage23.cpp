// Native x86 mock tests for Endurance Stage22 integrated F6/F7 clone proxy.
#include "endurance_clone_stage23.cpp"
#include <cstdio>
#include <cmath>
static int setCount=0,addCount=0,removeCount=0;
static double lastValue=1000.0;
static void* lastObject=nullptr;
static double __fastcall OriginalSet(void*,void*,double v) {
    ++setCount;lastValue=v;return v+0.125;
}
static void __fastcall OriginalAdd(void*,void*,void* obj) {
    ++addCount;lastObject=obj;
}
static void __fastcall OriginalRemove(void*,void*,void* obj,bool,int,bool) {
    ++removeCount;lastObject=obj;
}
static bool CheckSet(uint32_t id,bool hasOwner,double requested,double expected) {
    BYTE var[0x70]={};
    BYTE owner[0x400]={};
    BYTE data[0x60]={};
    *reinterpret_cast<uint32_t*>(var+0x18)=id;
    *reinterpret_cast<uint32_t*>(data+0x18)=99; // not the original player
    *reinterpret_cast<void**>(owner+0x28c)=data;
    *reinterpret_cast<void**>(var+0x60)=hasOwner?owner:nullptr;
    const double result=InterceptSetValue(var,nullptr,requested);
    return std::fabs(lastValue-expected)<0.000001 &&
           std::fabs(result-(expected+0.125))<0.000001;
}
int main(){
    bool edge=false;
    if(ChordDown(false,false,true) || ChordDown(true,false,true) ||
       ChordDown(false,true,true) || !ChordDown(true,true,true))return 20;
    if(ChordEdge(ChordDown(false,false,true),edge)||edge)return 21;
    if(ChordEdge(ChordDown(true,false,true),edge)||edge)return 22;
    if(!ChordEdge(ChordDown(true,true,true),edge)||!edge)return 23;
    if(ChordEdge(ChordDown(true,true,true),edge))return 24;
    if(ChordEdge(false,edge)||edge)return 25;
    if(!ChordEdge(ChordDown(true,true,true),edge))return 26;
    std::printf("STAGE23_CHORD_GUARD_PASS ctrl_shift_f9_f10 edge_only; F6 absent\n");

    g_self=GetModuleHandleW(nullptr);
    g_trampolineSet=reinterpret_cast<BYTE*>(&OriginalSet);
    g_trampolineAdd=reinterpret_cast<BYTE*>(&OriginalAdd);
    g_trampolineRemove=reinterpret_cast<BYTE*>(&OriginalRemove);
    if(!CheckSet(2047,false,75.0,0.0))return 2;
    if(!CheckSet(2047,false,76.0,0.0))return 3;
    if(!CheckSet(2003,false,101.0,101.0))return 4;
    if(!CheckSet(2386,false,50.0,50.0))return 5;
    if(!CheckSet(2054,false,1.0,1.0))return 6;
    if(!CheckSet(2047,true,25.0,25.0))return 7;
    if(g_frozen2047!=2 || setCount!=6)return 8;
    BYTE layer[0x400]={};
    BYTE player[0x400]={};
    BYTE clone[0x400]={};
    BYTE playerData[0x80]={};
    BYTE cloneData[0x80]={};
    int sceneMarker=1;
    *reinterpret_cast<void**>(layer+0x290)=&sceneMarker;
    *reinterpret_cast<int*>(layer+0x2b8)=2;
    *reinterpret_cast<void**>(player+0x28c)=playerData;
    *reinterpret_cast<uint32_t*>(playerData+0x18)=1;
    *reinterpret_cast<void**>(clone+0x28c)=cloneData;
    *reinterpret_cast<uint32_t*>(cloneData+0x18)=1;
    InterceptAddObject(layer,nullptr,player);
    if(g_playerObject!=player || g_playerLayer!=layer ||
       g_playerScene!=&sceneMarker || addCount!=1)return 9;
    InterlockedExchange(&g_cloneBusy,1);
    InterceptAddObject(layer,nullptr,clone);
    InterlockedExchange(&g_cloneBusy,0);
    if(g_newClone!=clone || g_playerObject!=player || addCount!=2)return 10;
    g_clonedObject=clone;
    g_cloneInstance=1002;
    g_cloneScene=&sceneMarker;
    InterceptRemoveObject(layer,nullptr,clone,true,0,false);
    if(g_clonedObject!=nullptr || g_cloneInstance!=-1 ||
       g_playerObject!=player || removeCount!=1)return 11;
    InterceptRemoveObject(layer,nullptr,player,true,0,false);
    if(g_playerObject!=nullptr || g_playerLayer!=nullptr ||
       g_playerScene!=nullptr || removeCount!=2)return 12;
    std::printf("STAGE23_ENDURANCE_CLONE_TEST_PASS freeze2 passthrough4 add2 remove2\n");
    return 0;
}
