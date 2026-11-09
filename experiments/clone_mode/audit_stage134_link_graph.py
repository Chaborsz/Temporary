#!/usr/bin/env python3
"""FOBS Stage134 link graph: read-only, bounded original Build29 project analysis.
Reachable means static topology only; conditions and runtime may disable links.
"""
import collections,hashlib,ijson,json
from pathlib import Path
P=Path('/tmp/clone-control/project_decrypted.json')
assert P.stat().st_size==301997021
WATCH={1,72,103,158,195,218,219,239}
EFFECTS={2:'HP2',2003:'GLOBAL_2003',2044:'ENDURANCE_2044',2047:'GLOBAL_2047',
         2042:'ACTIONSTATE_2042',2001:'CAMDIR_2001',23:'HORIZMOVE_23'}
def attrs(c):
    arr=[]
    if not isinstance(c,dict):return arr
    for block,p in c.items():
        if not isinstance(p,dict):continue
        if block=='switchVariableChange':
            if p.get('swtch') is False:
                vid=p.get('variableId')
                if vid in EFFECTS:
                    arr.append((EFFECTS[vid],p.get('variableObjectId'),p.get('variableQualifierId'),p.get('variableAssignOperator')))
            else:
                if p.get('switchId') in (2021,2023,2041,2036):
                    arr.append(('SWITCH_'+str(p.get('switchId')),p.get('switchObjectId'),p.get('switchQualifierId'),None))
        if block=='objectMove':
            arr.append(('MOVE_TARGET',p.get('targetObjectId'),p.get('targetQualifierId'),p.get('targettingType')))
        if block=='actionExec':
            arr.append(('EXEC_TARGET',p.get('objectId'),p.get('qualifierId'),p.get('actionId')))
    return arr
with P.open('rb') as file:
 for obj in ijson.items(file,'objectList.item',use_float=False):
    oid=obj.get('id')
    if oid not in WATCH:continue
    actions={}
    for ac in obj.get('actionList',[]) or []:
        aid=ac.get('id')
        rows=[]
        for index,cmd in enumerate(ac.get('objCommandList',[]) or []):
            for typ,scope,q,oper in attrs(cmd):
                if (scope in (1,0) or typ in ('MOVE_TARGET','EXEC_TARGET') or typ.startswith('SWITCH_')):
                    rows.append({'i':index,'kind':typ,'scope':scope,'qualifier':q,'operator':oper})
        actions[aid]={'name':str(ac.get('name',''))[:38],'effects':rows}
    adj=collections.defaultdict(list)
    contacts=[]
    playerCondition=collections.Counter()
    for link in obj.get('actionLinkList',[]) or []:
        pair=link.get('typeIdPair')
        if not isinstance(pair,list) or len(pair)!=2:continue
        src,dst=pair[0][1],pair[1][1]
        adj[src].append((dst,link))
        details=[]
        for cond in link.get('linkConditionList',[]) or []:
            if not isinstance(cond,dict) or cond.get('ignored'):continue
            block=cond.get('attackAreaTouched') or cond.get('objectHit') or cond.get('objectWallTouched')
            if isinstance(block,dict):
                details.append({'type':cond.get('type'),'group':block.get('objectGroup'),
                  'id':block.get('objectId'),'by':block.get('objectTypeByType'),
                  'objectType':block.get('objectType')})
            for k,v in cond.items():
                if isinstance(v,dict) and (
                  v.get('variableObjectId')==1 or v.get('switchObjectId')==1 or
                  v.get('objectId')==1):
                    playerCondition[k]+=1
        if details:contacts.append({'src':src,'dst':dst,'link':link.get('id'),'contact':details})
    print('STAGE134_GRAPH_OWNER',oid, 'active_contact_links',len(contacts),'id1_condition_refs',json.dumps(playerCondition.most_common()))
    # List explicit contact links only when meaningful: group 0 / object 1; other groups shown separately.
    showing=[x for x in contacts if any(y['id'] in (1,-1) or y['group'] in (0,1) for y in x['contact'])][:9]
    print('STAGE134_GRAPH_CONTACT_EXAMPLES',oid,json.dumps(showing,ensure_ascii=False)[:2900])
    # BFS from each distinct contact destination; record shortest candidate path to each effect family.
    hitPaths={}
    for c in contacts:
        start=c['dst']
        work=collections.deque([(start,[c['src'],start])])
        seen={start}
        while work:
            u,path=work.popleft()
            eff=actions.get(u,{}).get('effects',[])
            for e in eff:
                key=(e['kind'],e['scope'])
                if key not in hitPaths or len(path)<len(hitPaths[key]['path']):
                    hitPaths[key]={'path':path,'link':c['link'],'contacts':c['contact'][:1],
                           'action':u,'name':actions.get(u,{}).get('name'),
                           'effect':e}
            if len(path)>=11:continue
            for v,link in adj.get(u,[]):
                if v not in seen:
                    seen.add(v)
                    work.append((v,path+[v]))
    wanted=[(k,v) for k,v in hitPaths.items() if
         k[0] in ('HP2','ENDURANCE_2044','GLOBAL_2047','GLOBAL_2003','CAMDIR_2001','MOVE_TARGET','EXEC_TARGET',
          'SWITCH_2021','SWITCH_2023','SWITCH_2041','ACTIONSTATE_2042')]
    wanted.sort(key=lambda x:(len(x[1]['path']),x[0]))
    print('STAGE134_GRAPH_SHORTEST',oid,json.dumps([{'effect':k,'path':v['path'],'link':v['link'],
             'action':v['action'],'command':v['effect'],'contact':v['contacts']}
           for k,v in wanted[:22]],ensure_ascii=False)[:14500])
    # Print immediate action details for entry branches.
    print('STAGE134_GRAPH_ENTRY_ACTIONS',oid,json.dumps([
       {'contact_link':c['link'],'src':c['src'],'dst':c['dst'],
       'source_effects':actions.get(c['src'],{}).get('effects',[])[:5],
       'dest_effects':actions.get(c['dst'],{}).get('effects',[])[:6]}
       for c in contacts[:5]],ensure_ascii=False)[:2800])
print('STAGE134_GRAPH_PASS')
