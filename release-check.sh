#!/bin/sh
# 发版前自检：把今天踩过的坑都变成会失败的检查。
#
#   ./release-check.sh
#
# 五项检查，全过才可以推 marketplace：
#
#   1. marketplace.json 能解析，且 claude plugin validate 通过
#   2. source.sha 是完整 40 位（短 sha 会被 validate 拒绝：plugins.N.source: Invalid input）
#   3. **该 sha 是上游分支的祖先** —— 不是「GitHub 能查到这个 sha」。fork 与上游共享
#      对象存储，只推到 fork 的提交用上游 API 按 sha 也查得到，据此判断会把没合并的
#      提交当成已发布，用户装不上
#   4. 该 sha 上的 plugin.json version 与 marketplace 条目的 version 一致 —— plugin.json
#      的 version 决定用户能否收到更新，两处不一致时 marketplace 标了新版也没用
#   5. source.path 在该 sha 上确实存在
#
# 只用 sh + python3（标准库），不需要克隆 mint，也不需要网络以外的任何依赖。

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

python3 - "$MANIFEST" <<'PY'
import json, re, sys, urllib.error, urllib.request

manifest = json.load(open(sys.argv[1], encoding='utf-8'))
fails = []


def api(path):
    req = urllib.request.Request('https://api.github.com/' + path,
                                 headers={'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as f:
            return json.load(f), None
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:  # 网络不通等
        return None, str(e)


for entry in manifest.get('plugins', []):
    name = entry.get('name', '?')
    version = entry.get('version')
    src = entry.get('source')
    print(f"\n▸ {name} {version}")

    if not isinstance(src, dict) or src.get('source') != 'git-subdir':
        print('  · 非 git-subdir 源，跳过 sha 相关检查')
        continue

    sha = src.get('sha', '')
    ref = src.get('ref', 'HEAD')
    path = src.get('path', '')
    repo = re.sub(r'^https://github\.com/|\.git$', '', src.get('url', ''))

    # 2. sha 长度
    if re.fullmatch(r'[0-9a-f]{40}', sha or ''):
        print(f'  ✔ sha 40 位  {sha[:12]}…')
    else:
        fails.append(f'{name}: sha 不是完整 40 位十六进制（现在是 {sha!r}）')
        print('  ✘ sha 不是完整 40 位')
        continue

    # 3. sha 是不是 ref 的祖先（而不是「能查到」）
    cmp_, err = api(f'repos/{repo}/compare/{ref}...{sha}')
    if cmp_ is None:
        fails.append(f'{name}: 无法比较 {ref}...{sha[:12]}（{err}）')
        print(f'  ✘ 比较失败：{err}')
    else:
        status = cmp_.get('status')
        if status in ('identical', 'behind'):
            print(f'  ✔ sha 已在 {repo}@{ref} 上（{status}）')
        else:
            fails.append(f'{name}: sha 不在 {repo}@{ref} 上（status={status}，'
                         f'落后 {cmp_.get("behind_by")} / 领先 {cmp_.get("ahead_by")}）'
                         '——多半是只推到了 fork，还没合并进上游')
            print(f'  ✘ sha 不在 {ref} 上（status={status}）')

    # 4/5. 该 sha 上的 plugin.json
    r, err = api(f'repos/{repo}/contents/{path}/.claude-plugin/plugin.json?ref={sha}')
    if r is None:
        fails.append(f'{name}: 在 {sha[:12]} 上取不到 {path}/.claude-plugin/plugin.json（{err}）')
        print(f'  ✘ 该 sha 上没有 {path}/.claude-plugin/plugin.json（{err}）')
    else:
        import base64
        remote = json.loads(base64.b64decode(r['content']))
        if remote.get('version') == version:
            print(f'  ✔ plugin.json 与目录版本一致（{version}）')
        else:
            fails.append(f'{name}: plugin.json 是 {remote.get("version")}，'
                         f'marketplace 写的是 {version} —— 版本不一致时用户收不到更新')
            print(f'  ✘ 版本不一致：plugin.json={remote.get("version")} '
                  f'marketplace={version}')

print()
if fails:
    print('✘ 发版检查未通过：')
    for f in fails:
        print('  ·', f)
    sys.exit(1)

print('✔ 全部通过，可以推 marketplace。')
print('\n用户升级命令（发版公告里贴这个）：')
print('    claude plugin marketplace update wikipali')
print('    claude plugin update wikipali@wikipali')
print('    # 然后重启会话')
PY
