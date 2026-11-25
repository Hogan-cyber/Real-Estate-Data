"""Copy the exact local preview downloads after the website build."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[3]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    args=parser.parse_args()
    snapshot=json.loads((ROOT/'src/data.json').read_text())
    if hashlib.sha256((args.input/'observations.parquet').read_bytes()).hexdigest()!=snapshot['dataset']['sha256']:
        raise ValueError('Preview downloads do not match the built snapshot')
    destination=ROOT/'dist/downloads';destination.mkdir(parents=True,exist_ok=True)
    for filename in snapshot['dataset'].get('downloadFiles',[]):
        if Path(filename).name!=filename:raise ValueError('Invalid download filename')
        shutil.copyfile(args.input/filename,destination/filename)
    print(f'Copied {len(snapshot["dataset"].get("downloadFiles",[]))} matching preview downloads')

if __name__=='__main__':main()
