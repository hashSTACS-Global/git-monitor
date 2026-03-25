#!/usr/bin/env bash
# Git Monitor — Claude Code Skill 安装脚本
# 用法：curl -sL https://raw.githubusercontent.com/hashSTACS-Global/git-monitor/main/install.sh | bash
set -euo pipefail

SKILL_NAME="git-monitor"
SKILLS_BASE="$HOME/.claude/skills"
SKILL_DIR="$SKILLS_BASE/$SKILL_NAME"
REPO_URL="https://github.com/hashSTACS-Global/git-monitor.git"

# ── 颜色输出 ──
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
red()    { printf '\033[31m%s\033[0m\n' "$*"; }

# ── 自动安装依赖 ──

# 检测包管理器
detect_pkg_manager() {
    if [[ "$(uname)" == "Darwin" ]]; then
        if command -v brew &>/dev/null; then
            echo "brew"
        else
            echo "none_mac"
        fi
    elif command -v apt-get &>/dev/null; then
        echo "apt"
    elif command -v dnf &>/dev/null; then
        echo "dnf"
    elif command -v yum &>/dev/null; then
        echo "yum"
    elif command -v pacman &>/dev/null; then
        echo "pacman"
    else
        echo "none"
    fi
}

install_package() {
    local pkg="$1"
    local mgr
    mgr=$(detect_pkg_manager)

    yellow "正在尝试自动安装 $pkg..."
    case "$mgr" in
        brew)    brew install "$pkg" ;;
        apt)     sudo apt-get update -qq && sudo apt-get install -y "$pkg" ;;
        dnf)     sudo dnf install -y "$pkg" ;;
        yum)     sudo yum install -y "$pkg" ;;
        pacman)  sudo pacman -S --noconfirm "$pkg" ;;
        none_mac)
            red "未找到 Homebrew，请先安装 Homebrew："
            red '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            red "然后重新运行本安装脚本。"
            exit 1
            ;;
        *)
            red "无法自动安装 $pkg：未识别的包管理器"
            red "请手动安装后重新运行本脚本。"
            exit 1
            ;;
    esac
}

# 检查 git
if ! command -v git &>/dev/null; then
    install_package git
    if ! command -v git &>/dev/null; then
        red "错误：git 安装失败，请手动安装"
        exit 1
    fi
    green "git 安装成功"
fi

# 检查 python3
if ! command -v python3 &>/dev/null; then
    install_package python3
    if ! command -v python3 &>/dev/null; then
        red "错误：python3 安装失败，请手动安装"
        exit 1
    fi
    green "python3 安装成功"
fi

# 检查 python3 版本
python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
python_major=$(echo "$python_version" | cut -d. -f1)
python_minor=$(echo "$python_version" | cut -d. -f2)
if [ "$python_major" -lt 3 ] || { [ "$python_major" -eq 3 ] && [ "$python_minor" -lt 10 ]; }; then
    yellow "当前 Python 版本为 $python_version，需要 3.10+"
    if [[ "$(uname)" == "Darwin" ]] && command -v brew &>/dev/null; then
        yellow "正在通过 Homebrew 升级 Python..."
        brew install python@3.12 || brew upgrade python@3.12
        python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        green "Python 已升级至 $python_version"
    else
        red "错误：需要 Python 3.10+，请手动升级"
        exit 1
    fi
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
