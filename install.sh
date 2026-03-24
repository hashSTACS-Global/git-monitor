#!/usr/bin/env bash
# Git Monitor — Claude Code Skill 安装脚本
# 用法：curl -sL https://raw.githubusercontent.com/xxx/git-monitor/main/install.sh | bash
set -euo pipefail

SKILL_NAME="git-monitor"
SKILLS_BASE="$HOME/.claude/skills"
SKILL_DIR="$SKILLS_BASE/$SKILL_NAME"
REPO_URL="https://github.com/hashSTACS-Global/git-monitor.git"

# ── 颜色输出 ──
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
red()    { printf '\033[31m%s\033[0m\n' "$*"; }

# ── 前置检查 ──
if ! command -v git &>/dev/null; then
    red "错误：未找到 git，请先安装 git"
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    red "错误：未找到 python3，请先安装 Python 3.10+"
    exit 1
fi

python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
python_major=$(echo "$python_version" | cut -d. -f1)
python_minor=$(echo "$python_version" | cut -d. -f2)
if [ "$python_major" -lt 3 ] || { [ "$python_major" -eq 3 ] && [ "$python_minor" -lt 10 ]; }; then
    red "错误：需要 Python 3.10+，当前版本为 $python_version"
    exit 1
fi

# ── 确保 skills 目录存在 ──
mkdir -p "$SKILLS_BASE"

# ── 安装或更新 ──
if [ -d "$SKILL_DIR" ]; then
    if [ -d "$SKILL_DIR/.git" ]; then
        yellow "检测到已安装，正在更新..."
        cd "$SKILL_DIR"
        git pull --ff-only origin main 2>/dev/null || git pull origin main
        green "更新完成！"
    else
        yellow "检测到目录 $SKILL_DIR 已存在但不是 git 仓库"
        yellow "备份到 ${SKILL_DIR}.bak 并重新安装..."
        mv "$SKILL_DIR" "${SKILL_DIR}.bak.$(date +%s)"
        git clone "$REPO_URL" "$SKILL_DIR"
        green "重新安装完成！"
    fi
else
    echo "正在安装 $SKILL_NAME skill..."
    git clone "$REPO_URL" "$SKILL_DIR"
    green "安装完成！"
fi

# ── 配置 Claude Code 权限 ──
CLAUDE_SETTINGS="$HOME/.claude/settings.json"

# 需要的权限列表
PERMISSIONS=(
    "Bash(python3 *)"
    "Bash(python *)"
)

if [ -f "$CLAUDE_SETTINGS" ]; then
    python3 -c "
import json, sys

with open('$CLAUDE_SETTINGS', 'r') as f:
    settings = json.load(f)

allow = settings.setdefault('permissions', {}).setdefault('allow', [])
added = []
for perm in sys.argv[1:]:
    if perm not in allow:
        allow.append(perm)
        added.append(perm)

if added:
    with open('$CLAUDE_SETTINGS', 'w') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write('\n')
    for p in added:
        print(f'  + {p}')
else:
    print('  (权限已存在，无需修改)')
" "${PERMISSIONS[@]}"
else
    # settings.json 不存在，创建一个
    python3 -c "
import json, sys
settings = {'permissions': {'allow': list(sys.argv[1:])}}
with open('$CLAUDE_SETTINGS', 'w') as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write('\n')
for p in sys.argv[1:]:
    print(f'  + {p}')
" "${PERMISSIONS[@]}"
fi
green "Claude Code 权限已配置"

# ── 验证安装 ──
if [ ! -f "$SKILL_DIR/SKILL.md" ]; then
    red "错误：安装后未找到 SKILL.md，安装可能不完整"
    exit 1
fi

# ── 完成 ──
echo ""
green "✅ git-monitor skill 安装成功！"
echo ""
echo "安装位置：$SKILL_DIR"
echo "Python 版本：$python_version"
echo ""
echo "使用方法（在 Claude Code 中输入）："
echo "  /git-monitor https://github.com/owner/repo --branch main --since 2025-01-01"
echo ""
