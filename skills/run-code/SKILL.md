# run-code

## When to use

- "把这段代码/这个文件在板子上跑一下"
- "帮我验证一个 API 在这个固件上有没有"
- 写新 payload 时的快速迭代

## Preconditions

- `board-online` 能拿到固件串
- 代码不依赖外部文件（如需读文件，先确认板端路径存在）

## Steps

1. `python tools/run_code.py my_test.py`
2. 临时验证：`python tools/run_code.py --code "import os; print(os.uname())"`
3. 需要看画面：加 `--display ide`（会把 CFG['display'] 置为 ide）
4. 板端 stdout 原样打印；末尾 SUMMARY 含 `lines`、`duration_ms`

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 5 `script_error` | 看 stderr 最后一行：`NameError` 补 import；`OSError ENODEV` 查摄像头排线 |
| exit 4 超时 | 脚本里有死循环 → 加 `--timeout`，或改脚本为有界循环；必要时 `recover.py` |
| 输出里出现 `splay`/缺字符 | 大段代码被截断 → 已内置 256B 分块，仍出现就减小 `CHUNK`（`tools/_mprepl.py`） |
| exit 3 busy | 关 IDE 后重试 |
