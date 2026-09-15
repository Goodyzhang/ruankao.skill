#!/usr/bin/env python3
"""Install the five Skills and seed notes into a Vault without replacing notes."""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = {'antigravity': '.agents', 'codex': '.agents', 'claude': '.claude', 'trae': '.trae'}


def install(vault, platforms, dry_run=False, upgrade_skills=False):
    vault = Path(vault).expanduser().resolve()
    if vault == ROOT or ROOT in vault.parents or vault in ROOT.parents:
        raise ValueError('目标 Vault 与发布仓库不能相互包含；请选择独立目录。')
    entries = []
    for src in sorted((ROOT / 'vault').rglob('*')):
        if src.is_file():
            entries.append((src, vault / src.relative_to(ROOT / 'vault'), False))
    for folder in sorted({PLATFORMS[p] for p in platforms}):
        for src in sorted((ROOT / 'skills').rglob('*')):
            if src.is_file():
                entries.append((src, vault / folder / 'skills' / src.relative_to(ROOT / 'skills'), True))
    plan = []
    for src, dst, skill in entries:
        if src.is_symlink():
            raise ValueError(f'发布源不能包含符号链接：{src.relative_to(ROOT)}')
        cursor = dst
        while cursor != vault:
            if cursor.is_symlink():
                raise ValueError(f'目标路径包含符号链接，请先检查：{dst.relative_to(vault)}')
            if cursor != dst and cursor.exists() and not cursor.is_dir():
                raise ValueError(f'目标父路径不是目录：{cursor}')
            cursor = cursor.parent
        if dst.exists() and not dst.is_file():
            raise ValueError(f'目标不是普通文件：{dst}')
        if dst.exists():
            if dst.read_bytes() == src.read_bytes():
                action = 'same'
            elif skill and upgrade_skills:
                action = 'update-skill'
            else:
                action = 'keep-existing'
        else:
            action = 'create'
        plan.append((src, dst, action))
    counts = {}
    for src, dst, action in plan:
        counts[action] = counts.get(action, 0) + 1
        if action in ('create', 'update-skill') and not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if action == 'create':
                # Exclusive creation also protects files created after the preflight.
                with dst.open('xb') as target:
                    target.write(src.read_bytes())
            else:
                shutil.copyfile(src, dst)
        if action == 'keep-existing':
            print(f'保留已有文件：{dst.relative_to(vault)}')
    print(('预览' if dry_run else '完成') + ': ' + ', '.join(f'{k}={v}' for k, v in sorted(counts.items())))
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', required=True, help='目标 Obsidian Vault / Agent 工作区')
    parser.add_argument('--platform', nargs='+', choices=PLATFORMS, default=['antigravity'])
    parser.add_argument('--dry-run', action='store_true', help='仅预览，不创建目录或文件')
    parser.add_argument('--upgrade-skills', action='store_true', help='覆盖所选平台的同名 Skill 文件；知识资料始终不覆盖')
    args = parser.parse_args()
    try:
        install(args.vault, args.platform, args.dry_run, args.upgrade_skills)
    except (ValueError, OSError) as error:
        parser.exit(1, f'初始化失败：{error}\n')


if __name__ == '__main__':
    main()
