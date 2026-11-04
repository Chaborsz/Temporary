#!/usr/bin/env python3
"""Streaming old-AGTK weakfish decrypt + bounded Endurance search.

Game: Forest of the Blue Skin Build 29, AGTK / Pixel Game Maker MV.
Reimplements the MIT-licensed weakfish algorithm of blluv/pgmm_decrypt:
https://github.com/blluv/pgmm_decrypt
Copyright (c) 2022 blluv; MIT license.
This file is a read-only investigation tool, never a game patch.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import os
import sys
from pathlib import Path

IV = bytes.fromhex("A047E93D230A4C62A744B1A4EE857FBA")
EXPECTED_PLAIN_SIZE = 294287854
TERMS = (
    "endurance", "excitation", "excitement", "arousal", "stamina",
    "lust", "pleasure", "orgasm", "tension", "fatigue",
    "興奮", "興奋", "快感", "絶頂", "欲情", "体力", "精力",
)
# Old PGMM keys <=8 bytes select weakfish. The known key is b"232301 "
# including the trailing space. Unlike Twofish, weakfish needs no key schedule.
KNOWN_LEGACY_KEY = b"232301 "

def rotate_left(data: bytes, n: int) -> bytes:
    return data[n:] + data[:n]

def rotate_right(data: bytes, n: int) -> bytes:
    return data[-n:] + data[:-n] if n else data

def weak_decrypt(block: bytes) -> bytes:
    if len(block) != 16:
        raise ValueError("Weakfish block is not 16 bytes")
    trans = (rotate_right(block[:4], 1) + rotate_left(block[4:8], 1)
             + rotate_right(block[8:12], 1) + rotate_left(block[12:], 1))
    return rotate_right(trans, 8)

def weak_encrypt(block: bytes) -> bytes:
    if len(block) != 16:
        raise ValueError("Weakfish block is not 16 bytes")
    trans = (rotate_left(block[:4], 1) + rotate_right(block[4:8], 1)
             + rotate_left(block[8:12], 1) + rotate_right(block[12:], 1))
    return rotate_left(trans, 8)

def xor16(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x,y in zip(a,b))

def decrypt_file(src: Path, dst: Path) -> dict:
    size = src.stat().st_size
    if size < 20 or (size-4) % 16:
        raise ValueError("Invalid encrypted size/header (expected 4+16*N)")
    hasher = hashlib.sha256()
    produced = 0
    with src.open("rb") as reader, dst.open("wb") as writer:
        header = reader.read(4)
        if header[:3] != b"enc":
            raise ValueError("Not an AGTK 'enc' file")
        padding = header[3]
        if not 0 <= padding <= 15:
            raise ValueError("Unexpected trailing padding byte")
        plaintext_len = size - 4 - padding
        previous = IV
        blocks = 0
        while True:
            buf = reader.read(16 * 65536)
            if not buf:
                break
            if len(buf) % 16:
                raise ValueError("Input ends in incomplete cipher block")
            out = bytearray(len(buf))
            for offset in range(0, len(buf),16):
                encrypted = buf[offset:offset+16]
                plain = xor16(weak_decrypt(encrypted),previous)
                out[offset:offset+16] = plain
                previous = encrypted
                blocks += 1
            valid_len = max(0,min(len(out),plaintext_len-produced))
            writer.write(memoryview(out)[:valid_len])
            hasher.update(memoryview(out)[:valid_len])
            produced += valid_len
        if produced != plaintext_len:
            raise ValueError("Incomplete decryption")
    with dst.open("rb") as reader:
        first = reader.read(128).lstrip(b"\xef\xbb\xbf \t\r\n")
    if not first.startswith((b"{",b"[")):
        raise ValueError("Decryption did not produce JSON-like content")
    return {"status":"DECRYPTED","input_bytes":size,"output_bytes":produced,
            "sha256":hasher.hexdigest(),"padding_bytes":padding,"blocks":blocks,
            "matches_previous_decoded_size":produced == EXPECTED_PLAIN_SIZE}

def scan_json(path: Path, max_hits: int = 120) -> dict:
    import ijson
    found=[]
    counts=collections.Counter()
    last=collections.deque(maxlen=8)
    events=0
    with path.open("rb") as f:
        for prefix,event,value in ijson.parse(f, use_float=False):
            events += 1
            if event not in ("string","map_key","number","boolean"):
                continue
            text = str(value)
            if event in ("map_key","string"):
                lower=text.casefold()
                words=[w for w in TERMS if w in lower]
                if words:
                    for word in words:
                        counts[word] += 1
                    if len(found) < max_hits:
                        found.append({
                            "json_path":prefix[:240],"event":event,
                            "matched_terms":words,
                            "text":text[:280],
                            "preceding_scalars":list(last)[-6:]
                        })
            last.append({"path":prefix[-180:],
                         "event":event,"value":text[:100]})
    return {"status":"SCANNED","parser":"ijson streaming",
            "json_events":events,"matched_term_counts":dict(counts),
            "hits_recorded":len(found),"hits_capped":len(found)>=max_hits,"hits":found}

def selftest():
    base=b'{"names":["Endurance"],"id":27}'
    assert len(base)==31
    pad=(-len(base)) % 16
    plain=base+b" " * pad
    prev=IV
    cipher=bytearray()
    for i in range(0,len(plain),16):
        blk=weak_encrypt(xor16(plain[i:i+16],prev))
        cipher.extend(blk)
        prev=blk
    prev=IV
    out=bytearray()
    for i in range(0,len(cipher),16):
        enc=bytes(cipher[i:i+16])
        out.extend(xor16(weak_decrypt(enc),prev))
        prev=enc
    assert bytes(out[:len(base)])==base
    # End-to-end test: header, CBC streaming, final padding, JSON parser and Endurance hit.
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix="pgmm-weakfish-test-") as tmp:
        enc = Path(tmp)/"project.json"
        dec = Path(tmp)/"decrypted.json"
        enc.write_bytes(b"enc"+bytes([pad])+bytes(cipher))
        summary = decrypt_file(enc, dec)
        assert summary["output_bytes"] == len(base)
        assert dec.read_bytes() == base
        report = scan_json(dec,max_hits=5)
        assert any("endurance" in h["matched_terms"] for h in report["hits"])
    return {"status":"PASS","test":"weakfish CBC streaming decode + JSON scanner"}

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--input",type=Path)
    arg.add_argument("--output",type=Path,required=True,
                     help="Directory for only small reports")
    arg.add_argument("--self-test",action="store_true")
    arg.add_argument("--retain-decoded",action="store_true",
                     help="Do not remove temporary decoded JSON (avoid on public CI)")
    a=arg.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    report={"title":"FoBS Build 29 Endurance project.json","target":"Endurance/aguante/excitacion, not HP",
            "method":"old-AGTK weakfish-CBC; key b'232301 ' (7 bytes)",
            "source":str(a.input) if a.input else "(missing)"}
    if a.self_test:
        report["selftest"]=selftest()
    if not a.input or not a.input.is_file():
        report.update({"status":"SOURCE_MISSING",
          "next":"Supply encrypted Resources/data/project.json or already-decoded project_decrypted.json."})
    else:
        encoded=False
        with a.input.open("rb") as f:
            prefix=f.read(4)
        decoded_path = a.input
        if prefix.startswith(b"enc"):
            encoded=True
            decoded_path=a.output/"project_decoded_tmp.json"
            report["decryption"]=decrypt_file(a.input,decoded_path)
        try:
            report["scan"]=scan_json(decoded_path)
            report["status"]="SCANNED"
        except Exception as e:
            report["status"]="SCAN_FAILED"
            report["scan_error"]=type(e).__name__+": "+str(e)[:250]
            raise
        finally:
            if encoded and not a.retain_decoded and decoded_path.exists():
                decoded_path.unlink()
        report["next"]="Inspect named-variable and object/scene IDs in bounded hits and link to HUD Endurance meter; no patches."
    output_file=a.output/"stage4-weakfish-endurance.json"
    output_file.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STAGE4",report["status"],
          "source=",report["source"],
          "decoded_bytes=",report.get("decryption",{}).get("output_bytes",0),
          "hits=",len(report.get("scan",{}).get("hits",[])))
    print("REPORT",output_file)
    if report["status"]=="SOURCE_MISSING":
        print("BLOCKER: encrypted project.json is not available; player.exe does not include it.")
        return

if __name__ == "__main__":
    main()
