"""管理统计（只读，仅 root / administrator 账号）：wikipali admin stats|runs|run|digest|feedback。

都走 v3 的 /v3/admin/*，用登录用户 token。服务端不回账号身份（提问者只分登录用户 / 游客），
digest 只含用户同意「用于改进」的提问——给 agent 做问题聚类、改进建议用。
"""

import json
import sys

from client import make_client
from cmd_read import emit
from errors import ApiError, WpError

ADMIN_TIMEOUT = 60

FEEDBACK_TAGS = {
    'accurate': '准确', 'useful_citations': '出处有用', 'clear': '讲得清楚', 'inspiring': '有启发',
    'citation_wrong': '出处不对/引用不存在', 'missed': '其实有经文它说没找到', 'off_topic': '答非所问',
    'incorrect': '内容有错', 'too_long': '太长', 'too_academic': '太学术', 'slow': '太慢', 'other': '其他',
}


def admin_get(client, path, query=None, envelope=False):
    try:
        return client.call('GET', path, token=client.user_token, query=query, v3=True,
                           timeout=ADMIN_TIMEOUT, envelope=envelope)
    except ApiError as exc:
        if exc.status == 403:
            raise WpError(f'当前账号不是管理员（需要 root 或 administrator）（{exc}）。') from exc
        raise


def range_query(args):
    return {'from': args.since, 'to': args.until}


def pct(n, of):
    return f'{n * 100 / of:.1f}%' if of else '—'


def delta(cur, prev):
    if cur is None or not prev:
        return ''
    d = (cur - prev) * 100 / prev
    return f'（环比 {d:+.0f}%）'


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

def cmd_admin_stats(args):
    client = make_client(args)
    query = {**range_query(args), 'client': args.client, 'account_type': args.account_type}
    if args.kind == 'reading':
        query.pop('account_type')
        data = admin_get(client, '/v3/admin/reading-stats', query)
        emit(args, data, lambda: render_reading(data))
    else:
        query.pop('client')
        data = admin_get(client, '/v3/admin/agent-stats', query)
        emit(args, data, lambda: render_agent(data))
    return 0


def render_reading(d):
    r, s, p = d['range'], d['summary'], d.get('previous') or {}
    print(f"阅读统计 {r['from']} ~ {r['to']}（客户端：{r['client']}）\n")
    print(f"  活跃读者     {s['active_readers']}{delta(s['active_readers'], p.get('active_readers'))}")
    print(f"  打开章节     {s['chapters_opened']}{delta(s['chapters_opened'], p.get('chapters_opened'))}")
    if s.get('reading_seconds') is not None:
        print(f"  读经时长     {s['reading_seconds'] / 3600:.1f} 小时（{s.get('reading_users') or 0} 人，仅 App）")
    if s.get('page_views') is not None:
        print(f"  网页浏览     {s['page_views']}")
    print(f"  查词         {s['dict_lookups']}")
    st = d.get('sticky') or {}
    print(f"  黏性 DAU/MAU {st.get('dau', 0)}/{st.get('mau', 0)}")
    top = d.get('top_chapters') or []
    if top:
        print('\n热门章节：')
        for row in top[:10]:
            print(f"  {row['readers']:>5} 人  {row['book']}:{row['paragraph']}  {row['title']}")


