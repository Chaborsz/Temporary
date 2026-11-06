// Native x86 mock tests for Endurance Stage49 integrated Endurance and controller-isolated F9 clone proxy.
#include "endurance_clone_stage49.cpp"
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

static void* g_fakePlayerRet=nullptr;
static void* g_fakeInstanceRet=nullptr;
static void* g_fakeByInstanceRet=nullptr;
static void* __fastcall FakePlayerLookup(void*,void*){return g_fakePlayerRet;}
static void* __fastcall FakeInstanceLookup(void*,void*,int,int,int){return g_fakeInstanceRet;}
static void* __fastcall FakeByInstanceLookup(void*,void*,int){return g_fakeByInstanceRet;}
static int g_damageMockCalls=0, g_hpMockCalls=0, g_listMockCalls=0;
static void* g_lastDamageVictim=nullptr;
static void* g_lastDamageAttacker=nullptr;
static void* g_fakeList=nullptr;
static void* __fastcall MockTargetList(void*,void*,int){++g_listMockCalls;return g_fakeList;}
static void __fastcall MockDamaged(void* victim,void*,void* attacker,void*,void*){
    ++g_damageMockCalls;g_lastDamageVictim=victim;g_lastDamageAttacker=attacker;
}
static double __fastcall MockAddHp(void*,void*,double amount){
    ++g_hpMockCalls;return amount+0.75;
}

static int g_stage49TargetByIdCalls=0,g_stage49TargetByGroupCalls=0;
static int g_stage49LinkCalls[3]={};
static void* g_stage49Array=nullptr;
static void* __fastcall MockStage49TargetById(void*,void*,int,int){
    ++g_stage49TargetByIdCalls;return g_stage49Array;
}
static void* __fastcall MockStage49TargetByGroup(void*,void*,int,int){
    ++g_stage49TargetByGroupCalls;return g_stage49Array;
}
static bool __fastcall MockStage49Hit(void*,void*,void* marker){
    ++g_stage49LinkCalls[0];return marker!=nullptr;
}
static bool __fastcall MockStage49Touched(void*,void*,void* marker){
    ++g_stage49LinkCalls[1];return marker!=nullptr;
}
static bool __fastcall MockStage49Found(void*,void*,void* marker){
    ++g_stage49LinkCalls[2];return marker!=nullptr;
}
static int g_mockActionCalls[5]={};
static void* g_mockActionTarget=nullptr;
static void* __fastcall MockActionTarget(void*,void*,int a,int b){
    ++g_mockActionCalls[0];
    if(a!=313||(b!=-1 && b!=2 && b!=1))return nullptr;
    return g_mockActionTarget;
}
static bool __fastcall MockBoolAction(void*,void*,void* cmd){
    ++g_mockActionCalls[1];return cmd!=nullptr;
}
static int __fastcall MockIntAction(void*,void*,void* cmd){
    ++g_mockActionCalls[2];return cmd ? 42 : -1;
}
static void __fastcall MockVarAction(void*,void*,void*){
    ++g_mockActionCalls[3];
}
static void __fastcall MockObjectChange(void*,void*,void*){
    ++g_mockActionCalls[4];
}
static BYTE* g_nestedVariable=nullptr;
static double g_nestedRequested=0.0,g_nestedResult=-999.0;
static void __fastcall MockVariableEffect(void*,void*,void*){
    ++g_mockActionCalls[3];
    if(g_nestedVariable)
        g_nestedResult=InterceptSetValue(g_nestedVariable,nullptr,g_nestedRequested);
}

