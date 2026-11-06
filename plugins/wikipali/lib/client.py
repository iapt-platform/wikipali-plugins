"""HTTP 客户端：JSON 请求（只走当前设定的站点）、token 显示辅助。"""

import base64
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from creds import bucket_name_for, get_bucket, load_creds, resolve_api_url, save_creds
from errors import ApiError, WpError
from sites import site_label


TOKEN_REFRESH_MARGIN = 3600

DEFAULT_TIMEOUT = 30
WRITE_TIMEOUT = 120
DEFAULT_BATCH = 50

# 客户端身份：User-Agent 用标准「软件/版本」格式。版本只有 plugin.json 一处来源
# （与 install.sh 同一约定），读不到就退回 0.0.0。
DEFAULT_VERSION = "0.0.0"


def client_version():
    """从 <插件根>/.claude-plugin/plugin.json 读版本，失败退回 DEFAULT_VERSION。"""
    try:
        root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        path = os.path.join(root, ".claude-plugin", "plugin.json")
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and data.get("version"):
            return data["version"]
    except (OSError, ValueError):
        pass
    return DEFAULT_VERSION


USER_AGENT = f"wikipali-plugins/{client_version()}"


def mask(token):
    if not token:
        return "(无)"
    if len(token) <= 16:
        return token[:4] + "…"
    return token[:8] + "…" + token[-4:]


def jwt_payload(token):
    """不验签地读出 JWT payload，仅用于显示有效期。"""
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part.encode("ascii")))
    except Exception:
        return {}


def token_expiry(token):
    exp = jwt_payload(token).get("exp")
    return int(exp) if isinstance(exp, (int, float)) else None


def fmt_ts(ts):
    if not ts:
        return "未知"
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def note(msg):
    print(msg, file=sys.stderr)


def http_json(api_url, method, path, token=None, body=None, query=None, timeout=DEFAULT_TIMEOUT, v3=False,
              headers=None, envelope=False):
    """发一个 JSON 请求，返回解析后的响应体（dict）。

    网络层失败抛 urllib 的异常（由 Client 转成 WpError 报错退出）；
    HTTP 层失败抛 ApiError，带上服务端 message。

    v3=True 时按 v3 原生 Resource 信封处理：没有 ok 字段，成败只看 HTTP 状态码，
    同样返回 payload 的 data；v2 仍按 {ok, message, data} 判 ok。
    envelope=True（只对 v3）返回整个响应体，列表要读 meta（分页）时用。
    headers 是额外的请求头，如 agent 写入授权 X-Agent-Grant。
    """
    # 路径里可能有巴利词（parivāsa），urllib 只接受 ASCII，必须先百分号编码
    url = api_url + "/" + urllib.parse.quote(path.lstrip("/"), safe="/")
    if query:
        url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
    data = None
    # 本工具的界面是中文；v3 按 Accept-Language 返回错误文案（v2 不看这个头）
    # User-Agent 标识客户端软件（wikipali-plugins/版本），版本取自 plugin.json。
    headers = {"Accept": "application/json", "Accept-Language": "zh-Hans",
               "User-Agent": USER_AGENT, **(headers or {})}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        status = exc.code
        payload = safe_json(raw)
        message = None
        if isinstance(payload, dict):
            # v2 用 message，v3 Problem 用 detail（更具体），退 title（通用）
            message = payload.get("message") or payload.get("detail") or payload.get("title")
        raise ApiError(status, message, url=url, body=payload or raw)
    payload = safe_json(raw)
    if not isinstance(payload, dict):
        raise ApiError(status, f"响应不是 JSON：{raw[:200]}", url=url, body=raw)
    if v3:
        return payload if envelope else payload.get("data")
    if not payload.get("ok", False):
        raise ApiError(status, payload.get("message") or "请求失败", url=url, body=payload)
    return payload.get("data")


def safe_json(raw):
    try:
        return json.loads(raw)
    except ValueError:
        return None


class Client:
    """向当前设定的站点收发请求；网络不通即报错，不自动换站点。"""

    def __init__(self, api_url, source, creds):
        self.api_url = api_url
        self.source = source
        self.creds = creds
        self.bucket_name = bucket_name_for(api_url)
        self.bucket = get_bucket(creds, self.bucket_name, api_url)

    # -- 凭据 ---------------------------------------------------------------

    @property
    def user_token(self):
        token = (self.bucket.get("user") or {}).get("token")
        if not token:
            raise WpError(
                "尚未登录。执行 wikipali-login 即可——没有终端时它会弹出系统密码框，\n"
                "密码由你直接输给操作系统，AI 看不到。\n"
                "（若命令不在 PATH 上，用 ${CLAUDE_PLUGIN_ROOT}/bin/wikipali-login，"
                "或重启会话让 PATH 生效。）"
            )
        return token

    @property
    def model(self):
        model = self.bucket.get("model") or {}
        if not model.get("token"):
            raise WpError("尚未取得模型身份 token。请先跑：wikipali ensure-model --name <模型名>")
        return model

    def save(self):
        save_creds(self.creds)

    # -- 请求 ---------------------------------------------------------------

    def call(self, method, path, token=None, body=None, query=None, timeout=DEFAULT_TIMEOUT, v3=False,
             headers=None, envelope=False):
        # 只走当前设定的地址。网络层不通就报错退出，不自动换站点——换站点意味着换了
        # 代码版本甚至换了库，必须是用户明确的决定（wikipali endpoint / --api）。
        try:
            return http_json(self.api_url, method, path, token=token, body=body, query=query, timeout=timeout,
                             v3=v3, headers=headers, envelope=envelope)
        except (urllib.error.URLError, TimeoutError, OSError,
                http.client.HTTPException) as exc:
            # IncompleteRead 属于 HTTPException 而非 OSError——大响应（如两百多万
            # 字符的术语表）传输中断时会走到这里。不捕获的话会抛裸 traceback。
            reason = getattr(exc, "reason", exc)
            raise WpError(
                f"连不上 {self.api_url}（{site_label(self.api_url, self.creds)}）：{reason}\n"
                "不会自动切换站点。检查网络后重试，或用 wikipali endpoint 换一个站点"
                "（--api 只影响单次调用）。"
            )

    def api_note(self):
        src = {"cli": "--api", "env": "环境变量", "creds": "凭据文件", "default": "内置默认"}[self.source]
        return f"{self.api_url}（{site_label(self.api_url, self.creds)}，来源：{src}）"


def make_client(args):
    creds = load_creds()
    api_url, source = resolve_api_url(getattr(args, "api", None), creds)
    return Client(api_url, source, creds)