def render_agent(d):
    r, s, p = d['range'], d['summary'], d.get('previous') or {}
    runs = s['runs']
    print(f"AI 问答统计 {r['from']} ~ {r['to']}（账号：{r['account_type']}）\n")
    print(f"  提问         {runs}{delta(runs, p.get('runs'))}；提问人 {s['askers']}"
          f"（登录 {s['askers_user']} / 游客 {s['askers_guest']}）")
    print(f"  深度思考     {s['deep']}（{pct(s['deep'], runs)}）  阅读页提问 {s['passage']}")
    print(f"  出错 / 取消 / 额度拒绝  {s['errors']} / {s['cancelled']} / {s['denied']}")
    p50, p95 = s.get('latency_p50_ms'), s.get('latency_p95_ms')
    if p50 is not None:
        print(f"  耗时 P50/P95 {p50 / 1000:.1f}s / {(p95 or 0) / 1000:.1f}s")
    print(f"  token        入 {s['tokens_in']} / 出 {s['tokens_out']}")
    print(f"  可用于改进   {s['improve']}（{pct(s['improve'], runs)}）")
    print(f"\n  评价         👍 {s['feedback_up']}  👎 {s['feedback_down']}"
          f"（主动询问得到 {s['feedback_asked']}）")
    qa = s['quality_assessed']
    print(f"  质量检查     已检查 {qa}：引用不在证据里 {s['quality_unverified']}，"
          f"说没找到 {s['quality_missing']}，证据不足 {s['quality_thin']}")
    by_route = d.get('quality_by_route') or []
    if by_route:
        print('\n质量问题按路由（条数 / 检查数）：')
        print(f"  {'路由':<10} {'引用不在证据里':>10} {'说没找到':>8} {'证据不足':>8}")
        for row in by_route:
            n = row['assessed']
            print(f"  {row['route']:<12} {row['unverified']:>6}/{n:<6} {row['missing']:>6}/{n:<4} {row['thin']:>6}/{n}")
    reasons = d.get('feedback_reasons') or []
    if reasons:
        print('\n点踩原因：')
        for row in reasons:
            print(f"  {row['count']:>4}  {FEEDBACK_TAGS.get(row['reason'], row['reason'])}")
    tools = d.get('tools') or []
    if tools:
        print('\n工具调用：')
        for t in tools:
            print(f"  {t['name']:<20} {t['calls']:>5} 次  错 {t['errors']}  均 {t['avg_ms']}ms")


# ---------------------------------------------------------------------------
# runs / run
# ---------------------------------------------------------------------------

def cmd_admin_runs(args):
    client = make_client(args)
    query = {
        'page': args.page, 'per_page': args.limit,
        'filter[status]': args.status, 'filter[route]': args.route,
        'filter[account_type]': args.account_type, 'filter[client]': args.client,
        'filter[q]': args.q,
    }
    if args.improve:
        query['filter[improve]'] = 'true'
    payload = admin_get(client, '/v3/admin/agent-runs', query, envelope=True)
    rows = payload.get('data') or []

    def render():
        meta = payload.get('meta') or {}
        print(f"共 {meta.get('total', len(rows))} 条，第 {meta.get('current_page', 1)}/{meta.get('last_page', 1)} 页\n")
        for r in rows:
            flags = ' 深' if r.get('deep') else ''
            ms = r.get('latency_ms')
            took = f"{ms / 1000:.1f}s" if ms else '—'
            print(f"  {str(r.get('started_at'))[:16]}  {r.get('status'):<9} {str(r.get('route') or '—'):<9}"
                  f" {took:>6}{flags}  {(r.get('question') or '')[:60]}")
            print(f"      {r.get('run_id')}")
        print('\n详情：wikipali admin run <run_id>')

    emit(args, payload if args.json else rows, render)
    return 0


def cmd_admin_run(args):
    client = make_client(args)
    data = admin_get(client, f'/v3/admin/agent-runs/{args.run_id}')

    def render():
        print(f"问：{data.get('question')}")
        print(f"路由 {data.get('route')}  状态 {data.get('status')}"
              f"  耗时 {data.get('latency_ms')}ms  深度 {bool(data.get('deep'))}")
        if data.get('quality'):
            print(f"质量：{json.dumps(data['quality'], ensure_ascii=False)}")
        for step in data.get('steps') or []:
            name = step.get('name') or step.get('kind')
            err = f"  ✗ {step['error']}" if step.get('error') else ''
            print(f"  {step.get('seq'):>3} {step.get('kind')}:{name}  {step.get('ms') or 0}ms"
                  f"  {step.get('result_chars') or 0} 字{err}")
        if data.get('answer'):
            print('\n答：')
            print(data['answer'][:args.chars] if args.chars else data['answer'])

    emit(args, data, render)
    return 0


# ---------------------------------------------------------------------------
# digest：给 agent 分析用的精简导出（JSONL）
# ---------------------------------------------------------------------------

