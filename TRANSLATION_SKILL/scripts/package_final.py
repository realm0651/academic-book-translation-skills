#!/usr/bin/env python3
"""Create the final translation package with stable, filename-safe archive names."""
from __future__ import annotations
import argparse, re, shutil, zipfile
from pathlib import Path

UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')

def safe_stem(value: str) -> str:
    value = value.replace('%20', ' ')
    value = value.replace('：', '_').replace(':', '_')
    value = re.sub(r'\s+', '_', value.strip())
    value = UNSAFE.sub('_', value)
    value = re.sub(r'_+', '_', value).strip('._ ')
    return value or 'book'

def require(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(p)
    return p

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--book-stem', required=True)
    ap.add_argument('--master', required=True)
    ap.add_argument('--epub', required=True)
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--glossary', default='glossary.md')
    ap.add_argument('--metadata', default='zlibrary_metadata.md')
    ap.add_argument('--assets', default='')
    ap.add_argument('--output', default='')
    a=ap.parse_args()
    stem=safe_stem(a.book_stem)
    master, epub, pdf, glossary, metadata = map(require, [a.master,a.epub,a.pdf,a.glossary,a.metadata])
    out=Path(a.output) if a.output else Path(f'{stem}_final.zip')
    out=out.expanduser().resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.write(master, f'{stem}_master.md')
        z.write(epub, safe_stem(epub.stem)+epub.suffix.lower())
        z.write(pdf, safe_stem(pdf.stem)+pdf.suffix.lower())
        z.write(glossary, 'glossary.md')
        z.write(metadata, 'zlibrary_metadata.md')
        if a.assets:
            assets=Path(a.assets).expanduser().resolve()
            if assets.exists():
                for f in sorted(x for x in assets.rglob('*') if x.is_file()):
                    z.write(f, Path('assets')/f.relative_to(assets))
    print(out)
    return 0
if __name__=='__main__':
    raise SystemExit(main())
