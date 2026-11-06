"""guide：把本插件 references/ 下的共享文档原样打到 stdout。

上层插件（如 wikipali-workspace）读不到本插件的文件——${CLAUDE_PLUGIN_ROOT} 只指向
它自己——但 bin/ 在 PATH 上。共享约定因此经由这条命令对外提供，CLI 就是两层之间的契约。
"""

import json
import os
import sys

from errors import WpError

_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
_REFS = os.path.join(_ROOT, 'references')

TOPICS = {
    'conventions': ('conventions.md', '通用约定：坐标、引用格式、文献层次、译文来源判定、站点、凭据'),
    'api-read': ('api-read.md', '读侧端点参考'),
    'api-write': ('api-write.md', '写侧端点参考：token、句子、术语、批注'),
}


def plugin_version():
    try:
        with open(os.path.join(_ROOT, '.claude-plugin', 'plugin.json'), encoding='utf-8') as fh:
            return json.load(fh).get('version', '?')
    except (OSError, ValueError):
        return '?'


def cmd_guide(args):
    if not args.topic:
        print(f'wikipali {plugin_version()} 的共享文档（wikipali guide <主题>）：')
        for name, (_, desc) in TOPICS.items():
            print(f'  {name:<12} {desc}')
        return 0
    if args.topic not in TOPICS:
        raise WpError(f'没有主题 {args.topic!r}，可选：{", ".join(TOPICS)}')
    path = os.path.join(_REFS, TOPICS[args.topic][0])
    try:
        with open(path, encoding='utf-8') as fh:
            sys.stdout.write(fh.read())
    except OSError as exc:
        raise WpError(f'读不到 {path}：{exc}。插件副本可能不完整，重装一下') from exc
    return 0