def cmd_admin_digest(args):
    client = make_client(args)
    payload = admin_get(client, '/v3/admin/agent-runs/digest',
                        {**range_query(args), 'limit': args.limit}, envelope=True)
    rows = payload.get('data') or []
    meta = payload.get('meta') or {}
    out = open(args.out, 'w', encoding='utf-8') if args.out else sys.stdout
    try:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + '\n')
    finally:
        if args.out:
            out.close()
    more = '（还有更多，缩小日期范围或加大 --limit）' if meta.get('has_more') else ''
    print(f"digest {meta.get('from')} ~ {meta.get('to')}：{len(rows)} 条{more}"
          + (f"，已写入 {args.out}" if args.out else ''), file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# feedback
# ---------------------------------------------------------------------------

def cmd_admin_feedback(args):
    client = make_client(args)
    rating = {'up': '1', 'down': '-1'}.get(args.rating) if args.rating else None
    query = {
        **range_query(args), 'page': args.page, 'per_page': args.limit,
        'filter[rating]': rating, 'filter[tag]': args.tag,
        'filter[has_comment]': 'true' if args.has_comment else None,
    }
    payload = admin_get(client, '/v3/admin/agent-feedback', query, envelope=True)
    rows = payload.get('data') or []

    def render():
        meta = payload.get('meta') or {}
        print(f"共 {meta.get('total', len(rows))} 条，第 {meta.get('current_page', 1)}/{meta.get('last_page', 1)} 页\n")
        for r in rows:
            mark = '👍' if (r.get('rating') or 0) > 0 else '👎'
            asked = ' [询问]' if r.get('asked') else ''
            tags = '、'.join(FEEDBACK_TAGS.get(t, t) for t in r.get('tags') or [])
            print(f"  {str(r.get('updated_at'))[:16]} {mark}{asked} {tags}")
            if r.get('comment'):
                print(f"      「{r['comment']}」")
            q = r.get('question')
            print(f"      问：{q[:70]}" if q else '      （提问记录还没入库）')
            if r.get('run_id'):
                print(f"      {r['run_id']}  {r.get('route') or ''}")

    emit(args, payload if args.json else rows, render)
    return 0


# ---------------------------------------------------------------------------
# 装配
# ---------------------------------------------------------------------------

def add_admin_parser(sub):
    p = sub.add_parser('admin', help='管理统计（只读，需 root / administrator 账号）')
    asub = p.add_subparsers(dest='admin_command', required=True)

    def add(name, help_text):
        q = asub.add_parser(name, help=help_text)
        q.add_argument('--json', action='store_true', help='输出原始 JSON')
        return q

    def add_range(q):
        q.add_argument('--since', help='起始日 YYYY-MM-DD（UTC）；统计与 digest 缺省 30 天前，评价缺省不限')
        q.add_argument('--until', help='结束日 YYYY-MM-DD（含），缺省今天')

    q = add('stats', '阅读 / AI 问答的汇总统计')
    q.add_argument('kind', choices=['reading', 'agent'])
    add_range(q)
    q.add_argument('--client', choices=['all', 'web', 'mobile'], help='阅读统计按客户端筛')
    q.add_argument('--account-type', dest='account_type', choices=['all', 'user', 'guest'],
                   help='AI 统计按账号类型筛')
    q.set_defaults(func=cmd_admin_stats)

    q = add('runs', 'AI 提问记录列表（最新在前）')
    q.add_argument('--status', choices=['ok', 'error', 'cancelled', 'denied', 'unchecked'])
    q.add_argument('--route', help='路由，如 question / term / passage / chat')
    q.add_argument('--account-type', dest='account_type', choices=['user', 'guest'])
    q.add_argument('--client', choices=['mobile', 'web'])
    q.add_argument('--improve', action='store_true', help='只看同意用于改进的')
    q.add_argument('--q', help='按问题文字搜')
    q.add_argument('--limit', type=int, default=20, help='每页条数，最多 100')
    q.add_argument('--page', type=int, default=1)
    q.set_defaults(func=cmd_admin_runs)

    q = add('run', '一次提问的研究过程')
    q.add_argument('run_id')
    q.add_argument('--chars', type=int, default=2000, help='回答最多显示多少字符，0 为不截断')
    q.set_defaults(func=cmd_admin_run)

    q = asub.add_parser('digest', help='精简导出（JSONL，一行一次提问），给 agent 做聚类与改进分析')
    add_range(q)
    q.add_argument('--limit', type=int, default=500, help='最多多少条，服务端上限 2000')
    q.add_argument('--out', help='写到文件；缺省输出到 stdout')
    q.set_defaults(func=cmd_admin_digest)

    q = add('feedback', '用户评价（点赞点踩、原因、说明）')
    add_range(q)
    q.add_argument('--rating', choices=['up', 'down'])
    q.add_argument('--tag', choices=list(FEEDBACK_TAGS), help='按标签 / 原因筛')
    q.add_argument('--has-comment', dest='has_comment', action='store_true', help='只看写了文字说明的')
    q.add_argument('--limit', type=int, default=20, help='每页条数，最多 100')
    q.add_argument('--page', type=int, default=1)
    q.set_defaults(func=cmd_admin_feedback)
