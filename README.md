# Camk230_lzy —— CanMV K230 能力基座

笔记本体是给 **AI 会话**用的，不是教程。三个入口：

| 先看这个 | 是什么 |
| --- | --- |
| **[NEEDS-YOU.md](NEEDS-YOU.md)** | 只有人能做的事（4 项，约 6 分钟）。**最显眼，先扫一遍** |
| **[SKILLS.md](SKILLS.md)** | AI 选技能的索引：触发场景 → 技能 → 入口脚本 → 退出码 |
| **[FACTS.md](FACTS.md)** | 已验证的环境事实（端口/固件/MTP/性能）+ 仍未验证清单 |

```
skills/<name>/SKILL.md   14 份技能说明（When / Preconditions / Steps / Failure modes）
tools/                  14 个入口脚本 + 3 个库（_wincom/_mprepl/_common）
payloads/               7 个板端脚本（经 REPL 推送执行，CFG 注入参数）
assets/tags36h11/       TAG36H11 全家族 587 张打印图（id 0–586）
logs/                   数据落点：live_*.csv、accept/*.py、<run_id>/ 运行记录
legacy-教程/            历史教程与构建记录，**AI 不要读**
```

约定：所有命令在仓库根目录执行（`python tools/xxx.py`）；串口运行期间 CanMV IDE 必须关闭。
