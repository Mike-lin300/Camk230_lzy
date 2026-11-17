# board-online

## When to use

- "板子在不在 / 连没连上"
- "现在什么固件、什么芯片"
- "内存还剩多少、温度多少"

## Preconditions

- `smoke.py` 的 `serial_port_found`、`port_openable` PASS
- 没有其他程序占用 COM（IDE 必须关闭）

## Steps

1. `python tools/board.py`
2. 读 SUMMARY 的 `fw_version`、`mem_free`、`temp_c`、`port`
3. 需要原始输出加 `--raw`；需要机读加 `--json`

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 2 `no usable COM port` | `python tools/smoke.py` 看 `serial_port_found`；无端口先查线/供电 |
| exit 3 `cannot open` | IDE 占用 → 关掉 IDE；或 `python tools/recover.py --release-port` |
| exit 4 `no REPL prompt` | `python tools/recover.py` 诊断（可能 main.py 自启锁死） |
| exit 6 `incomplete` | 板端输出被截断 → 重跑；连续两次则 `recover.py --reset` |
