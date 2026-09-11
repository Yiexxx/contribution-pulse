#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""contribution-pulse: GitHub 贡献脉搏

零依赖的 Python 小工具:抓取你最近一年的 GitHub 贡献日历,在终端里
画出热力图,并给出总量 / 当前连续天数 / 最长连续天数等统计。
配合 `--log` 会把当天快照追加到 LOG.md 并更新 history/stats.json,
仓库内置的每日定时 Action 就是这样每天自动提交一次的。

用法:
  python pulse.py                  # 需要环境变量 GH_TOKEN 或 GH_PAT
  python pulse.py --token ghp_xxx
  python pulse.py --log            # 额外写入 LOG.md / history/stats.json
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import date, timedelta

API = "https://api.github.com"

# 仿 GitHub 贡献格的配色(0-4 档)
LEVEL_COLORS = [
    (22, 27, 34),
    (14, 68, 41),
    (0, 109, 50),
    (38, 166, 65),
    (57, 211, 83),
]
LEVEL_CHARS = ["·", "░", "▒", "▓", "█"]

GRAPHQL = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def http_json(url, token=None):
    req = urllib.request.Request(url, headers={
        "User-Agent": "contribution-pulse",
        "Accept": "application/vnd.github+json",
    })
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_login(token):
    return http_json(API + "/user", token)["login"]


def fetch_graphql(token, login):
    body = json.dumps({"query": GRAPHQL, "variables": {"login": login}}).encode("utf-8")
    req = urllib.request.Request(
        API + "/graphql",
        data=body,
        headers={
            "User-Agent": "contribution-pulse",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("errors"):
        raise RuntimeError(data["errors"][0].get("message", "graphql error"))
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = {}
    for week in cal["weeks"]:
        for d in week["contributionDays"]:
            days[d["date"]] = d["contributionCount"]
    return cal.get("totalContributions", sum(days.values())), days


def fetch_scrape(login):
    """备用方案:直接解析公开的个人主页贡献图。"""
    req = urllib.request.Request(
        "https://github.com/users/%s/contributions" % login,
        headers={"User-Agent": "Mozilla/5.0 (contribution-pulse)"},
    )
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    days = {}
    for tag in re.findall(r"<rect[^>]+>", html):
        m_d = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', tag)
        m_c = re.search(r'data-count="(\d+)"', tag)
        if m_d and m_c:
            days[m_d.group(1)] = int(m_c.group(1))
    if not days:
        raise RuntimeError("无法解析贡献页面")
    return sum(days.values()), days


def compute_levels(days):
    """把每天的贡献次数映射成 0-4 个颜色档位。"""
    nonzero = [c for c in days.values() if c > 0]
    if not nonzero:
        return {k: 0 for k in days}
    mx = float(max(nonzero))
    levels = {}
    for d, c in days.items():
        if c == 0:
            levels[d] = 0
        elif c <= mx * 0.25:
            levels[d] = 1
        elif c <= mx * 0.5:
            levels[d] = 2
        elif c <= mx * 0.75:
            levels[d] = 3
        else:
            levels[d] = 4
    return levels


def calc_streaks(days):
    """返回 (当前连续天数, 最长连续天数)。"""
    longest = 0
    cur = 0
    prev = None
    for key in sorted(days):
        if days[key] > 0:
            d = date.fromisoformat(key)
            cur = cur + 1 if prev is not None and (d - prev).days == 1 else 1
            longest = max(longest, cur)
            prev = d
    today = date.today()
    current = 0
    probe = today if days.get(today.isoformat(), 0) > 0 else today - timedelta(days=1)
    while days.get(probe.isoformat(), 0) > 0:
        current += 1
        probe -= timedelta(days=1)
    return current, longest


def build_weeks(days):
    """把 {日期字符串: 次数} 整理成以周为列、周日开头的 7 行网格。

    返回 (weeks, levels):每个 week 是长度为 7 的列表,网格外的位置是 None。
    """
    if not days:
        return [], {}
    start = date.fromisoformat(min(days))
    end = date.fromisoformat(max(days))
    counts = {}
    d = start
    while d <= end:
        key = d.isoformat()
        counts[key] = days.get(key, 0)
        d += timedelta(days=1)
    levels = compute_levels(counts)

    weeks = []
    week = [None] * ((start.weekday() + 1) % 7)  # 第一周左侧补位
    for key in sorted(counts):
        week.append(levels[key])
        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        weeks.append(week)
    return weeks, levels


def render_heatmap(days, use_color):
    """按周列(GitHub 同款,周日开头)渲染一年份热力图。"""
    if not days:
        return "(没有拿到贡献数据)"
    weeks, _ = build_weeks(days)

    lines = []
    for row in range(7):
        line = ""
        for w in weeks:
            lv = w[row] if row < len(w) else None
            if lv is None:
                line += " "
            elif use_color:
                r, g, b = LEVEL_COLORS[lv]
                line += "\033[48;2;%d;%d;%dm \033[0m" % (r, g, b)
            else:
                line += LEVEL_CHARS[lv]
        lines.append(line.rstrip())
    legend = "更少 " + ("".join(LEVEL_CHARS) if not use_color else "".join(
        "\033[48;2;%d;%d;%dm \033[0m" % LEVEL_COLORS[i] for i in range(5))) + " 更多"
    lines.append(legend)
    return "\n".join(lines)


SVG_DOTS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
FONT = "Segoe UI,Helvetica,Arial,sans-serif"


def render_stats_svg(login, total, current, longest, days):
    """生成自托管的统计卡片 SVG:标题 + 三个指标 + 一年份热力图。"""
    weeks, _ = build_weeks(days)
    cell, gap = 10, 3
    left, top = 24, 100
    width = max(left * 2 + len(weeks) * (cell + gap) - gap, 560)
    height = 216

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
        % (width, height, width, height),
        '<rect width="100%" height="100%" rx="12" fill="#0d1117" stroke="#30363d"/>',
        '<text x="%d" y="44" font-family="%s" font-size="17" font-weight="600" fill="#e6edf3">@%s · GitHub 贡献脉搏</text>'
        % (left, FONT, login),
        '<text x="%d" y="208" font-family="%s" font-size="12" fill="#c9d1d9">更新于 %s · 每天 08:23 自动刷新</text>'
        % (left, FONT, date.today().isoformat()),
    ]
    x = left
    for label, value, color in (
        ("近一年贡献", format(total, ","), "#39d353"),
        ("当前连续", str(current), "#7ee787"),
        ("最长连续", str(longest), "#7ee787"),
    ):
        parts.append('<text x="%d" y="76" font-family="%s" font-size="13" fill="#c9d1d9">%s</text>'
                     % (x, FONT, label))
        parts.append('<text x="%d" y="76" font-family="%s" font-size="15" font-weight="600" fill="%s">%s</text>'
                     % (x + len(label) * 13 + 8, FONT, color, value))
        x += len(label) * 13 + len(value) * 9 + 42

    for ci, w in enumerate(weeks):
        for ri, lv in enumerate(w):
            if lv is None:
                continue
            parts.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>'
                         % (left + ci * (cell + gap), top + ri * (cell + gap), cell, cell, SVG_DOTS[lv]))

    parts.append("</svg>")
    return "\n".join(parts)


