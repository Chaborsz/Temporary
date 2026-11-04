#!/usr/bin/env python3
# coding: utf-8
"""Forest of the Blue Skin Build 29 — AGTK Weakfish to ZIP (Python 3 stdlib).
Reads Resources/data/project.json encrypted, writes ZIP with project_decrypted.json.
No installation or third-party packages required.
Weakfish algorithm adapted from blluv/pgmm_decrypt (MIT; Copyright 2022 blluv).
https://github.com/blluv/pgmm_decrypt
"""
import argparse
import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path

IV = bytes.fromhex("A047E93D230A4C62A744B1A4EE857FBA")
EXPECTED_DECODED_SIZE = 294287854

def weakfish_decrypt(block):
    if len(block) != 16:
        raise ValueError("Bloque Weakfish incompleto")
    x = block[3:4] + block[:3] + block[5:8] + block[4:5] + block[11:12] + block[8:11] + block[13:16] + block[12:13]
    return x[8:] + x[:8]

def decrypt_file(src, dst):
    size = src.stat().st_size
    if size < 20 or (size - 4) % 16:
        raise ValueError("Longitud del archivo cifrado invalida")
    sha = hashlib.sha256()
    with src.open("rb") as source, dst.open("wb") as target:
        hdr = source.read(4)
        if hdr[:3] != b"enc":
            raise ValueError("El archivo no empieza con la cabecera AGTK 'enc'")
        padding = hdr[3]
        if padding > 15:
            raise ValueError("Padding AGTK invalido")
        decoded_size = size - 4 - padding
        prev = IV
        count = 0
        while True:
            raw = source.read(16 * 32768)
            if not raw:
                break
            if len(raw) % 16:
                raise ValueError("Trama de cifrado incompleta")
            out = bytearray(len(raw))
            for pos in range(0,len(raw),16):
                cipher = raw[pos:pos+16]
                unmasked = weakfish_decrypt(cipher)
                out[pos:pos+16] = bytes(x^y for x,y in zip(unmasked,prev))
                prev = cipher
            valid = min(len(out), decoded_size-count)
            if valid > 0:
                chunk=memoryview(out)[:valid]
                target.write(chunk)
                sha.update(chunk)
                count += valid
        if count != decoded_size:
            raise ValueError("Decodificacion incompleta")
    with dst.open("rb") as f:
        prefix = f.read(80).lstrip(b"\xef\xbb\xbf \t\r\n")
    if not prefix.startswith((b"{",b"[")):
        raise ValueError("El resultado no parece un JSON (verificar version)")
    return count, sha.hexdigest(), padding

def zip_and_validate(src, dst):
    with zipfile.ZipFile(dst,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
        archive.write(src,arcname="project_decrypted.json")
    with zipfile.ZipFile(dst) as check:
        members=check.infolist()
        if len(members)!=1 or members[0].filename!="project_decrypted.json":
            raise RuntimeError("Archivo ZIP creado con contenido inesperado")
        if check.testzip() is not None:
            raise RuntimeError("Fallo de CRC del ZIP")

def main():
    a=argparse.ArgumentParser(description="Descifrar project.json AGTK Build 29 y comprimir sin guardar copia suelta")
    a.add_argument("project_json",type=Path,help="Ruta al project.json CIFRADO")
    a.add_argument("--output",type=Path,default=Path("project_data.zip"))
    opts=a.parse_args()
    source=opts.project_json.resolve()
    destination=opts.output.resolve()
    if not source.is_file():
        a.error("No se encontro el archivo original: "+str(source))
    if destination==source:
        a.error("La salida ZIP no puede sustituir al original")
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fobs-weakfish-") as tmp:
        plain=Path(tmp)/"project_decrypted.json"
        n, sha, padding=decrypt_file(source,plain)
        print("Descifrado correcto | tamano:", n, "| SHA256:",sha,"| padding:",padding,flush=True)
        if n != EXPECTED_DECODED_SIZE:
            print("Aviso: tamano distinto al checkpoint Build29; no se modifica el original.",flush=True)
        try:
            zip_and_validate(plain,destination)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    print("ZIP verificado:",destination,"| bytes:",destination.stat().st_size,flush=True)
    print("Contiene solo project_decrypted.json; sin copia descomprimida.",flush=True)

if __name__=="__main__":
    main()
