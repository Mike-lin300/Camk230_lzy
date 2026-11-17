# vision-blob-online

## When to use

- "识别红块 / 试试色块检测"
- "调一下颜色阈值，看看能不能稳定框住"
- 视觉闭环保通路验证（不需要 AprilTag）

## Preconditions

- `camera-check` verdict=ok
- 画面里有人能放进去的纯色物体（色卡/纸片/玩具）

## Steps

1. `python tools/vision.py --mode blob --frames 120`
2. 换颜色：`--threshold "30,100,-64,-8,50,70"`（红/绿/蓝各有一套默认值见 SKILLS.md 底部）
3. 读 SUMMARY：`hit_ratio`、`fps_median`、`csv`
4. 人验收：`python tools/accept.py --skill vision-blob`

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 7 `no_detection` | 阈值不对或物体太小 → 先 `--min-pixels 50` 放宽，再照 IDE 阈值编辑器取色 |
| exit 6 `no_frames` | 摄像头没出图 → 先跑 `camera-check` |
| `hit_ratio` 高但框错物体 | 多个同色物体 → 工具取最大色块；改用 `--min-pixels` 过滤 |
| exit 3 busy | 关 IDE |
