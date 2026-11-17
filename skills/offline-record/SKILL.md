# offline-record

## When to use

- "录几分钟数据，我回头分析"
- "脱开电脑让它自己跑"
- "把这段过程的帧率/命中率记下来"

## Preconditions

- `board-online` PASS（会占用 COM 直到录制结束）
- 板端 `/data` 可写（`board.py` 的 `path_data=1`）

## Steps

1. `python tools/record.py start --duration 180`（默认 apriltag；blob 加 `--mode blob`）
2. 等它跑满自动结束，读 `run_id`、`frames`、`hits`、`saved`
3. 看已有记录：`python tools/record.py status`
4. 拷回本地：`python tools/pull_logs.py`（下一步技能）

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 4 超时 | 时长设太长 → 确认 `--duration` 与工具超时（内部=duration+120s） |
| exit 5 `NameError` | payload 顶部取消 `# import image` |
| exit 6 不完整 | 录制被中断（断电/复位）→ `record.py status` 看残留，重录 |
| `saved=0` 但 `hits>0` | `--save-interval-ms` 太大 → 调小到 500 |
