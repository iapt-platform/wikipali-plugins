# WikiPali 插件目录

[WikiPali](https://www.wikipali.org) 的 Claude Code 插件 marketplace。

```
/plugin marketplace add iapt-platform/wikipali-plugins
/plugin install wikipali@wikipali
```

桌面版在 **Code** 标签页点 `+` → **Plugins** → **Add plugin** 也能装。

## 插件

| 插件 | 说明 |
|---|---|
| [`wikipali`](https://github.com/iapt-platform/mint/tree/development/plugins/wikipali) | 巴利三藏的检索与阅读（词形展开、按词形检索、出处分布、按坐标取原文与译本），以及以 AI 模型身份写入句子。 |

## 这个仓库里为什么只有一个 json

插件本体住在 [iapt-platform/mint](https://github.com/iapt-platform/mint) 里，跟它调用的 Laravel API 同仓演进——API 契约一改，插件在同一个提交里跟上，不会漂移。

本仓库只放目录文件，是因为 `/plugin marketplace add` 会**完整克隆** marketplace 仓库，而 mint 是个几百 MB 的 monorepo。插件本身用 `git-subdir` 源，Claude Code 会**稀疏克隆**，只取 `plugins/wikipali/` 那一个目录。所以你装插件时下载的是几十 KB，不是几百 MB。

## 安全

插件能在你的机器上执行代码。装之前请读插件自己的 README，那里写明了它会读写哪些文件、会往哪里发数据。
