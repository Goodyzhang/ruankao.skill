#!/usr/bin/env python3
"""Install the optional Antigravity soft-exam Harness into one workspace."""
import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HOOK_NAMES = (
    "soft-exam-tool-guard",
    "soft-exam-stop-guard",
    "soft-exam-pre-invocation",
)
PAYLOAD_FILES = (
    Path("rules") / "soft-exam-suspension.md",
    Path("scripts") / "harness_common.py",
    Path("scripts") / "harness_pre_invocation.py",
    Path("scripts") / "harness_stop_guard.py",
    Path("scripts") / "harness_tool_guard.py",
)


def load_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"无效 JSON：{path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"JSON 根节点必须是对象：{path}")
    return value


def install(workspace, dry_run=False, force=False):
    workspace = Path(workspace).expanduser().resolve()
    agent_root = workspace / ".agents"
    source_hooks = load_json(ROOT / "hooks.json")
    target_hooks = agent_root / "hooks.json"

    if target_hooks.exists():
        current_hooks = load_json(target_hooks)
    else:
        current_hooks = {}

    merged_hooks = dict(current_hooks)
    actions = []
    for name in HOOK_NAMES:
        desired = source_hooks[name]
        if name not in current_hooks:
            merged_hooks[name] = desired
            actions.append((target_hooks, "create-hook"))
        elif current_hooks[name] == desired:
            actions.append((target_hooks, "same-hook"))
        elif force:
            merged_hooks[name] = desired
            actions.append((target_hooks, "update-hook"))
        else:
            actions.append((target_hooks, "keep-hook"))

    for relative in PAYLOAD_FILES:
        source = ROOT / relative
        target = agent_root / relative
        if not source.is_file():
            raise ValueError(f"发布包缺少 Harness 文件：{relative}")
        if not target.exists():
            action = "create"
        elif target.read_bytes() == source.read_bytes():
            action = "same"
        elif force:
            action = "update"
        else:
            action = "keep"
        actions.append((target, action))

    changed_hooks = merged_hooks != current_hooks
    if not dry_run:
        for target, action in actions:
            if action in {"create", "update"}:
                source = ROOT / target.relative_to(agent_root)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
        if changed_hooks:
            target_hooks.parent.mkdir(parents=True, exist_ok=True)
            target_hooks.write_text(
                json.dumps(merged_hooks, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    counts = {}
    for _, action in actions:
        counts[action] = counts.get(action, 0) + 1
    mode = "预览" if dry_run else "完成"
    print(mode + ": " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    if any(action == "keep-hook" for _, action in actions):
        print("保留了同名 Harness Hook；使用 --force 才会替换这三个命名 Hook。")
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Antigravity 工作区根目录")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写入")
    parser.add_argument("--force", action="store_true", help="更新同名 Harness 文件和命名 Hook")
    args = parser.parse_args()
    try:
        install(args.workspace, args.dry_run, args.force)
    except (OSError, ValueError) as error:
        parser.exit(1, f"安装失败：{error}\n")


if __name__ == "__main__":
    main()
