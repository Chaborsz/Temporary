#!/usr/bin/env python3
"""Stage65 route matrix for independent clone feasibility (read-only).
Records exact original actions/commands referencing player ID 1 and critical
variables. A target reference is NOT necessarily damage or a write.
"""
import argparse,collections,csv,json
from pathlib import Path
import ijson
PLAYER_KEYS={"objectId","targetObjectId","variableObjectId","switchObjectId",
 "assignVariableObjectId","actionExecObjectId"}
CRITICAL={2003,2031,2044,2047}
FIELDS=["owner_object_id","owner_object_name","action_id","action_name",
 "command_index","command_type","block","field","target_id","qualifier_id",
 "switch_id","variable_id","operation","route_kind"]
CRIT_FIELDS=["owner_object_id","owner_object_name","action_id","action_name",
 "command_index","command_type","block","variable_id","variable_object_id",
 "variable_qualifier_id","variable_assign_operator","variable_assign_value_type",
 "assign_value","potential_write"]
def classifier(k):
 if k in ("objectId","targetObjectId"):return "object_selection_or_create"
 if k in ("variableObjectId","switchObjectId"):return "player_scoped_variable_or_switch"
 if k=="assignVariableObjectId":return "right_hand_side_variable"
 return "other_player_reference"
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--project",required=True);ap.add_argument("--out",required=True)
 opt=ap.parse_args();out=Path(opt.out);out.mkdir(exist_ok=True,parents=True)
 categories=collections.Counter();contexts=collections.Counter();critical_by_scope=collections.Counter()
 actor_counts=collections.Counter();crit_counts=collections.Counter()
 count_refs=0;count_critical=0
 with (out/"STAGE65_PLAYER_ID1_REFERENCES.csv").open("w",newline="",encoding="utf-8") as fref, \
      (out/"STAGE65_CRITICAL_VARIABLE_COMMANDS.csv").open("w",newline="",encoding="utf-8") as fcrit, \
      open(opt.project,"rb") as inp:
  wref=csv.DictWriter(fref,fieldnames=FIELDS);wref.writeheader()
  wcrit=csv.DictWriter(fcrit,fieldnames=CRIT_FIELDS);wcrit.writeheader()
  for obj in ijson.items(inp,"objectList.item",use_float=False):
   if not isinstance(obj,dict):continue
   oid=obj.get("id");oname=str(obj.get("name",""))[:130]
   for ac in obj.get("actionList",[]) or []:
    if not isinstance(ac,dict):continue
    aid=ac.get("id");aname=str(ac.get("name",""))[:135]
    for ci,cmd in enumerate(ac.get("objCommandList",[]) or []):
     if not isinstance(cmd,dict):continue
     ct=cmd.get("commandType")
     for block,par in cmd.items():
      if not isinstance(par,dict):continue
      for k,v in par.items():
       if k in PLAYER_KEYS and v==1:
        q=par.get(k.replace("ObjectId","QualifierId"),par.get("qualifierId",
                 par.get("variableQualifierId",par.get("switchQualifierId"))))
        kind=classifier(k)
        row={"owner_object_id":oid,"owner_object_name":oname,
         "action_id":aid,"action_name":aname,"command_index":ci,"command_type":ct,
         "block":block,"field":k,"target_id":v,"qualifier_id":q,
         "switch_id":par.get("switchId"),"variable_id":par.get("variableId"),
         "operation":par.get("variableAssignOperator"),"route_kind":kind}
        wref.writerow(row);count_refs+=1
        categories[kind]+=1;contexts[f"{block}.{k}"]+=1
        if oid!=1:actor_counts[str(oid)]+=1
      vid=par.get("variableId")
      if vid in CRITICAL:
       scope=par.get("variableObjectId")
       q=par.get("variableQualifierId")
       # A script edit of a variable uses commandType=31 with swtch=false.
       potential=(ct==31 and block=="switchVariableChange" and par.get("swtch") is False)
       row={"owner_object_id":oid,"owner_object_name":oname,
        "action_id":aid,"action_name":aname,"command_index":ci,"command_type":ct,
        "block":block,"variable_id":vid,"variable_object_id":scope,
        "variable_qualifier_id":q,"variable_assign_operator":par.get("variableAssignOperator"),
        "variable_assign_value_type":par.get("variableAssignValueType"),
        "assign_value":str(par.get("assignValue",""))[:60],
        "potential_write":int(potential)}
       wcrit.writerow(row);count_critical+=1
       critical_by_scope[(str(vid),str(scope),str(q),str(potential))]+=1
       crit_counts[str(oid)]+=1
 report={"count_player_refs":count_refs,"player_reference_classes_excluding_player":len(actor_counts),
         "id1_field_categories":categories.most_common(),
         "id1_parameter_fields":contexts.most_common(45),
         "top_actor_ids_explicit_id1":actor_counts.most_common(40),
         "critical_variable_commands":count_critical,
         "critical_by_id_scope_qualifier_write":critical_by_scope.most_common(70),
         "top_actor_ids_critical":crit_counts.most_common(30),
         "method":"project.json static, no claim each reference executes or causes damage",
         "legend":{"objectId=1":"script object type selection",
             "variableObjectId=1":"explicit player variable scope",
             "assignVariableObjectId=1":"read-side reference",
             "scope 0":"candidate shared/global, verify runtime",
             "scope -2":"candidate action owner/self, verify runtime"}}
 (out/"STAGE65_ROUTE_MATRIX_SUMMARY.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
 print("STAGE65_ROUTING_ROUTE_KINDS",json.dumps(categories.most_common()))
 print("STAGE65_ROUTING_TOP_FIELDS",json.dumps(contexts.most_common(25)))
 print("STAGE65_CRITICAL_SCOPE_TOP",json.dumps(critical_by_scope.most_common(22)))
 print("STAGE65_ROUTE_MATRIX_PASS",count_refs,count_critical)
if __name__=="__main__":main()
