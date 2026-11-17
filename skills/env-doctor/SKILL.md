# env-doctor

## When to use

- "工具跑不起来 / 环境是不是坏了"
- "换电脑了，先看看这套还能不能用"
- 任何技能报"找不到端口/模块不存在"之前的第一站

## Preconditions

- 无。这是唯一不需要前置的技能。

## Steps

1. `python tools/smoke.py`
2. 读表格：11 项应全 PASS
3. 有 FAIL 时看末行 `next_skill=` 指向的技能名，直接切过去

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| `serial_port_found` FAIL | 板子没上电或线是充电线 → 换线/换口；仍无则 `recover-board` |
| `port_openable` FAIL（busy） | CanMV IDE 占着 COM → 关 IDE，或 `python tools/recover.py --release-port` |
| `repl_prompt` FAIL | 板子在跑死循环或 main.py 自启 → `recover-board` |
| `raw_repl` FAIL | 固件不是 v1.8 → 按 `FACTS.md` 的镜像项复核，暂不升级 |
| `mtp_device_present` FAIL | 只影响 `pull-logs`；先跑 `python tools/pull_logs.py` 确认，或改用读卡器 |
