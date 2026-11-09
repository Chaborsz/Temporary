#!/usr/bin/env python3
"""Stage46: game object actions and real event-trigger conditions by object ID.
Read-only project schema, bounded console output.
"""
import ijson, collections,json
from pathlib import Path
src=Path("/tmp/clone-control/project_decrypted.json")
assert src.stat().st_size==301997021
selected={1,2,25,85,91,195}
with src.open("rb") as f:
 for obj in ijson.items(f,"objectList.item",use_float=False):
  id=obj.get("id")
  if id not in selected:continue
  counter=collections.Counter()
  references=collections.Counter()
  snippets=[]
  named=[]
  switchdefs={}
  for ac in obj.get("actionList",[]):
   for cmd in ac.get("objCommandList",[]):
    t=cmd.get("commandType","-")
    counter[t]+=1
    for typ,val in cmd.items():
     if not isinstance(val,dict):continue
     for k,v in val.items():
      if k in ("variableObjectId","assignVariableObjectId","switchObjectId",
       "objectId","targetObjectId","objectGroup","qualifierId",
       "variableQualifierId","assignVariableQualifierId","switchQualifierId","targetQualifierId"):
       references[(t,typ,k,str(v))]+=1
     if ("script" in typ.lower() or "switchvariable" in typ.lower() or
       "actionexec" in typ.lower()) and len(snippets)<12:
      snippets.append({"action_name":ac.get("name"),"action_id":ac.get("id"),
          "cmd_type":t,"fields":{k:str(v)[:200] for k,v in val.items() if
            any(z in k.lower() for z in ("object","qualifier","variable","script","switch","action","id","assign"))}})
   name=str(ac.get("name",""))
   if any(k in name.lower() for k in ("hit","attack","player","damage","rape","sex","ゲージ","ＨＰ","ダメージ","えっち","拘束","射精","吸収","ダウン","捕","当たり","興奮","性的")) and len(named)<70:
    named.append((ac.get("id"),name))
  linkcounts=collections.Counter()
  linkforeign=collections.Counter()
  linkhits=[]
  for link in obj.get("actionLinkList",[]):
   for cond in link.get("linkConditionList",[]):
    tp=cond.get("type","-")
    linkcounts[tp]+=1
    for k,v in cond.items():
     if not isinstance(v,dict):continue
     for attr,ref in v.items():
      if "objectId" in attr and str(ref) not in ("-1","-2","0"):
       linkforeign[(tp,k,attr,str(ref))]+=1
     if any(q in k.lower() for q in ("objecthit","wall","otherobject","switchvariable","attack","colli")):
      if len(linkhits)<8 and (id in (1,195) or tp!=17):
       linkhits.append({"link_id":link.get("id"),"link_type":link.get("changeConditionType"),
          "name":k,"type":tp,"params":{q:str(w)[:70] for q,w in list(v.items())[:20]}})
  print("S46_OBJECT",id,obj.get("name"),"actions",len(obj.get("actionList",[])),
    "commands",sum(counter.values()),"links",len(obj.get("actionLinkList",[])))
  print("S46_COMMAND_TYPES",id,counter.most_common(26))
  print("S46_LINK_TYPES",id,linkcounts.most_common(20))
  print("S46_REFERENCE_COUNTS",id,[(*key,n) for key,n in references.most_common(35)])
  print("S46_LINK_FOREIGN",id,[(*key,n) for key,n in linkforeign.most_common(25)])
  print("S46_NAMED_ACTIONS",id,json.dumps(named,ensure_ascii=False,default=str)[:6000])
  print("S46_COMMAND_SAMPLES",id,json.dumps(snippets[:12],ensure_ascii=False,default=str)[:8500])
  print("S46_LINK_SAMPLES",id,json.dumps(linkhits[:8],ensure_ascii=False,default=str)[:4600])
print("STAGE46_PROJECT_ACTION_AUDIT_PASS")

# Stage134: separate read-only native event chain audit using the same verified original inputs.
import runpy
runpy.run_path(str(Path(__file__).with_name('audit_stage134_full_chain.py')), run_name='__main__')

