#!/usr/bin/env python3
"""Stage 9: build a reversible, isolated AGTK project.json trial that freezes
global temptation gauge ID 2047 to zero. Original input remains untouched.

This is a TEST CANDIDATE, not runtime-verified. Other global variables, including
HP/MP and the ejaculation gauge, are deliberately excluded.
"""
from __future__ import annotations
import argparse,hashlib,json,mmap,re,shutil,struct,tempfile,zipfile
from collections import Counter
from pathlib import Path
import ijson
from decode_project_weakfish import IV,weak_encrypt,weak_decrypt,xor16

EXPECTED_SHA="2a19596ffc6e54c4651780ad9ee0ab37dc98d4b6a0a979d63ec2b32523e1af89"
EXPECTED_SIZE=301997021
SETTING=re.compile(
    rb'("variableId"\s*:\s*2047\s*,\s*"variableAssignOperator"\s*:\s*)'
    rb'(-?\d+)(\s*,\s*"variableAssignValueType"\s*:\s*)'
    rb'(-?\d+)(\s*,\s*"assignValue"\s*:\s*)'
    rb'(-?\d+(?:\.\d+)?)(\s*,)')
GLOBAL_OWNER=re.compile(
    rb'"variableObjectId"\s*:\s*0\s*,\s*"variableQualifierId"\s*:\s*-?\d+\s*,\s*$')

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def collect(p):
    found=[]
    patches=[]
    counts=Counter()
    with p.open("rb") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
        for m in SETTING.finditer(mm):
            back=mm[max(0,m.start()-225):m.start()]
            if not GLOBAL_OWNER.search(back):
                counts["non_global_id2047_ignored"]+=1
                continue
            counts["global_2047_setter_matches"]+=1
            fields=(("assignment_operator",2),("value_type",4),("assigned_numeric_value",6))
            for label,group in fields:
                start,end=m.span(group)
                raw=m.group(group)
                substitute=b"0" + b" "*(len(raw)-1)
                if substitute != raw:
                    patches.append((start,end,raw,substitute,label))
                    counts[label+"_modified"]+=1
            if len(found)<20:
                found.append({"offset":m.start(),"op":m.group(2).decode(),
                              "type":m.group(4).decode(),
                              "value":m.group(6).decode()})
    patches.sort()
    for a,b in zip(patches,patches[1:]):
        if b[0]<a[1]:
            raise RuntimeError("Overlapping edits")
    if counts["global_2047_setter_matches"]<1000:
        raise RuntimeError("Insufficient proven ID2047 setters; refusing to patch.")
    return patches,counts,found

def apply(source,destination,patches):
    h=hashlib.sha256()
    with source.open("rb") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm, destination.open("wb") as w:
        frompos=0
        for start,end,original,replacement,_ in patches:
            if mm[start:end] != original or len(replacement)!=end-start:
                raise RuntimeError("Patch preimage mismatch")
            part=memoryview(mm)[frompos:start]
            w.write(part);h.update(part);del part
            w.write(replacement);h.update(replacement)
            frompos=end
        part=memoryview(mm)[frompos:]
        w.write(part);h.update(part);del part
    assert destination.stat().st_size == source.stat().st_size
    return h.hexdigest()

def test_json(path):
    found=False
    count=0
    with path.open("rb") as f:
        for var in ijson.items(f,"variableList.item",use_float=False):
            count+=1
            if var.get("id")==2047 and var.get("name")=="ちんこ誘惑ゲージ(MAX76)":
                assert var.get("initialValue")==0
                found=True
    if not found:raise RuntimeError("Global var 2047 no longer valid")
    return count

def encrypt(src,dst):
    padding=(-src.stat().st_size)%16
    total=src.stat().st_size
    previous=IV
    with src.open("rb") as inp, dst.open("wb") as out:
        out.write(b"enc"+bytes([padding]))
        while True:
            chunk=inp.read(16*65536)
            if not chunk:break
            if len(chunk)%16:
                chunk=chunk+b"\0"*((-len(chunk))%16)
            enc=bytearray(len(chunk))
            for pos in range(0,len(chunk),16):
                block=xor16(chunk[pos:pos+16],previous)
                cipher=weak_encrypt(block)
                enc[pos:pos+16]=cipher
                previous=cipher
            out.write(enc)
    if dst.stat().st_size != total+padding+4:
        raise RuntimeError("Encrypted size invalid")
    return padding

def verify_encrypted(encrypted,expected_sha,expected_size):
    h=hashlib.sha256()
    with encrypted.open("rb") as f:
        header=f.read(4)
        assert header[:3]==b"enc"
        prev=IV
        left=expected_size
        while True:
            chunk=f.read(16*65536)
            if not chunk:break
            out=bytearray(len(chunk))
            for i in range(0,len(chunk),16):
                cipher=bytes(chunk[i:i+16])
                out[i:i+16]=xor16(weak_decrypt(cipher),prev)
                prev=cipher
            n=min(left,len(out))
            h.update(memoryview(out)[:n])
            left-=n
    assert left==0 and h.hexdigest()==expected_sha, "CBC full roundtrip mismatch"
    return h.hexdigest()

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--input",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    a.add_argument("--dry-run",action="store_true")
    opts=a.parse_args()
    if opts.input.stat().st_size!=EXPECTED_SIZE or sha256(opts.input)!=EXPECTED_SHA:
        raise RuntimeError("Canonical project source hash/size mismatch")
    patches,counts,examples=collect(opts.input)
    print("ID2047_GLOBAL_SETTERS",counts["global_2047_setter_matches"],
          "NON_GLOBAL_SKIPPED",counts["non_global_id2047_ignored"])
    print("PATCH_BYTES",len(patches),"COUNTS",json.dumps(dict(counts)))
    opts.out.mkdir(parents=True,exist_ok=True)
    report={"source_sha256":EXPECTED_SHA,"source_bytes":EXPECTED_SIZE,
            "target":"ID2047 global temptation gauge","intended_effect":"freeze zero at every global setter",
            "other_ids_untouched":True,"no_engine_binary_changes":True,
            "counts":dict(counts),"samples":examples,"runtime_verified":False,
            "warning":"Unverified candidate; may alter cutscenes/temptation state transitions. Back up game project.json before replacing."}
    if not opts.dry_run:
        with tempfile.TemporaryDirectory(prefix="endurance-2047-") as td:
            plain=Path(td)/"project_decrypted_trial.json"
            raw=Path(td)/"project.json"
            newsha=apply(opts.input,plain,patches)
            report["patched_plain_sha256"]=newsha
            report["global_variable_count"]=test_json(plain)
            report["weakfish_padding"]=encrypt(plain,raw)
            report["encrypted_file_bytes"]=raw.stat().st_size
            report["roundtrip_sha256"]=verify_encrypted(raw,newsha,EXPECTED_SIZE)
            archive=opts.out/"endurance_2047_freeze0_TEST.zip"
            with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_STORED,allowZip64=True) as z:
                z.write(raw,"project.json")
            with zipfile.ZipFile(archive) as z:
                assert z.testzip() is None and z.getinfo("project.json").file_size == raw.stat().st_size
            report["candidate_archive"]=archive.name
            report["candidate_archive_bytes"]=archive.stat().st_size
            print("STAGE9_TEST_BUILD_PASS",archive,
                  "bytes",archive.stat().st_size,
                  "CBC_ROUNDTRIP_PASS","patch_count",len(patches))
    else:
        print("STAGE9_DRY_RUN_PASS (no modifications emitted)")
    (opts.out/"stage9-freeze0-manifest.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":main()