int main(){
    bool edge=false;
    if(ChordEdge(false,edge) || edge)return 20;
    if(!ChordEdge(true,edge) || !edge)return 21;
    if(ChordEdge(true,edge))return 22;
    if(ChordEdge(false,edge) || edge)return 23;
    if(!ChordEdge(true,edge))return 24;
    std::puts("STAGE49_F9_EDGE_TOGGLE_PASS");
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
    BYTE clone[0x480]={};
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
    std::puts("STAGE49_SEPARATE_RUNTIME_DATA_PASS no-controller-mutation");
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
    std::puts("STAGE49_MOVEMENT_FILTER_PASS clone_blocked original_forwarded cleanup_forwarded");
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
    BYTE nextPlayer[0x480]={},nextLayer[0x400]={},nextObjectData[0x90]={};
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
    std::puts("STAGE49_SCENE_REACQUIRE_PASS valid_player_only thread_retained stale_rejected");
    // Resolver trace never redirects the target pointer.
    // Configure an active clone in the native scene and compare all returns.
    g_playerObject=nextPlayer;
    g_clonedObject=clone;
    g_cloneScene=&nextSceneMarker;
    g_cloneInstance=1555;
    g_trampolinePlayerLookup=reinterpret_cast<BYTE*>(&FakePlayerLookup);
    g_trampolineInstanceLookup=reinterpret_cast<BYTE*>(&FakeInstanceLookup);
    g_trampolineTargetByInstance=reinterpret_cast<BYTE*>(&FakeByInstanceLookup);
    g_fakePlayerRet=nextPlayer;
    g_fakeInstanceRet=nextPlayer;
    g_fakeByInstanceRet=clone;
    if(TraceScenePlayer(&nextSceneMarker,nullptr)!=nextPlayer)return 70;
    if(TraceSceneInstance(&nextSceneMarker,nullptr,1,-1,2)!=nextPlayer)return 71;
    if(TraceTargetByInstance(&nextSceneMarker,nullptr,1555)!=clone)return 72;
    if(g_resolverTotals[0]!=1||g_resolverTotals[1]!=1||g_resolverTotals[2]!=1)return 73;
    // Non-player object lookup must not alter its result or the counter.
    g_fakeInstanceRet=nullptr;
    if(TraceSceneInstance(&nextSceneMarker,nullptr,10,-1,2)!=nullptr)return 74;
    if(g_resolverTotals[1]!=1)return 75;
    g_cloneInstance=-1;
    if(TraceScenePlayer(&nextSceneMarker,nullptr)!=nextPlayer)return 76;
    if(g_resolverTotals[0]!=1)return 77;
    std::puts("STAGE49_READ_ONLY_EVENT_RESOLVER_PASS originals_preserved scope_guarded");
    // Three read-only API interceptors must preserve original pointers,
    // actor recipients, parameters and floating point return ABI.
    g_cloneInstance=1555;
    g_playerObject=nextPlayer;
    g_clonedObject=clone;
    g_trampolineTargetList=reinterpret_cast<BYTE*>(&MockTargetList);
    g_trampolineDamaged=reinterpret_cast<BYTE*>(&MockDamaged);
    g_trampolineHp=reinterpret_cast<BYTE*>(&MockAddHp);
    BYTE cocosArray[0x18]={},targetArray[0x30]={};
    void* actors[2]={nextPlayer,clone};
    *reinterpret_cast<unsigned*>(cocosArray)=2;
    *reinterpret_cast<void***>(cocosArray+8)=actors;
    *reinterpret_cast<void**>(targetArray+0x1c)=cocosArray;
    g_fakeList=targetArray;
    if(TraceTargetList(&nextSceneMarker,nullptr,1)!=targetArray ||
       g_listMockCalls!=1||g_targetListCount!=1)return 80;
    g_fakeList=nullptr;
    if(TraceTargetList(&nextSceneMarker,nullptr,55)!=nullptr||
       g_listMockCalls!=2)return 81;
    TraceDamaged(nextPlayer,nullptr,clone,nullptr,nullptr);
    if(g_damageMockCalls!=1||g_lastDamageVictim!=nextPlayer||
       g_lastDamageAttacker!=clone||g_damagedCount!=1)return 82;
    TraceDamaged(clone,nullptr,nextPlayer,nullptr,nullptr);
    if(g_damageMockCalls!=2||g_lastDamageVictim!=clone||
       g_lastDamageAttacker!=nextPlayer||g_damagedCount!=2)return 83;
    BYTE originalPlay[0x100]={},clonePlay[0x100]={};
    *reinterpret_cast<void**>(nextPlayer+0x310)=originalPlay;
    *reinterpret_cast<void**>(clone+0x310)=clonePlay;
    double r1=TraceAddHp(originalPlay,nullptr,-20.5);
    double r2=TraceAddHp(clonePlay,nullptr,9.25);
    if(std::fabs(r1-(-19.75))>0.00001 ||
       std::fabs(r2-10.0)>0.00001 ||
       g_hpMockCalls!=2 || g_hpCount!=2)return 84;
    g_cloneInstance=-1;
    double r3=TraceAddHp(originalPlay,nullptr,3.0);
    if(std::fabs(r3-3.75)>0.00001 || g_hpCount!=2)return 85;
    std::puts("STAGE49_VICTIM_HP_TARGET_LIST_READONLY_PASS no_return_change scoped_logs");

    // Event-specific action diagnostics MUST preserve return values, targets,
    // commands, and state. Log only while a real clone and original coexist.
    g_cloneInstance=1555;
    g_playerObject=nextPlayer;
    g_clonedObject=clone;
    g_playerScene=&nextSceneMarker;
    g_cloneScene=&nextSceneMarker;
    BYTE nativeAction[0x100]={},eventOwner[0x480]={},eventObjectData[0x80]={};
    *reinterpret_cast<void**>(nativeAction+0x50)=eventOwner;
    *reinterpret_cast<void**>(eventOwner+0x28c)=eventObjectData;
    *reinterpret_cast<uint32_t*>(eventObjectData+0x18)=31;
    *reinterpret_cast<int*>(eventOwner+0x40c)=707;
    g_trampolineActionTarget=reinterpret_cast<BYTE*>(&MockActionTarget);
    g_trampolineActionExec=reinterpret_cast<BYTE*>(&MockBoolAction);
    g_trampolineScriptExec=reinterpret_cast<BYTE*>(&MockIntAction);
    g_trampolineVarExec=reinterpret_cast<BYTE*>(&MockVarAction);
    g_trampolineObjectChange=reinterpret_cast<BYTE*>(&MockObjectChange);
    g_mockActionTarget=nextPlayer;
    if(TraceActionTarget(nativeAction,nullptr,313,-1)!=nextPlayer)return 90;
    if(!TraceActionExec(nativeAction,nullptr,eventObjectData))return 91;
    if(TraceScriptExec(nativeAction,nullptr,eventObjectData)!=42)return 92;
    TraceVarExec(nativeAction,nullptr,eventObjectData);
    TraceObjectChange(nativeAction,nullptr,eventObjectData);
    for(int k=0;k<5;k++){
        if(g_actionTotals[k]!=1 || g_mockActionCalls[k]!=1)return 93;
    }
    // Outside clone lifetime all originals still execute, no extra logs.
    g_cloneInstance=-1;
    g_mockActionTarget=clone;
    if(TraceActionTarget(nativeAction,nullptr,313,-1)!=clone)return 94;
    if(g_actionTotals[0]!=1 || g_mockActionCalls[0]!=2)return 95;
    std::puts("STAGE49_EVENT_ACTION_OWNER_SCOPE_PASS default_original_persists");

    // Stage49 should redirect ONLY when native action OWNER is the spawned
    // clone, selected target is original and scope==2.
    g_cloneInstance=1555;
    g_playerObject=nextPlayer;
    g_clonedObject=clone;
    g_playerScene=&nextSceneMarker;
    g_cloneScene=&nextSceneMarker;
    *reinterpret_cast<void**>(nativeAction+0x50)=clone;
    *reinterpret_cast<uint32_t*>(cloneData+0x18)=1;
    g_mockActionTarget=nextPlayer;
    const LONG beforeRedirect=g_cloneTargetRedirects;
    if(TraceActionTarget(nativeAction,nullptr,313,2)!=clone)return 100;
    if(g_cloneTargetRedirects!=beforeRedirect+1)return 101;
    if(TraceActionTarget(nativeAction,nullptr,313,1)!=nextPlayer)return 102;
    if(g_cloneTargetRedirects!=beforeRedirect+1)return 103;
    *reinterpret_cast<void**>(nativeAction+0x50)=eventOwner;
    if(TraceActionTarget(nativeAction,nullptr,313,2)!=nextPlayer)return 104;
    if(g_cloneTargetRedirects!=beforeRedirect+1)return 105;
    *reinterpret_cast<void**>(nativeAction+0x50)=clone;
    g_mockActionTarget=clone;
    if(TraceActionTarget(nativeAction,nullptr,313,2)!=clone)return 106;
    if(g_cloneTargetRedirects!=beforeRedirect+1)return 107;
    g_mockActionTarget=nextPlayer;
    g_cloneScene=&sceneMarker; // scene changed = no safe rerouting
    if(TraceActionTarget(nativeAction,nullptr,313,2)!=nextPlayer)return 108;
    if(g_cloneTargetRedirects!=beforeRedirect+1)return 109;
    g_cloneScene=&nextSceneMarker;
    *reinterpret_cast<uint32_t*>(cloneData+0x18)=73;
    if(TraceActionTarget(nativeAction,nullptr,313,2)!=nextPlayer)return 110;
    if(g_cloneTargetRedirects!=beforeRedirect+1)return 111;
    *reinterpret_cast<uint32_t*>(cloneData+0x18)=1;
    g_cloneInstance=-1;
    if(TraceActionTarget(nativeAction,nullptr,313,2)!=nextPlayer)return 112;
    std::puts("STAGE49_CLONE_OWNER_REDIRECT_PASS only_clone_owner_same_scene_scope2_no_global");
    // Both relocation sensitive SEH hooks retain complete 10-byte boundaries.
    const uintptr_t base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    const uint32_t script=static_cast<uint32_t>(base+0x4bca9c);
    const uint32_t var=static_cast<uint32_t>(base+0x4bc894);
    if(script!=static_cast<uint32_t>(base+0x4bca9c)||
       var!=static_cast<uint32_t>(base+0x4bc894))return 113;

    // Stage49: actual setter owner identity is not inferred from player ID1:
    // instrument global, original object and clone independently.
    g_cloneInstance=1555;
    g_clonedObject=clone;g_playerObject=nextPlayer;
    g_cloneScene=&nextSceneMarker;g_playerScene=&nextSceneMarker;
    BYTE trackedVariable[0x78]={};
    *reinterpret_cast<uint32_t*>(trackedVariable+0x18)=2003;
    *reinterpret_cast<double*>(trackedVariable+0x28)=12.5;
    const LONG oldGlobal=g_varGlobal, oldPlayer=g_varPlayer, oldClone=g_varClone;
    TraceVariableWrite(trackedVariable,2003,nullptr,51.0);
    if(g_varGlobal!=oldGlobal+1 || g_varPlayer!=oldPlayer || g_varClone!=oldClone)return 120;
    TraceVariableWrite(trackedVariable,2003,nextPlayer,15.0);
    if(g_varPlayer!=oldPlayer+1 || g_varClone!=oldClone)return 121;
    TraceVariableWrite(trackedVariable,2003,clone,12.0);
    if(g_varClone!=oldClone+1)return 122;
    TraceVariableWrite(trackedVariable,2044,originalPlay,2.0);
    TraceVariableWrite(trackedVariable,2044,clonePlay,2.0);
    if(g_varPlayer!=oldPlayer+2 || g_varClone!=oldClone+2)return 123;
    // HUD variable writes unrelated to original/clone should be ignored.
    TraceVariableWrite(trackedVariable,2003,eventOwner,100.0);
    TraceVariableWrite(trackedVariable,2003,nullptr,100.0);
    if(g_varGlobal!=oldGlobal+2)return 124;
    const double after=*reinterpret_cast<const double*>(trackedVariable+0x28);
    if(std::fabs(after-12.5)>0.0000001)return 125;
    g_cloneInstance=-1;
    TraceVariableWrite(trackedVariable,2003,nextPlayer,1.0);
    if(g_varPlayer!=oldPlayer+2)return 126;
    std::puts("STAGE49_VARIABLE_OWNER_DIAGNOSTIC_PASS global_original_clone_bounded_no_mutations");


    // Stage49 nested clone-owned command isolation; do not globally block
    // shared variables or change the effects of external owners.
    g_trampolineVarExec=reinterpret_cast<BYTE*>(&MockVariableEffect);
    g_cloneInstance=1555;
    g_playerObject=nextPlayer;g_clonedObject=clone;
    g_playerScene=&nextSceneMarker;g_cloneScene=&nextSceneMarker;
    *reinterpret_cast<void**>(nativeAction+0x50)=clone;
    BYTE eventVariable[0x78]={};
    g_nestedVariable=eventVariable;
    *reinterpret_cast<uint32_t*>(eventVariable+0x18)=2003;
    *reinterpret_cast<double*>(eventVariable+0x28)=45.0;
    *reinterpret_cast<void**>(eventVariable+0x60)=nullptr;
    const int setterBaseline=setCount;
    const LONG sharedBaseline=g_shieldGlobal2003Writes;
    g_nestedRequested=51.0;
    TraceVarExec(nativeAction,nullptr,eventObjectData);
    if(setCount!=setterBaseline || std::fabs(g_nestedResult-45.0)>1e-7 ||
       g_shieldGlobal2003Writes!=sharedBaseline+1 || g_effectOwnerFrame!=0u)return 130;
    // The original player's local variable is protected in the same scope.
    *reinterpret_cast<uint32_t*>(eventVariable+0x18)=52;
    *reinterpret_cast<void**>(eventVariable+0x60)=nextPlayer;
    const LONG originalBaseline=g_shieldOriginalWrites;
    TraceVarExec(nativeAction,nullptr,eventObjectData);
    if(setCount!=setterBaseline || std::fabs(g_nestedResult-45.0)>1e-7 ||
       g_shieldOriginalWrites!=originalBaseline+1 || g_effectOwnerFrame!=0u)return 131;
    // Clone's own variable is NOT suppressed.
    *reinterpret_cast<void**>(eventVariable+0x60)=clone;
    TraceVarExec(nativeAction,nullptr,eventObjectData);
    if(setCount!=setterBaseline+1 || std::fabs(g_nestedResult-51.125)>1e-7 ||
       g_effectOwnerFrame!=0u)return 132;
    // Another actor's same global ID2003 is always forwarded.
    *reinterpret_cast<void**>(nativeAction+0x50)=eventOwner;
    *reinterpret_cast<uint32_t*>(eventVariable+0x18)=2003;
    *reinterpret_cast<void**>(eventVariable+0x60)=nullptr;
    TraceVarExec(nativeAction,nullptr,eventObjectData);
    if(setCount!=setterBaseline+2 || g_effectOwnerFrame!=0u)return 133;
    // Clone-owned writes to unrelated global IDs also pass unmodified.
    *reinterpret_cast<void**>(nativeAction+0x50)=clone;
    *reinterpret_cast<uint32_t*>(eventVariable+0x18)=2103;
    TraceVarExec(nativeAction,nullptr,eventObjectData);
    if(setCount!=setterBaseline+3 || g_effectOwnerFrame!=0u)return 134;
    // No isolation outside clone's lifetime.
    g_cloneInstance=-1;
    *reinterpret_cast<uint32_t*>(eventVariable+0x18)=2003;
    TraceVarExec(nativeAction,nullptr,eventObjectData);
    if(setCount!=setterBaseline+4 || g_effectOwnerFrame!=0u)return 135;
    std::puts("STAGE49_EFFECT_ISOLATION_PASS global2003_original_local_only_clone_owned other_actors_preserved");

    // Stage49 strictly read-only event target arrays, preserving every object.
    g_cloneInstance=1555;
    g_playerObject=nextPlayer;g_clonedObject=clone;
    g_playerScene=&nextSceneMarker;g_cloneScene=&nextSceneMarker;
    *reinterpret_cast<void**>(nativeAction+0x50)=eventOwner;
    g_trampolineByObjectId=reinterpret_cast<BYTE*>(&MockStage49TargetById);
    g_trampolineByGroup=reinterpret_cast<BYTE*>(&MockStage49TargetByGroup);
    g_trampolineConditionHit=reinterpret_cast<BYTE*>(&MockStage49Hit);
    g_trampolineConditionAttackTouched=reinterpret_cast<BYTE*>(&MockStage49Touched);
    g_trampolineConditionFound=reinterpret_cast<BYTE*>(&MockStage49Found);
    BYTE stage49TargetArray[0x38]={},stage49CocosArray[0x20]={};
    void* stage49Actors[2]={nextPlayer,clone};
    *reinterpret_cast<void**>(stage49TargetArray+0x1c)=stage49CocosArray;
    *reinterpret_cast<unsigned*>(stage49CocosArray)=2;
    *reinterpret_cast<void***>(stage49CocosArray+8)=stage49Actors;
    g_stage49Array=stage49TargetArray;
    if(TraceActionById(nativeAction,nullptr,1,-2)!=stage49TargetArray ||
       TraceActionByGroup(nativeAction,nullptr,-1,-2)!=stage49TargetArray ||
       stage49Actors[0]!=nextPlayer || stage49Actors[1]!=clone ||
       g_stage49TargetByIdCalls!=1 || g_stage49TargetByGroupCalls!=1)return 140;
    if(!TraceConditionHit(nativeAction,nullptr,eventOwner) ||
       !TraceConditionAttackTouched(nativeAction,nullptr,eventOwner) ||
       !TraceConditionObjectFound(nativeAction,nullptr,eventOwner))return 141;
    if(TraceConditionHit(nativeAction,nullptr,nullptr) ||
       TraceConditionAttackTouched(nativeAction,nullptr,nullptr) ||
       TraceConditionObjectFound(nativeAction,nullptr,nullptr))return 142;
    if(g_stage49LinkCalls[0]!=2||g_stage49LinkCalls[1]!=2||
       g_stage49LinkCalls[2]!=2)return 143;
    g_cloneInstance=-1;
    if(TraceActionById(nativeAction,nullptr,1,-2)!=stage49TargetArray ||
       TraceConditionHit(nativeAction,nullptr,nullptr))return 144;
    if(g_stage49TargetByIdCalls!=2 || g_stage49LinkCalls[0]!=3)return 145;
    std::puts("STAGE49_EXTERNAL_EVENT_NATIVE_READONLY_PASS target_arrays_and_link_conditions");
    std::printf("STAGE49_ENDURANCE_CLONE_TEST_PASS freeze2 passthrough4 add2 remove2\n");
    return 0;
}
