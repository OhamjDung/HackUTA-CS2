"""Fetch the public handoff archive, verify its bytes and reject unsafe ZIP paths."""
import argparse
import hashlib
import subprocess
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

URL = 'https://github.com/OhamjDung/HackUTA-CS2/releases/download/clone-training-data-v1/cs2-rounds-transfer.zip'
SHA256 = '0e46914cbca514efbb5727b64f9e753116da4afaa98f764be66d15d97cb8ad25'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=Path('data/habit-audit'))
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    archive=args.out/'cs2-rounds-transfer.zip'
    if not archive.exists():
        part=archive.with_suffix('.zip.part')
        subprocess.run(['curl','--location','--fail','--retry','2','--output',str(part),URL],check=True)
        part.replace(archive)
    actual=hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != SHA256:
        raise ValueError(f'Archive checksum mismatch: {actual}')
    destination=(args.out/'parsed').resolve()
    with ZipFile(archive) as z:
        infos=z.infolist()
        if sum(i.file_size for i in infos)>1024**3:
            raise ValueError('Unexpected expanded archive size')
        for i in infos:
            p=PurePosixPath(i.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in i.filename or (i.external_attr>>16)&0o170000==0o120000:
                raise ValueError(f'Unsafe archive entry: {i.filename}')
            if i.filename != 'games.json' and not (len(p.parts)==2 and p.parts[0]=='round_json' and p.name.endswith('.json.gz')):
                raise ValueError(f'Unexpected archive entry: {i.filename}')
            print(i.filename,i.file_size)
        z.extractall(destination)
    print(f'SHA256 verified {actual}; parsed data at {destination}')
    print('Ignore archive games.json; use current clone-model/games.json for verified selection.')


if __name__=='__main__':main()
