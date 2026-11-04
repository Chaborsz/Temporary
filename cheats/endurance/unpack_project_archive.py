#!/usr/bin/env python3
"""Select and unpack one project.json from a ZIP/7z input; never extract arbitrary members."""
import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

LIMIT = 750 * 1024 * 1024

def safe_path(name: str) -> bool:
    parts=PurePosixPath(name.replace("\\","/")).parts
    return bool(parts) and ".." not in parts and not name.startswith(("/","\\")) and ":" not in parts[0]

def choose(names):
    valid=[n for n in names if safe_path(n) and PurePosixPath(n.replace("\\","/")).name.lower() in ("project.json","project_decrypted.json")]
    if not valid:
        raise ValueError("ZIP/7z must contain project.json or project_decrypted.json")
    def rank(n):
        p=n.replace("\\","/").lower()
        basename=p.rsplit("/",1)[-1]
        return (0 if basename == "project_decrypted.json" else 1,
                0 if p.endswith("resources/data/project.json") else 1,
                len(p),p)
    return sorted(valid,key=rank)[0]

def extract(archive: Path, out_dir: Path):
    out_dir.mkdir(parents=True,exist_ok=True)
    kind=archive.suffix.lower()
    if kind==".zip":
        with zipfile.ZipFile(archive) as z:
            name=choose([i.filename for i in z.infolist() if not i.is_dir()])
            meta=z.getinfo(name)
            if meta.file_size>LIMIT: raise ValueError("Uncompressed size exceeds safety limit")
            dest=out_dir/PurePosixPath(name.replace("\\","/")).name
            with z.open(name) as src, dest.open("wb") as dst:
                shutil.copyfileobj(src,dst,1024*1024)
            if dest.stat().st_size!=meta.file_size:
                dest.unlink(missing_ok=True)
                raise ValueError("Incorrect decompressed size")
            return {"archive":archive.name,"member":name,"path":str(dest),"size":dest.stat().st_size}
    if kind==".7z":
        try: import py7zr
        except ImportError as e: raise RuntimeError("For 7z archives install py7zr") from e
        with tempfile.TemporaryDirectory(prefix="fobs7z-") as td:
            with py7zr.SevenZipFile(archive,"r") as z:
                name=choose(z.getnames())
                z.extract(path=td,targets=[name])
            internal=Path(td).joinpath(*PurePosixPath(name.replace("\\","/")).parts)
            if not internal.is_file() or internal.stat().st_size>LIMIT:
                raise ValueError("Extracted project file absent or too large")
            dest=out_dir/internal.name
            shutil.move(str(internal),str(dest))
            return {"archive":archive.name,"member":name,"path":str(dest),"size":dest.stat().st_size}
    raise ValueError("Supported extensions: .zip / .7z")

def test():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        with zipfile.ZipFile(root/"sample.zip","w") as z:
            z.writestr("Resources/data/project_decrypted.json",'{"endurance":42}')
        r=extract(root/"sample.zip",root/"out")
        assert Path(r["path"]).read_bytes()==b'{"endurance":42}'
    print("ARCHIVE_SELFTEST_PASS (ZIP single member)")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive",type=Path)
    ap.add_argument("--output-dir",type=Path)
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:test()
    if a.archive:
        if not a.output_dir:ap.error("--output-dir required")
        r=extract(a.archive,a.output_dir)
        print("ARCHIVE_EXTRACTED",r)
    elif not a.self_test:ap.error("Provide --archive or --self-test")

if __name__=="__main__":main()
