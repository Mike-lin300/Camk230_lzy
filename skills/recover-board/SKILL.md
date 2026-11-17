# recover-board

## When to use

- "板子卡死 / IDE 连不上 / 一直重启"
- "上电就在跑我上次的脚本，停不下来"
- 任何技能报 `no REPL prompt`

## Preconditions

- 无（自愈优先）；**半自动**：默认只诊断，`--yes` 才动文件

## Steps

1. `python tools/recover.py`（dry-run，只看）
2. 按提示执行 `--yes`：把 `sdcard/main.py` 改名为 `main.py.bak`（保留现场）
3. 需要立即生效加 `--reset`（软复位）
4. 只查端口占用：`--release-port`

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 3 `port_busy` | IDE 占用 → 关掉 IDE；本工具不会强杀进程 |
| exit 4 `no REPL prompt` | 软复位也无效 → 拔 Type-C 等 5 秒重插（物理断电），再跑本工具 |
| 仍无 REPL | 用读卡器删 `sdcard/main.py`，或重烧镜像（不在技能包内，需人操作） |
| 改名成功但仍自动跑 | 还有一个 `boot.py` → 用 `run_code.py --code "import os; os.remove('/sdcard/boot.py')"` 前先确认存在 |
