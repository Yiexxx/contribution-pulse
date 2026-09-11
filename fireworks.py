#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""贡献烟花 🎆

读取 history/stats.json 里今天的贡献数据,生成一段循环绽放的烟花动画 SVG。
今天的贡献越多,烟花就越多。每天由 fireworks 工作流自动刷新。
"""

import json
import math
import random
from datetime import date

CYCLE = 6.0          # 动画总周期(秒),所有烟花按这个节奏循环
W, H = 740, 340
FONT = "Segoe UI,Helvetica,Arial,sans-serif"
COLORS = ["#ff7b72", "#ffa657", "#ffbd2e", "#7ee787", "#39d353",
          "#58a6ff", "#79c0ff", "#bc8cff", "#f778ba"]


def load_today():
    try:
        with open("history/stats.json", encoding="utf-8") as f:
            entries = json.load(f)
        for e in reversed(entries):
            if e.get("date") == date.today().isoformat():
                return e
    except (OSError, ValueError):
        pass
    return {"today": 0, "current_streak": 0}


def frac(t):
    return round(min(max(t, 0.0), CYCLE) / CYCLE, 4)


def burst(x, y, color, delay, rnd):
    """一发烟花:火箭升空 -> 空中爆裂 -> 粒子四散坠落。"""
    t0 = delay            # 点火
    t1 = delay + 0.7      # 爆裂
    t2 = delay + 1.7      # 消散
    f0, f1, f2 = frac(t0), frac(t1), frac(t2)
    g = ['<g>']

    # 火箭:从底部升空,爆裂后隐去
    g.append('<circle cx="%s" cy="0" r="2.5" fill="#e6edf3" opacity="0">' % x)
    g.append('<animate attributeName="cy" values="%s;%s;%s;%s" keyTimes="0;%s;%s;1" dur="%ss" repeatCount="indefinite"/>'
             % (H - 8, H - 8, y, y, f0, f1, CYCLE))
    g.append('<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;%s;%s;%s;%s;1" dur="%ss" repeatCount="indefinite"/>'
             % (f0, min(f0 + 0.002, 0.99), f1, min(f1 + 0.002, 0.99), CYCLE))
    g.append('</circle>')

    # 中心闪光
    g.append('<circle cx="%s" cy="%s" r="0" fill="%s" opacity="0">' % (x, y, color))
    g.append('<animate attributeName="r" values="0;0;16;0;0" keyTimes="0;%s;%s;%s;1" dur="%ss" repeatCount="indefinite"/>'
             % (f1, min(f1 + 0.05, 0.99), min(f1 + 0.16, 0.99), CYCLE))
    g.append('<animate attributeName="opacity" values="0;0;0.9;0;0" keyTimes="0;%s;%s;%s;1" dur="%ss" repeatCount="indefinite"/>'
             % (f1, min(f1 + 0.05, 0.99), min(f1 + 0.16, 0.99), CYCLE))
    g.append('</circle>')

    # 粒子:向四周飞散并受重力下坠
    n = 12
    for i in range(n):
        ang = 2 * math.pi * i / n + rnd.uniform(-0.15, 0.15)
        dist = rnd.uniform(26, 46)
        dx = round(dist * math.cos(ang), 1)
        dy = round(dist * math.sin(ang), 1)
        g.append('<circle cx="%s" cy="%s" r="2.6" fill="%s" opacity="0">' % (x, y, color))
        g.append('<animate attributeName="cx" values="%s;%s;%s;%s" keyTimes="0;%s;%s;1" dur="%ss" repeatCount="indefinite"/>'
                 % (x, x, x + dx, x + dx, f1, f2, CYCLE))
        g.append('<animate attributeName="cy" values="%s;%s;%s;%s" keyTimes="0;%s;%s;1" dur="%ss" repeatCount="indefinite"/>'
                 % (y, y, y + dy, y + dy + 10, f1, f2, CYCLE))
        g.append('<animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;%s;%s;%s;1" dur="%ss" repeatCount="indefinite"/>'
                 % (f1, min(f1 + 0.02, 0.99), f2, CYCLE))
        g.append('</circle>')

    g.append('</g>')
    return g


def main():
    stats = load_today()
    today = stats.get("today", 0)
    streak = stats.get("current_streak", 0)

    rnd = random.Random(date.today().isoformat())  # 每天一种编排,当天内稳定
    n_bursts = 3 + min(today, 5)  # 贡献越多烟花越多

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
        % (W, H, W, H),
        '<rect width="%d" height="%d" rx="12" fill="#0d1117" stroke="#30363d"/>'
        % (W, H),
    ]

    # 背景星星(缓慢闪烁)
    for _ in range(26):
        sx, sy = rnd.uniform(10, W - 10), rnd.uniform(10, H - 120)
        parts.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#8b949e">'
                     '<animate attributeName="opacity" values="0.15;0.8;0.15" dur="%.1fs" begin="%.1fs" repeatCount="indefinite"/></circle>'
                     % (sx, sy, rnd.uniform(0.6, 1.4), rnd.uniform(2, 4), rnd.uniform(0, 4)))

    # 烟花:位置错开、时间错开、颜色错开
    for i in range(n_bursts):
        x = round(rnd.uniform(W * 0.12, W * 0.88))
        y = round(rnd.uniform(50, H * 0.45))
        color = COLORS[(i + today) % len(COLORS)]
        delay = round(i * (CYCLE - 2.0) / max(n_bursts - 1, 1) + rnd.uniform(0, 0.3), 2)
        parts.extend(burst(x, y, color, delay, rnd))

    # 地平线与文字
    parts.append('<line x1="0" y1="%d" x2="%d" y2="%d" stroke="#21262d" stroke-width="1"/>' % (H - 30, W, H - 30))
    parts.append('<text x="%d" y="%d" font-family="%s" font-size="17" font-weight="600" fill="#e6edf3" text-anchor="middle">🎆 贡献烟花 · 今天绽放了 %d 发</text>'
                 % (W // 2, H - 10, FONT, n_bursts))
    parts.append('<text x="%d" y="%d" font-family="%s" font-size="12" fill="#8b949e" text-anchor="middle">今日贡献 %d 次 · 连续 %d 天 · 烟花数量随当日贡献增长 · 每天自动刷新</text>'
                 % (W // 2, H - 40, FONT, today, streak))
    parts.append('</svg>')

    with open("fireworks.svg", "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print("烟花生成完毕: %d 发,今日贡献 %d 次" % (n_bursts, today))


if __name__ == "__main__":
    main()
