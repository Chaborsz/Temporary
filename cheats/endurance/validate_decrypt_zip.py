#!/usr/bin/env python3
"""Small synthetic end-to-end test for encrypted AGTK -> decrypted ZIP -> extract -> JSON."""
import hashlib
import tempfile
from pathlib import Path

from decode_project_weakfish import IV, weak_encrypt, xor16
from decrypt_to_zip import decrypt_file, zip_and_validate
from unpack_project_archive import extract

def main():
    data=b'{"variables":[{"name":"Endurance","id":27,"kind":"arousal"}],"ok":true}'
    pad=(-len(data))%16
    padded=data+b"\x00"*pad
    prev=IV
    cipher=bytearray()
    for i in range(0,len(padded),16):
        block=weak_encrypt(xor16(padded[i:i+16],prev))
        cipher.extend(block)
        prev=block
    with tempfile.TemporaryDirectory(prefix="endurance-archive-test-") as td:
        root=Path(td)
        encrypted=root/"project.json"
        encrypted.write_bytes(b"enc"+bytes([pad])+cipher)
        plaintext=root/"temp.json"
        n,sha,pad_found=decrypt_file(encrypted,plaintext)
        assert n==len(data) and pad_found==pad
        assert sha==hashlib.sha256(data).hexdigest()
        assert plaintext.read_bytes()==data
        archive=root/"project_data.zip"
        zip_and_validate(plaintext,archive)
        extracted=extract(archive,root/"input")
        assert Path(extracted["path"]).read_bytes()==data
    print("ENDURANCE_DECRYPT_ZIP_UNPACK_TEST_PASS")

if __name__=="__main__":
    main()
