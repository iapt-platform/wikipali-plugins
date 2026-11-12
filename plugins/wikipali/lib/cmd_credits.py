"""AI 对话积分策略（公开，不需要登录）：wikipali credit-policy。

走 v3 的 GET /v3/credit-policy。只有当前生效的一版；version 是生效日（YYYYMMDD），
也记在每笔积分流水里。
"""

from client import make_client
from cmd_read import emit


def cmd_credit_policy(args):
    client = make_client(args)
    data = client.call('GET', '/v3/credit-policy', v3=True)

    def render():
        free, cost, earn = data['daily_free'], data['cost'], data.get('earn') or {}
        print(f"AI 对话积分策略 v{data['version']}（「一天」按 {data['day_timezone']} 算）\n")
        print(f"  每日赠送     游客 {free['guest']} / 登录用户 {free['user']}（当天用完即止，不累积）")
        print(f"  每次提问     普通 {cost['normal']} / 深度思考 {cost['deep']}")
        cap = data.get('guest_ip_daily_cap')
        print(f"  同 IP 游客   每天合计最多消耗 {cap if cap is not None else '不限'}")
        names = {'reading': '读经', 'editing': '编辑'}
        for key, rule in earn.items():
            daily = rule.get('daily_cap')
            print(f"  {names.get(key, key)}换积分   每分钟 {rule['credits_per_minute']}，"
                  f"每天上限 {daily if daily is not None else '不限'}（仅登录用户，积分不过期）")

    emit(args, data, render)
    return 0
