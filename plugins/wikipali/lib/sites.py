"""站点清单与地址解析。

内置只有两个线上地址：www.wikipali.cc（稳定版）与 next.wikipali.cc（最新版）。
两者共享同一个数据库和同一把 jwt 密钥，凭据完全通用；www / next 是代码版本，
不是数据环境。

其他地址（开发机、预发布等）不写进插件代码，由用户用
`wikipali endpoint add <简称> <url>` 手工登记，只保存在本机凭据文件的
`custom_sites` 里。自定义地址一律视为**另一个库**：自成一桶。

所有请求只发往当前设定的地址，网络不通即报错，不会自动切换站点。
"""

import re
import urllib.parse

from errors import WpError


# bucket 决定凭据/缓存存哪一桶。只有 bucket == "online" 的地址共享同一个数据库
# 与 jwt 密钥，凭据通用。
SITES = [
    {"key": "www", "url": "https://www.wikipali.cc/api",
     "version": "稳定版", "domain": ".cc", "bucket": "online"},
    {"key": "next", "url": "https://next.wikipali.cc/api",
     "version": "最新版", "domain": ".cc", "bucket": "online"},
]

BUCKET_BY_URL = {s["url"]: s["bucket"] for s in SITES}
DEFAULT_API_URL = SITES[0]["url"]

# 旧版内置、现已移除的线上地址 → 现在对应的内置地址（与原地址同库同版本）。
# 只用于把旧凭据文件里记下的地址平滑迁过来，不再对外展示。
LEGACY_ONLINE = {
    "https://www.wikipali.org/api": "https://www.wikipali.cc/api",
    "https://next.wikipali.org/api": "https://next.wikipali.cc/api",
}
# 旧版内置的别名，用户可能还在命令里这么写。
LEGACY_KEYS = {"www.cc": "www", "next.cc": "next"}

CUSTOM_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,31}$")


def normalize_api_url(url):
    url = url.strip().rstrip("/")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise WpError(f"API 地址必须以 http:// 或 https:// 开头：{url}")
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "http" and host not in ("127.0.0.1", "localhost", "::1"):
        raise WpError(f"只有 127.0.0.1 / localhost 允许用 http://，其余必须 https://：{url}")
    return LEGACY_ONLINE.get(url, url)


def custom_sites(creds):
    """凭据文件里用户手工登记的地址（只在本机）。"""
    items = (creds or {}).get("custom_sites") or []
    out = []
    for item in items:
        if isinstance(item, dict) and item.get("key") and item.get("url"):
            out.append({"key": item["key"], "url": item["url"],
                        "version": item.get("label") or "自定义", "domain": "独立库",
                        "bucket": "site:" + item["url"], "custom": True})
    return out


def all_sites(creds):
    """内置站点 + 本机登记的自定义站点，顺序即 `wikipali endpoint` 列表的序号。"""
    return SITES + custom_sites(creds)


def expand_site_alias(value, creds=None):
    """把序号 / 简称展开成完整 url；已是 url 则原样返回。"""
    value = value.strip()
    value = LEGACY_KEYS.get(value, value)
    sites = all_sites(creds)
    if value.isdigit():
        idx = int(value) - 1
        if 0 <= idx < len(sites):
            return sites[idx]["url"]
        raise WpError(f"站点序号超出范围：{value}（可选 1-{len(sites)}）")
    for site in sites:
        if value == site["key"]:
            return site["url"]
    if "://" in value:
        return value
    raise WpError(
        f"无法识别的站点：{value}。可用简称：" + " / ".join(s["key"] for s in sites)
        + "，或直接给完整 url；本机专用地址可用 wikipali endpoint add <简称> <url> 登记"
    )


def site_label(api_url, creds=None):
    for site in all_sites(creds):
        if site["url"] == api_url:
            if site.get("custom"):
                return f"{site['key']} · {site['version']} · 独立库"
            return f"{site['version']} · {site['domain']}"
    return "自定义地址"
