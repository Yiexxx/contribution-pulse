#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日编程语录

从内置语录库中按顺序(不重复)抽取一条,渲染成 quote-card.svg,
并追加到 QUOTES.md。每天由 daily-quote 工作流早晚各跑一次,
趣味和贡献格子双丰收。
"""

import os
from datetime import datetime, timedelta, timezone

QUOTES = [
    ("Talk is cheap. Show me the code.", "Linus Torvalds"),
    ("任何傻瓜都能写出计算机能懂的代码,好的程序员写的是人能懂的代码。", "Martin Fowler"),
    ("先让它能跑,再让它跑对,最后让它跑快。", "Kent Beck"),
    ("调试就像在犯罪电影里当侦探,只不过你同时也是凶手。", "Filipe Fortes"),
    ("代码是写给人看的,顺便能在机器上运行。", "Harold Abelson"),
    ("简单是可靠的前提。", "Edsger Dijkstra"),
    ("过早优化是万恶之源。", "Donald Knuth"),
    ("没有什么比临时方案更持久了。", "佚名"),
    ("最好的错误消息,是永远不会出现的那一个。", "Thomas Fuchs"),
    ("一切皆文件。", "Unix 哲学"),
    ("程序是用来解决问题的,不是用来展示聪明的。", "佚名"),
    ("计算机科学只有两件难事:缓存失效和命名。", "Phil Karlton"),
    ("测试是写给未来的自己的一封信。", "佚名"),
    ("慢下来,想清楚,再敲键盘。", "佚名"),
    ("代码评论里最常出现的一句话:『当时我到底在想什么?!』", "佚名"),
    ("好代码自己会说话。", "佚名"),
    ("重复,是一切软件罪恶之母。", "Robert C. Martin"),
    ("修 bug 的第一步,是让它可以稳定重现。", "佚名"),
    ("不要在凌晨三点 merge 代码。", "血泪教训"),
    ("最爽的 commit,是删掉了 500 行代码的那个。", "佚名"),
    ("今日事今日毕,今日 bug 今日修。", "佚名"),
    ("编程 90% 是思考,10% 才是敲键盘。", "佚名"),
    ("世界上有 10 种人:懂二进制的,和不懂的。", "经典老梗"),
    ("绿格子不会说谎。", "佚名"),
    ("commit message 是写给三个月后的自己的邮件。", "佚名"),
    ("能自动化的,就不要手动做。", "程序员信条"),
    ("备份做得最认真的时候,应该是丢数据之前。", "佚名"),
    ("需求总在变,抽象要先行。", "佚名"),
    ("EOF 不是结束,而是新故事的开始。", "佚名"),
    ("『git commit -m \"fix\"』是一种罪过。", "佚名"),
    ("别人写的代码都是垃圾——包括三个月前的自己。", "程序员定律"),
    ("测试跑得越快,你写测试的意愿就越强。", "佚名"),
    ("每学会一个新工具,就想把旧项目全部重写一遍。", "程序员通病"),
    ("睡眠是最好的调试器。", "佚名"),
    ("每个伟大的项目,都始于一句『我先随便搭个架子』。", "佚名"),
    ("删代码比写代码更需要勇气。", "Ron Jeffries"),
    ("代码不会自己烂掉,烂的是需求。", "佚名"),
    ("当你复制粘贴第三遍的时候,就该抽象成函数了。", "三次法则"),
    ("重新发明轮子之前,先看看轮子说明书。", "佚名"),
    ("写文档的最好时机是写代码的时候,其次是现在。", "佚名"),
    ("你以为的 bug,其实是 feature。", "程序员的自我修养"),
    ("Stay hungry, stay foolish.", "Steve Jobs"),
]

BEIJING = timezone(timedelta(hours=8))
FONT = "Segoe UI,Helvetica,Arial,sans-serif"


def disp_width(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)


def wrap(text, max_units=66):
    """按显示宽度折行:CJK 字符算 2 个单位,ASCII 算 1 个。"""
    lines, cur, w = [], "", 0
    for ch in text:
        cw = 2 if ord(ch) > 127 else 1
        if cur and w + cw > max_units:
            lines.append(cur)
            cur, w = "", 0
            if ch == " ":
                continue
        cur += ch
        w += cw
    if cur:
        lines.append(cur)
    return lines


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def count_entries():
    if not os.path.exists("QUOTES.md"):
        return 0
    n = 0
    with open("QUOTES.md", encoding="utf-8") as f:
        for line in f:
            if line.startswith("| ") and not line.startswith("| #") and not line.startswith("|--"):
                n += 1
    return n


def already_today_slot(today, slot):
    if not os.path.exists("QUOTES.md"):
        return False
    with open("QUOTES.md", encoding="utf-8") as f:
        for line in f:
            if line.startswith("| ") and today in line and slot in line:
                return True
    return False


def last_entry():
    """从 QUOTES.md 最后一行恢复 (idx, 日期, 时段, 语录, 作者),用于只刷新卡片样式。"""
    if not os.path.exists("QUOTES.md"):
        return None
    rows = []
    with open("QUOTES.md", encoding="utf-8") as f:
        for line in f:
            if line.startswith("| ") and not line.startswith("| #") and not line.startswith("|--"):
                rows.append(line)
    if not rows:
        return None
    parts = rows[-1].strip().strip("|").split("|")
    if len(parts) < 5:
        return None
    idx = parts[0].strip()
    return (int(idx) if idx.isdigit() else 1,
            parts[1].strip(), parts[2].strip(), parts[3].strip(), parts[4].strip())


def render_card(idx, total, text, author, slot, today):
    lines = wrap(text)
    width, height = 740, 158 + len(lines) * 34
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
        % (width, height, width, height),
        '<rect width="%d" height="%d" rx="12" fill="#0d1117" stroke="#30363d"/>'
        % (width, height),
        '<text x="28" y="74" font-family="%s" font-size="48" fill="#39d353">\u275d</text>' % FONT,
    ]
    y = 114
    for ln in lines:
        parts.append('<text x="86" y="%d" font-family="%s" font-size="18" font-weight="600" fill="#39d353">%s</text>'
                     % (y, FONT, esc(ln)))
        y += 34
    parts.append('<text x="712" y="%d" font-family="%s" font-size="15" font-weight="600" fill="#7ee787" text-anchor="end">—— %s</text>'
                 % (y, FONT, esc(author)))
    parts.append('<text x="28" y="%d" font-family="%s" font-size="12" fill="#c9d1d9">语录 #%d / %d · %s %s · 每天早晚各更新一条</text>'
                 % (height - 22, FONT, idx, total, today, slot))
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    now = datetime.now(BEIJING)
    today = now.strftime("%Y-%m-%d")
    hour = now.hour
    slot = "🌅 早间" if hour < 12 else ("🌆 午间" if hour < 18 else "🌙 晚间")

    if already_today_slot(today, slot):
        # 本时段已记录过:仍然重渲染卡片,让样式更新也能生效
        last = last_entry()
        if last:
            idx, d, s, text, author = last
            with open("quote-card.svg", "w", encoding="utf-8") as f:
                f.write(render_card(idx, len(QUOTES), text, author, s, d))
            print("%s %s 的语录已经记录过了,只刷新卡片样式" % (today, slot))
        else:
            print("%s %s 的语录已经记录过了,跳过" % (today, slot))
        return

    n = count_entries()
    idx = n + 1
    text, author = QUOTES[n % len(QUOTES)]

    with open("quote-card.svg", "w", encoding="utf-8") as f:
        f.write(render_card(idx, len(QUOTES), text, author, slot, today))

    header = (
        "# 🎙️ 每日编程语录\n\n"
        "由 [daily-quote](.github/workflows/daily-quote.yml) 早晚各抽取一条,"
        "语录不重复,直到把整个语录库轮完一轮。\n\n"
        "| # | 日期 | 时段 | 语录 | 作者 |\n"
        "|---|---|---|---|---|\n"
    )
    body = ""
    if os.path.exists("QUOTES.md"):
        with open("QUOTES.md", encoding="utf-8") as f:
            body = "".join(l for l in f
                           if l.startswith("| ") and not l.startswith("| #") and not l.startswith("|--"))
    row = "| %d | %s | %s | %s | %s |\n" % (idx, today, slot, text, author)
    with open("QUOTES.md", "w", encoding="utf-8") as f:
        f.write(header + body + row)
    print("语录 #%d: %s —— %s" % (idx, text, author))


if __name__ == "__main__":
    main()