# Stage134: native graph from physical contact transitions to resource/movement actions.
runpy.run_path(str(Path(__file__).with_name('audit_stage134_link_graph.py')), run_name='__main__')

# Stage134 final pass: identify cross-object action execution (enemy -> ID1).
from collections import Counter
import ijson as _ij
_interest={1,72,103,158,195,218,219,239}
_actors={}
with src.open('rb') as _f:
    for _obj in _ij.items(_f,'objectList.item',use_float=False):
        if _obj.get('id') in _interest:
            _actors[_obj['id']]=_obj
_pact={x.get('id'):str(x.get('name',''))[:55] for x in _actors[1].get('actionList',[])}
for _id in (72,103,158,195,218,219,239):
    _obj=_actors[_id]
    _deleg=[]
    _moves=[]
    _damage=[]
    _paired=[]
    for _a in _obj.get('actionList',[]):
        _aid=_a.get('id')
        _states=[]
        _cond=[]
        for _i,_c in enumerate(_a.get('objCommandList',[]) or []):
            for _block,_p in _c.items():
                if not isinstance(_p,dict):continue
                if _block=='actionExec' and _p.get('objectId')==1:
                    _deleg.append({'from':_aid,'name':str(_a.get('name',''))[:45],
                     'command_i':_i,'target_action':_p.get('actionId'),
                     'target_action_name':_pact.get(_p.get('actionId')),
                     'qualifier':_p.get('qualifierId'),'fields':{k:v for k,v in _p.items()
                       if k in ('objectId','actionId','qualifierId','actionExecType')}})
                if _block=='objectMove' and _p.get('targetObjectId')==1:
                    _moves.append({'from':_aid,'name':str(_a.get('name',''))[:36],
                     'i':_i,'targetQualifierId':_p.get('targetQualifierId'),
                     'targettingType':_p.get('targettingType'),
                     'moveType':_p.get('moveType')})
                if _block=='switchVariableChange' and _p.get('swtch') is False:
                    _vid=_p.get('variableId'); _scope=_p.get('variableObjectId')
                    if (_vid,_scope) in {(2,1),(2044,1),(2047,0),(2003,0),
                                         (2042,1),(2001,1)}:
                        _states.append((_vid,_scope,_p.get('variableAssignOperator')))
                        if _vid==2 and _scope==1:
                            _damage.append({'from':_aid,'name':str(_a.get('name',''))[:40],
                               'i':_i,'op':_p.get('variableAssignOperator'),
                               'type':_p.get('variableAssignValueType'),
                               'value':str(_p.get('assignValue'))[:25],
                               'rhsobj':_p.get('assignVariableObjectId'),
                               'rhsid':_p.get('assignVariableId')})
        if len(set((v,scope) for v,scope,op in _states))>=3:
            _paired.append({'action':_aid,'name':str(_a.get('name',''))[:35],
                            'fields':_states[:16]})
    print('STAGE134_CROSS_EXEC',_id,json.dumps(_deleg,ensure_ascii=False)[:4800])
    print('STAGE134_CROSS_MOVES',_id,json.dumps(_moves,ensure_ascii=False)[:2800])
    print('STAGE134_CROSS_DAMAGE',_id,json.dumps(_damage,ensure_ascii=False)[:2400])
    print('STAGE134_CROSS_PAIRED',_id,json.dumps(_paired[:9],ensure_ascii=False)[:2900])
    for _aid in ([27,308,417,420,524] if _id in (103,158,195,218,219,239) else []):
        _match=[a for a in _obj.get('actionList',[]) if a.get('id')==_aid]
        if _match:
            _m=_match[0]
            print('STAGE134_ENTRY_DETAILS',_id,_aid,
              json.dumps({'name':str(_m.get('name'))[:60],
                 'commandCount':len(_m.get('objCommandList',[])),
                 'keys':list(_m.keys()),
                 'linksOut':sum(1 for l in _obj.get('actionLinkList',[])
                        if l.get('typeIdPair',[[],[]])[0][1]==_aid)},ensure_ascii=False)[:650])
print('STAGE134_CROSS_OBJECT_PASS')

# Stage135: Build29 ABI getter symbol verification (read-only).
