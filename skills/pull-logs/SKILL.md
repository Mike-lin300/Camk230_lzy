# pull-logs

## When to use

- "把数据拉回来"
- "板子上录的东西拷一份到本地"
- 分析前的搬运步骤

## Preconditions

- 「此电脑」里有 `CanMV` 便携设备（无盘符是正常的）
- 板子不在写盘（LED 常亮或没有录制任务）

## Steps

1. `python tools/pull_logs.py`
2. 读 `pulled_count`、`valid_runs`、`last_run_dir`
3. 只拉一个：`--only <run_id>`；拉别的目录：`--remote data/live --dest logs/live`
4. 数据落在 `logs/<run_id>/`，可直接给 `analyze-log`

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 2 `no_device` | MTP 设备不在 → 查供电/数据线；或改用读卡器（FACTS.md 有步骤） |
| exit 7 `remote_missing` | 板端没有该路径 → 先 `record.py start` 或 `camera_check.py --save` |
| 拉下来 0 字节 | 板子还在写 → 等录制结束；或 `--force` 重拉 |
| 超时 | MTP 卡住 → 重跑一次；连续失败用读卡器 |
