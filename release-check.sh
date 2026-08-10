#!/bin/sh
# 发版前自检：把踩过的坑都变成会失败的检查。
#
#   ./release-check.sh
#
# 插件源码与 marketplace 同仓（source 是相对路径，不钉 sha），所以检查全部在本地
# 完成，不需要网络。以前那三项与 sha 有关的检查——40 位完整 sha、sha 是上游分支的
# 祖先、path 在该 sha 上存在——随着 sha 一起作废了。
#
#   1. marketplace.json 能解析，且 claude plugin validate 通过
#   2. marketplace 条目的 version 与 plugin.json 的 version 一致 —— 装的时候以
#      plugin.json 为准，两处不一致时 marketplace 标了新版也没用
#   3. source 指向的目录存在，且带 .claude-plugin/plugin.json
#   4. bin/ 下的程序有可执行位 —— 丢了 x 位，命令进了 PATH 也跑不起来
#   5. lib/ 与 bin/ 的 Python 能编译
#
# 只用 sh + python3（标准库）。

set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MANIFEST="$DIR/.claude-plugin/marketplace.json"

[ -f "$MANIFEST" ] || { echo "找不到 $MANIFEST" >&2; exit 1; }

if command -v claude >/dev/null 2>&1; then
    echo "▸ claude plugin validate"
    claude plugin validate "$DIR" >/dev/null || { echo "  ✘ validate 未通过，跑 claude plugin validate . 看详情" >&2; exit 1; }
    echo "  ✔ 通过"
else
    echo "▸ claude 不在 PATH，跳过 validate（其余检查照常）"
fi

python3 - "$MANIFEST" "$DIR" <<'PY'
import json
import os
import py_compile
import stat
import sys
import tempfile

manifest_path, root = sys.argv[1], sys.argv[2]
manifest = json.load(open(manifest_path, encoding='utf-8'))
fails = []

for entry in manifest.get('plugins', []):
    name = entry.get('name', '?')
    version = entry.get('version')
    src = entry.get('source')
    print(f"\n▸ {name} {version}")

    if not isinstance(src, str):
        fails.append(f'{name}: source 不是相对路径字符串（当前 {src!r}）。'
                     '同仓插件应写成 "./plugins/<名字>"')
        continue

    plugin_dir = os.path.normpath(os.path.join(root, src))
    if not os.path.isdir(plugin_dir):
        fails.append(f'{name}: source 指向的目录不存在：{src}')
        continue
    print(f'  ✔ 目录存在 {src}')

    # 2 + 3：plugin.json 必须在，且版本要对得上
    plugin_json = os.path.join(plugin_dir, '.claude-plugin', 'plugin.json')
    if not os.path.isfile(plugin_json):
        fails.append(f'{name}: 缺 .claude-plugin/plugin.json')
        continue
    declared = json.load(open(plugin_json, encoding='utf-8')).get('version')
    if declared != version:
        fails.append(f'{name}: marketplace 写 {version}，plugin.json 写 {declared}。'
                     '装的时候以 plugin.json 为准，两者必须一致')
    else:
        print(f'  ✔ 版本一致 {declared}')

    # 4：可执行位
    bin_dir = os.path.join(plugin_dir, 'bin')
    if os.path.isdir(bin_dir):
        for f in sorted(os.listdir(bin_dir)):
            path = os.path.join(bin_dir, f)
            if not os.path.isfile(path):
                continue
            if not os.stat(path).st_mode & stat.S_IXUSR:
                fails.append(f'{name}: bin/{f} 没有可执行位，chmod +x')
            else:
                print(f'  ✔ bin/{f} 可执行')

    # 5：Python 能编译
    bad = []
    for sub in ('lib', 'bin'):
        d = os.path.join(plugin_dir, sub)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            path = os.path.join(d, f)
            if not os.path.isfile(path):
                continue
            if sub == 'lib' and not f.endswith('.py'):
                continue
            with open(path, 'rb') as fh:
                if sub == 'bin' and b'python' not in fh.readline():
                    continue
            try:
                with tempfile.NamedTemporaryFile(suffix='.pyc', delete=True) as out:
                    py_compile.compile(path, cfile=out.name, doraise=True)
            except py_compile.PyCompileError as e:
                bad.append(f'{sub}/{f}: {e.msg.strip().splitlines()[-1]}')
    if bad:
        fails.extend(f'{name}: {b}' for b in bad)
    else:
        print('  ✔ Python 全部可编译')

print()
if fails:
    for f in fails:
        print(f'✘ {f}')
    sys.exit(1)
print('全部通过，可以推。')
PY
