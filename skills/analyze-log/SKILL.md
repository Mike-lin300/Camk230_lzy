# analyze-log

## When to use

- "分析这份数据 / 给个结论"
- "这套参数能不能上机"
- "为什么丢目标、帧率够不够"

## Preconditions

- `logs/<run_id>/data.csv` 存在（`pull-logs` 之后）

## Steps

1. `python tools/analyze_log.py logs/<run_id>`
2. 读 SUMMARY：`fps_median`、`hit_ratio`、`gaps`、`max_gap_ms`、`verdict`
3. 详细看 `report.md`（结论/命中区间/AI 摘要）与 `timeline.svg`
4. 要看现场：`logs/<run_id>/frames/*.jpg`

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 6 `no_data` | CSV 只有表头 → 录制没跑起来或全被中断，重录 |
| `eof=NO` | 录制被断电中断 → 数据到断点为止仍有效，但不要用于结论 |
| `verdict=有问题` | 按报告里第一条 ⚠️ 处理：帧率→降分辨率；命中率→调阈值/查标签 |
| exit 2 目录不存在 | 先 `pull-logs` |
