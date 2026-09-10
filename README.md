# 📊 Contribution Pulse · 贡献脉搏

一个**零依赖**的 Python 小工具 + 一个每日定时 GitHub Action。

它每天自动抓取你的 GitHub 贡献数据(近一年总量、连续天数、热力图),
把当天的快照写进 `LOG.md` 并提交到本仓库 —— 于是:

- ✅ 你的主页贡献格子每天都会亮一格(这个仓库每天产生一次真实提交)
- ✅ `LOG.md` 变成一份持续更新的"贡献日志",随时回看自己的记录
- ✅ 工具本身可以在终端里渲染出 GitHub 同款贡献热力图

## 效果

仓库里的 `LOG.md` 长这样:

| 日期 | 近一年贡献 | 当前连续 | 最长连续 | 当天 |
|---|---|---|---|---|
| 2026-09-08 | 1,234 | 42 | 128 | 🟢 3 |

在本地终端运行 `python pulse.py`,还能直接看到彩色的热力图和统计。

主页同款统计卡片(自托管,永不限流):

```
https://raw.githubusercontent.com/Yiexxx/contribution-pulse/main/stats-card.svg
```

## 仓库结构

```
contribution-pulse/
├── pulse.py                            # 主工具(零依赖,只要 Python 3)
├── daily_quote.py                      # 每日编程语录生成器
├── fireworks.py                        # 贡献烟花动画生成器
├── LOG.md                              # 每日快照日志(Action 自动追加)
├── QUOTES.md                           # 每日语录日志(早晚各一条)
├── stats-card.svg                      # 自托管统计卡片(每天重新生成)
├── quote-card.svg                      # 今日语录卡片
├── fireworks.svg                       # 贡献烟花动画(当日贡献越多烟花越多)
├── history/stats.json                  # 结构化的历史数据
└── .github/workflows/                  # daily-pulse + daily-quote + fireworks 定时任务
```

## 本地使用

```bash
# 需要 GitHub token(有 repo 读权限即可),也可以用环境变量 GH_TOKEN
python pulse.py --token ghp_xxxxxxxxxxxx

# 顺便写入 LOG.md / history/stats.json
python pulse.py --log
```

## 它是怎么点亮贡献格子的?

GitHub 的贡献格子只统计**由你的账号邮箱提交**到默认分支的提交。
定时 Action 里默认的 `GITHUB_TOKEN` 身份是 `github-actions[bot]`,
它提交的记录**不算**你的贡献。所以本仓库的做法是:

1. 把一个属于你自己的 Personal Access Token(PAT)存为仓库 Secret `GH_PAT`;
2. Action 用这个 PAT 拉取你的贡献数据,并以
   `<你的ID>+<你的用户名>@users.noreply.github.com` 作为提交邮箱;
3. 这样每天 08:23(北京时间)就会有一次"属于你"的提交,
   贡献格子上就多一个绿点。

## 配置 / 自定义

- **改时间**:编辑 `.github/workflows/daily-pulse.yml` 里的 cron
  (注意 cron 用的是 UTC 时间,北京时间 = UTC + 8)。
- **换 token / 撤销**:仓库 Settings → Secrets and variables → Actions
  里更新或删除 `GH_PAT`;或在 GitHub 设置页直接吊销该 PAT。
- GitHub 会在仓库长期无活动时自动暂停定时任务,本仓库每天都有提交,
  所以不会触发这个问题。

## 一点说明

这些提交是工具自动生成的,用于保持记录和点亮格子 😄
真正的技术成长,还是来自你每天写的真实项目。

License: MIT