def write_log(login, total, current, longest, days):
    """把当天快照写入 LOG.md(按日去重)和 history/stats.json,并生成 stats-card.svg。"""
    today = date.today().isoformat()
    today_count = days.get(today, 0)
    row = "| %s | %s | %d | %d | %s %d |" % (
        today, format(total, ","), current, longest,
        "🟢" if today_count else "💤", today_count,
    )

    os.makedirs("history", exist_ok=True)

    header = (
        "# 📊 Contribution Pulse · 贡献日志\n\n"
        "每天由 [daily-pulse](.github/workflows/daily-pulse.yml) 自动快照一次,"
        "每一行都对应一次真实提交,顺便点亮主页的贡献格子。\n\n"
        "| 日期 | 近一年贡献 | 当前连续 | 最长连续 | 当天 |\n"
        "|---|---|---|---|---|\n"
    )
    rows = []
    if os.path.exists("LOG.md"):
        with open("LOG.md", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("|") and not line.startswith("| 日期") \
                        and not line.startswith("|---") and line.strip() != "":
                    rows.append(line.rstrip("\n"))
    rows = [r for r in rows if not r.startswith("| " + today + " |")]
    rows.append(row)
    with open("LOG.md", "w", encoding="utf-8") as f:
        f.write(header + "\n".join(rows) + "\n")

    path = os.path.join("history", "stats.json")
    entries = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except (ValueError, OSError):
            entries = []
    entries = [e for e in entries if e.get("date") != today]
    entries.append({
        "date": today,
        "total_last_year": total,
        "current_streak": current,
        "longest_streak": longest,
        "today": today_count,
    })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries[-400:], f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open("stats-card.svg", "w", encoding="utf-8") as f:
        f.write(render_stats_svg(login, total, current, longest, days))


def main():
    ap = argparse.ArgumentParser(description="GitHub 贡献脉搏")
    ap.add_argument("--token", help="GitHub token(默认读环境变量 GH_TOKEN / GH_PAT)")
    ap.add_argument("--log", action="store_true", help="写入 LOG.md 与 history/stats.json")
    args = ap.parse_args()

    token = args.token or os.environ.get("GH_TOKEN") or os.environ.get("GH_PAT")
    if not token:
        sys.exit("需要 GitHub token:请设置环境变量 GH_TOKEN,或用 --token 传入")

    login = get_login(token)
    try:
        total, days = fetch_graphql(token, login)
        source = "GraphQL API"
    except Exception as e:
        print("GraphQL 不可用(%s),改用网页解析" % e)
        total, days = fetch_scrape(login)
        source = "公开网页"

    current, longest = calc_streaks(days)
    use_color = sys.stdout.isatty() or bool(os.environ.get("FORCE_COLOR"))

    print("@%s 的 GitHub 贡献脉搏" % login)
    if days:
        print("范围: %s → %s (数据源: %s)" % (min(days), max(days), source))
    print("近一年贡献: %s 次 | 当前连续: %d 天 | 最长连续: %d 天" % (
        format(total, ","), current, longest))
    print()
    print(render_heatmap(days, use_color))

    if args.log:
        write_log(login, total, current, longest, days)
        print()
        print("已写入 LOG.md、history/stats.json 和 stats-card.svg")


if __name__ == "__main__":
    main()
