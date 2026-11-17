# SKILLS —— CanMV K230 能力索引

> 只读本文件即可选技能：按「触发场景」匹配 → 打开 `skills/<name>/SKILL.md` → 执行其中的命令 → 读末尾 `--- SUMMARY ---`。
> 环境事实（端口、固件、无盘符、性能）见 `FACTS.md`；本机是 Windows，所有命令在仓库根目录执行。
> **需要人做的事**（看屏、按 KEY、确认端子丝印）见 `NEEDS-YOU.md`，AI 不要替人下结论。
> 退出码：`0` 成功 / `2` 无端口或设备 / `3` 串口被占用 / `4` REPL 超时 / `5` 板端 Traceback / `6` 数据校验失败 / `7` 前置条件不满足。
>
> **人机分段**：AI 用 `--display none` 跑（帧率真实、零带宽）；人验收用 `python tools/accept.py --skill <name>` 生成 IDE 可直接运行的脚本，
> 同一份 payload、同一套参数，差别只有 `DISPLAY_MODE`。物理动作（举标签、短接 pin8↔pin10、插拔线）需要人。

| 技能 | 触发场景 | 入口脚本 | 预计耗时 | 前置检查 |
| --- | --- | --- | --- | --- |
| `env-doctor` | 工具跑不起来、换电脑、任何"找不到端口"之前 | `python tools/smoke.py` | 10 s | 无 |
| `board-online` | 板子在不在、什么固件、内存温度 | `python tools/board.py` | 3 s | 串口可开 + REPL 应答 |
| `run-code` | 跑一段代码/一个 .py、验 API | `python tools/run_code.py <file>` | 5–30 s | board-online |
| `camera-check` | 镜头有没有画面、分辨率帧率 | `python tools/camera_check.py` | 8 s | 摄像头在 CSI |
| `vision-blob-online` | 识别红/绿/蓝块、调阈值 | `python tools/vision.py --mode blob` | 15 s | camera-check verdict=ok |
| `vision-apriltag-online` | 识别 TAG36H11、id/坐标/角度 | `python tools/vision.py --mode apriltag` | 15 s | 标签在 30–80 cm 内（人放） |
| `gpio-led` | 点灯、闪灯、读按键 | `python tools/gpio.py --action blink` | 3 s | board-online |
| `display-lcd` | 屏装好了怎么点亮、LCD 黑屏/花屏 | `python tools/display.py` | 15 s | 31P 排线已接；**屏亮不亮需人确认** |
| `uart-loopback` | 串口通不通、TX/RX 接对没 | `python tools/uart_loop.py` | 10 s | **pin8↔pin10 短接（人）** |
| `offline-record` | 录几分钟数据、脱开电脑跑 | `python tools/record.py start` | 30–600 s | board-online + `/data` 可写 |
| `pull-logs` | 把板子数据拉回本地 | `python tools/pull_logs.py` | 5 s | `CanMV` 便携设备存在 |
| `analyze-log` | 分析数据、出结论、能不能上机 | `python tools/analyze_log.py logs/<run>` | 2 s | `logs/<run>/data.csv` |
| `recover-board` | 卡死、IDE 连不上、main.py 自启锁死 | `python tools/recover.py` | 20 s | 无（默认 dry-run） |
| `pinout` | IO2 是哪个针、UART 接哪两个 | `python tools/pinout.py --search UART1` | 1 s | 无（静态表） |

无标签/无目标时，视觉技能加 `--allow-empty` 只验通路：exit 0、`status=no_detection`（通路正常，只是没目标）。

**在线 / 离线是两组独立技能**：在线 = `camera-check` / `vision-*-online`（实时回传，板端不写盘）；
离线 = `offline-record` → `pull-logs` → `analyze-log`（板端写盘 → MTP 拉回 → 离线报告）。两者不互相调用。

`legacy-教程/` 是给人看的历史教程，**不要读**（内容与技能包不一致，会误导）。
