// Native x86 mock tests for Endurance Stage34 integrated Endurance and controller-isolated F9 clone proxy.
#include "endurance_clone_stage34.cpp"
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
static int __fastcall FakeControllerGet(void* obj,void*){
    void* play=*reinterpret_cast<void**>(static_cast<BYTE*>(obj)+0x310);
    if(!play)return -1;
    return *reinterpret_cast<int*>(static_cast<BYTE*>(play)+0x20);
}
static int movementRealCalls=0;
static GameVec2* __fastcall MockMovement(void*,void*,GameVec2* output,float delta){
    ++movementRealCalls;
    if(output){
        output->x=delta*100.0f;
        output->y=delta*200.0f;
    }
    return output;
}

int main(){
    bool edge=false;
    if(ChordEdge(false,edge) || edge)return 20;
    if(!ChordEdge(true,edge) || !edge)return 21;
    if(ChordEdge(true,edge))return 22;
    if(ChordEdge(false,edge) || edge)return 23;
    if(!ChordEdge(true,edge))return 24;
    std::puts("STAGE34_F9_EDGE_TOGGLE_PASS");
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
    // Original and clone remain separate without changing either controller.
    BYTE playerRuntime[0x80]={},cloneRuntime[0x80]={};
    *reinterpret_cast<void**>(player+0x310)=playerRuntime;
    *reinterpret_cast<void**>(clone+0x310)=cloneRuntime;
    *reinterpret_cast<int*>(playerRuntime+0x20)=-1;
    *reinterpret_cast<int*>(cloneRuntime+0x20)=-1;
    if(!CheckCloneSeparateData(player,clone,
      reinterpret_cast<GetObjectControllerId>(&FakeControllerGet)))return 30;
    if(*reinterpret_cast<int*>(playerRuntime+0x20)!=-1 ||
       *reinterpret_cast<int*>(cloneRuntime+0x20)!=-1)return 31;
    *reinterpret_cast<void**>(clone+0x310)=playerRuntime;
    if(CheckCloneSeparateData(player,clone,
      reinterpret_cast<GetObjectControllerId>(&FakeControllerGet)))return 32;
    *reinterpret_cast<void**>(clone+0x310)=cloneRuntime;
    *reinterpret_cast<int*>(playerRuntime+0x20)=1;
    *reinterpret_cast<int*>(cloneRuntime+0x20)=3;
    if(!CheckCloneSeparateData(player,clone,
      reinterpret_cast<GetObjectControllerId>(&FakeControllerGet)))return 33;
    if(*reinterpret_cast<int*>(playerRuntime+0x20)!=1 ||
       *reinterpret_cast<int*>(cloneRuntime+0x20)!=3)return 34;
    std::puts("STAGE34_SEPARATE_RUNTIME_DATA_PASS no-controller-mutation");
    // Native ObjectMovement::move by-value cocos2d::Vec2 (hidden sret) ABI tests.
    g_trampolineMove=reinterpret_cast<BYTE*>(&MockMovement);
    BYTE originalMover[0x40]={},cloneMover[0x40]={};
    *reinterpret_cast<void**>(originalMover+0x18)=player;
    *reinterpret_cast<void**>(cloneMover+0x18)=clone;
    GameVec2 movementResult={9.0f,9.0f};
    if(InterceptMovement(originalMover,nullptr,&movementResult,0.5f)!=&movementResult ||
       movementRealCalls!=1 || movementResult.x!=50.0f ||
       movementResult.y!=100.0f)return 40;
    g_clonedObject=clone;g_cloneInstance=1002;
    movementResult={9.0f,9.0f};
    if(InterceptMovement(cloneMover,nullptr,&movementResult,0.5f)!=&movementResult ||
       movementRealCalls!=1 || movementResult.x!=0.0f ||
       movementResult.y!=0.0f || g_cloneMoveSuppressed!=1)return 41;
    g_clonedObject=nullptr;g_cloneInstance=-1;
    movementResult={9.0f,9.0f};
    if(InterceptMovement(cloneMover,nullptr,&movementResult,0.25f)!=&movementResult ||
       movementRealCalls!=2 || movementResult.x!=25.0f ||
       movementResult.y!=50.0f)return 42;
    std::puts("STAGE34_MOVEMENT_FILTER_PASS clone_blocked original_forwarded cleanup_forwarded");
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
    // Simulate a new active scene: native Scene::getObjectPlayer() resolves
    // another player instance without an addObject call on our intercepted layer.
    BYTE nextPlayer[0x400]={},nextLayer[0x400]={},nextObjectData[0x90]={};
    int nextSceneMarker=2;
    *reinterpret_cast<void**>(nextPlayer+0x28c)=nextObjectData;
    *reinterpret_cast<uint32_t*>(nextObjectData+0x18)=1;
    *reinterpret_cast<void**>(nextPlayer+0x308)=nextLayer;
    *reinterpret_cast<void**>(nextLayer+0x290)=&nextSceneMarker;
    *reinterpret_cast<int*>(nextLayer+0x2b8)=3;
    if(AdoptScenePlayer(&sceneMarker,nextPlayer))return 50;
    if(g_playerObject || g_playerLayer || g_playerScene)return 51;
    if(!AdoptScenePlayer(&nextSceneMarker,nextPlayer))return 52;
    if(g_playerObject!=nextPlayer || g_playerLayer!=nextLayer ||
       g_playerScene!=&nextSceneMarker ||
       g_playerThread!=GetCurrentThreadId())return 53;
    // A cloned actor must never replace the scene player.
    g_clonedObject=clone;
    *reinterpret_cast<void**>(clone+0x308)=nextLayer;
    if(AdoptScenePlayer(&nextSceneMarker,clone))return 54;
    if(g_playerObject!=nextPlayer)return 55;
    g_clonedObject=nullptr;
    *reinterpret_cast<uint32_t*>(nextObjectData+0x18)=73;
    if(AdoptScenePlayer(&nextSceneMarker,nextPlayer))return 56;
    *reinterpret_cast<uint32_t*>(nextObjectData+0x18)=1;
    // Removing player clears actor pointers yet preserves known game-thread identity.
    InterceptRemoveObject(nextLayer,nullptr,nextPlayer,true,0,false);
    if(g_playerObject || g_playerLayer || g_playerScene ||
       g_playerThread!=GetCurrentThreadId())return 57;
    std::puts("STAGE34_SCENE_REACQUIRE_PASS valid_player_only thread_retained stale_rejected");
    std::printf("STAGE34_ENDURANCE_CLONE_TEST_PASS freeze2 passthrough4 add2 remove2\n");
    return 0;
}
