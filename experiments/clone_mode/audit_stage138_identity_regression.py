#!/usr/bin/env python3
"""FOBS Stage138 regression: original Build29 catalog identity, native object-change commands.
Read-only. Never modify or redistribute original project.
"""
import ijson, collections, json
from pathlib import Path
p=Path('/tmp/clone-control/project_decrypted.json')
assert p.stat().st_size==301997021
target={143,158}
objects={}
refs=collections.Counter();links=[];transitions=[]
with p.open('rb') as f:
  for obj in ijson.items(f,'objectList.item',use_float=False):
    oid=obj.get('id');name=str(obj.get('name',''))
    if oid in target:
      objects[oid]={'name':name,'group':obj.get('objectGroup'),
        'actions':len(obj.get('actionList',[]) or []),
        'links':len(obj.get('actionLinkList',[]) or [])}
    for ac in obj.get('actionList',[]) or []:
      aid=ac.get('id');aname=str(ac.get('name',''))[:55]
      for ix,cmd in enumerate(ac.get('objCommandList',[]) or []):
        for key,d in cmd.items():
          if not isinstance(d,dict):continue
          rel={k:v for k,v in d.items() if
               k in ('objectId','targetObjectId','actionExecObjectId','objectGroup',
                 'targettingType','targetQualifierId','qualifierId','actionId',
                 'changeType','objectChangeType','createType','newObjectId',
                 'afterObjectId','fromObjectId','toObjectId','objectIdBefore','objectIdAfter')
                 and isinstance(v,(str,bool,int,float))}
          if any(isinstance(v,int) and not isinstance(v,bool) and v in target for v in rel.values()):
            keyref=(str(oid),key)
            refs[keyref]+=1
            if len(transitions)<160:
              transitions.append({'owner':oid,'name':name[:48],'action':aid,
                  'action_name':aname,'i':ix,'cmd':cmd.get('commandType'),
                  'block':key,'args':rel})
          if oid in target and ('change' in key.lower() or 'create' in key.lower() or
                                'anim' in key.lower() or 'actionexec' in key.lower()):
            if len(links)<120:
              links.append({'owner':oid,'action':aid,'action_name':aname,
                 'index':ix,'command_type':cmd.get('commandType'),'block':key,
                 'args':rel})
print('STAGE138_IDENTITIES',json.dumps(objects,ensure_ascii=False))
print('STAGE138_CROSS_REFS',json.dumps(refs.most_common(40),ensure_ascii=False))
for x in transitions:
  if x['owner'] in target or x['block'].lower().find('change')>=0:
    print('STAGE138_CROSS_TRANSITION',json.dumps(x,ensure_ascii=False)[:1000])
print('STAGE138_SAMPLE_OTHER_REFS',json.dumps([v for v in transitions if v['owner'] not in target][:20],ensure_ascii=False)[:5500])
print('STAGE138_NATIVE_CHANGE_COMMAND_SAMPLES',json.dumps(links[:30],ensure_ascii=False)[:10000])
print('STAGE138_IDENTITY_AUDIT_PASS')
