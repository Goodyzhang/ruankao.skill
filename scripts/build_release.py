#!/usr/bin/env python3
"""Build separate tool and study-material ZIPs from a clean Git checkout."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MATERIALS = Path('materials/系统架构设计师')
CATEGORIES = {
    'textbook': ('教材',),
    'notes': ('笔记',),
    'questions-cases': ('题库', '案例分析'),
    'essays': ('论文',),
}


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def build(output, version):
    output = Path(output).resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError('Output must be outside the repository.')
    if not version or any(c not in '0123456789.' for c in version):
        raise ValueError('Version must contain only digits and dots.')
    git('diff', '--quiet', 'HEAD', '--')
    tracked = [Path(p.decode()) for p in git('ls-files', '-z').split(b'\0') if p]
    files = [p for p in tracked if MATERIALS in p.parents]
    if not files:
        raise ValueError('No tracked study materials; use the full Git checkout.')
    tool_output, material_output = output / 'toolkit', output / 'materials'
    tool_output.mkdir(parents=True, exist_ok=True)
    material_output.mkdir(parents=True, exist_ok=True)
    toolkit = tool_output / f'ruankao-toolkit-v{version}.zip'
    git('archive', '--format=zip', f'--prefix=ruankao-toolkit-v{version}/',
        f'--output={toolkit}', 'HEAD')
    with zipfile.ZipFile(toolkit) as archive:
        names = archive.namelist()
        if any('/materials/' in n or '/artifacts/' in n for n in names):
            raise ValueError('Tool package includes optional study materials or visual books.')
        if archive.testzip():
            raise ValueError('Tool ZIP integrity check failed.')
    built = [toolkit]
    all_folders = tuple(folder for folders in CATEGORIES.values() for folder in folders)
    for name, folders in [('materials', all_folders), *CATEGORIES.items()]:
        selected = [p for p in files if len(p.relative_to(MATERIALS).parts) == 1
                    or p.relative_to(MATERIALS).parts[0] in folders]
        destination = material_output / f'ruankao-architect-{name}-v{version}.zip'
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for p in selected:
                source = ROOT / p
                if source.is_symlink():
                    raise ValueError(f'Symlink is not allowed: {p}')
                archive.write(source, Path('系统架构设计师') / p.relative_to(MATERIALS))
            archive.write(ROOT / 'NOTICE.md', 'NOTICE.md')
        with zipfile.ZipFile(destination) as archive:
            if archive.testzip():
                raise ValueError(f'ZIP integrity check failed: {destination.name}')
        built.append(destination)
    git('diff', '--quiet', 'HEAD', '--')
    for folder in (tool_output, material_output):
        sums = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n'
                       for p in built if p.parent == folder)
        (folder / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8')
    for p in built:
        print(f'{p.name}: {p.stat().st_size} bytes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', default='1.0.0')
    args = parser.parse_args()
    build(args.output, args.version)


if __name__ == '__main__':
    main()
