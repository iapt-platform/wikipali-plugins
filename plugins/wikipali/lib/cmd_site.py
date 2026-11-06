"""与站点和凭据状态有关的子命令：endpoint / whoami。"""

import sys
import time

from client import fmt_ts, make_client, mask, note, token_expiry
from creds import bucket_name_for, get_bucket, resolve_api_url, save_creds, load_creds, CREDS_PATH
from errors import ApiError, WpError, explain_api_error
from sites import CUSTOM_KEY_RE, LEGACY_KEYS, SITES, all_sites, expand_site_alias, normalize_api_url, site_label


def cmd_endpoint(args):
    creds = load_creds()
    if args.target in ("add", "remove", "rm"):
        return _endpoint_edit(args, creds)
    if args.rest:
        raise WpError(f"多余的参数：{' '.join(args.rest)}")
    current_url, source = resolve_api_url(getattr(args, "api", None), creds)
    sites = all_sites(creds)

    if not args.target:
        for idx, site in enumerate(sites, 1):
            mark = "  ← 当前" if site["url"] == current_url else ""
            if site.get("custom"):
                desc = f"{site['key']} · {site['version']} · 独立库（本机登记）"
            else:
                desc = f"{site['key']} · {site['version']}"
            print(f"  {idx}) {site['url']:<32} {desc}{mark}")
        if source in ("cli", "env"):
            src = "--api" if source == "cli" else "WIKIPALI_API_URL"
            note(f"注意：当前地址来自 {src}，是一次性覆盖，未写入凭据文件。")
        if current_url not in [s["url"] for s in sites]:
            print(f"  *) {current_url:<32} 自定义地址  ← 当前")
        keys = "|".join(x["key"] for x in sites)

        # 只有在真正的终端里才提示选择。agent 的 Bash 调用、CI、管道都没有 tty，
        # 那里必须保持纯展示——否则会卡在等输入上，且没人看得到提示符。
        if args.list or not sys.stdin.isatty():
            print(f"\n切换：wikipali endpoint <序号|{keys}|完整url>")
            print("登记本机专用地址：wikipali endpoint add <简称> <url> [--label 说明]")
            return 0

        print(f"\n输入序号切换，直接回车不改（也可以 wikipali endpoint <{keys}|完整url>）")
        try:
            raw = input("选择：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not raw:
            print("未改动。")
            return 0
        args.target = raw

    url = normalize_api_url(expand_site_alias(args.target, creds))
    name = bucket_name_for(url)
    bucket = get_bucket(creds, name, url)
    bucket["api_url"] = url
    creds["current"] = name
    save_creds(creds)
    print(f"已切换到 {url}（{site_label(url, creds)}）")
    if name != "online":
        note("提示：该地址按**另一个数据库**处理，与内置线上站点不共用数据与密钥。"
             "凭据和本地缓存都是独立的一桶，可能需要在该站点重新登录。")
        if url not in [s["url"] for s in all_sites(creds)]:
            note(f"可用 wikipali endpoint add <简称> {url} 登记，之后用简称切换。")
    return 0


def _endpoint_edit(args, creds):
    """登记 / 删除本机专用地址。只写本机凭据文件，不进插件代码。"""
    sites = creds.setdefault("custom_sites", [])
    builtin_keys = {s["key"] for s in SITES} | set(LEGACY_KEYS)

    if args.target == "add":
        if len(args.rest) != 2:
            raise WpError("用法：wikipali endpoint add <简称> <url> [--label 说明]")
        key, raw_url = args.rest
        if not CUSTOM_KEY_RE.match(key) or key.isdigit():
            raise WpError(f"简称只能用字母开头的字母 / 数字 / . _ -（至多 32 个字符）：{key}")
        if key in builtin_keys:
            raise WpError(f"{key} 是内置站点的简称，换一个")
        url = normalize_api_url(raw_url)
        if url in [s["url"] for s in SITES]:
            raise WpError(f"{url} 已是内置站点，无需登记")
        sites[:] = [x for x in sites if isinstance(x, dict) and x.get("key") != key and x.get("url") != url]
        item = {"key": key, "url": url}
        if args.label:
            item["label"] = args.label
        sites.append(item)
        save_creds(creds)
        print(f"已登记 {key} → {url}（只保存在 {CREDS_PATH}）")
        print(f"切换：wikipali endpoint {key}；单次使用：wikipali --api {key} …")
        return 0

    if len(args.rest) != 1:
        raise WpError("用法：wikipali endpoint remove <简称>")
    key = args.rest[0]
    hit = [x for x in sites if isinstance(x, dict) and x.get("key") == key]
    if not hit:
        raise WpError(f"本机没有登记过 {key}")
    sites[:] = [x for x in sites if x not in hit]
    if not sites:
        del creds["custom_sites"]
    url = hit[0]["url"]
    if creds.get("current") == bucket_name_for(url):
        creds["current"] = "online"
        print("当前站点就是它，已改回内置默认。")
    save_creds(creds)
    print(f"已删除登记 {key}（{url}）。该站点的凭据桶保留，重新登记即可沿用。")
    return 0


def cmd_whoami(args):
    client = make_client(args)
    print(f"API      : {client.api_note()}")
    print(f"凭据文件 : {CREDS_PATH}（桶：{client.bucket_name}）")

    user = client.bucket.get("user") or {}
    if user.get("token"):
        exp = token_expiry(user["token"])
        expired = exp is not None and exp < time.time()
        print(f"用户     : {user.get('username', '?')}  uid={user.get('uid', '?')}")
        print(f"           token {mask(user['token'])}  到期 {fmt_ts(exp)}{'  ⚠ 已过期' if expired else ''}")
    else:
        print("用户     : 未登录（wikipali-login）")

    model = client.bucket.get("model") or {}
    if model.get("token"):
        exp = token_expiry(model["token"])
        expired = exp is not None and exp < time.time()
        print(f"模型     : {model.get('name', '?')}  uid={model.get('uid', '?')}")
        print(f"           token {mask(model['token'])}  到期 {fmt_ts(exp)}{'  ⚠ 已过期' if expired else ''}")
    else:
        print("模型     : 未建立（wikipali ensure-model --name <模型名>）")

    tokens = client.bucket.get("access_tokens") or {}
    if tokens:
        print("access token：")
        for uid, item in tokens.items():
            exp = item.get("exp") or token_expiry(item.get("token", ""))
            expired = exp is not None and exp < time.time()
            book = item.get("book", 0)
            scope = "全部 book" if book == 0 else f"book {book}"
            name = item.get("channel_name") or ""
            print(f"  {uid[:8]}… {name:<24} {scope:<10} 到期 {fmt_ts(exp)}{'  ⚠ 已过期' if expired else ''}")
    else:
        print("access token：无（wikipali grant <channel>）")

    if args.check:
        try:
            data = client.call("GET", "v2/auth/current", token=client.user_token)
        except ApiError as exc:
            raise explain_api_error(exc, "校验用户 token")
        print(f"\n服务端确认：{data.get('nickName')} / realName={data.get('realName')}（studio_name 用它）")
    return 0
