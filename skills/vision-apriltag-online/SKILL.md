# vision-apriltag-online

## When to use

- "识别 AprilTag / TAG36H11"
- "看一下 tag 的 id / 中心坐标 / 角度"
- 无人机视觉对准的通路验证

## Preconditions

- `camera-check` verdict=ok
- 30~80 cm 内有一张 TAG36H11 标签（需要人放）
- 固件含 `image` 模块（`board.py` 的 `mod_image=1`）

## Steps

1. `python tools/vision.py --mode apriltag --frames 120`
2. 读 SUMMARY：`hits`、`hit_ratio`、`fps_median`、`csv`
3. CSV 列：`frame,found,id,cx,cy,w,h,rot`（`w/h` 是距离的粗信号）
4. 画面里暂时没有标签时：加 `--allow-empty`，exit 0 + `status=no_detection`，用于证明通路正常
5. 人验收：`python tools/accept.py --skill vision-apriltag`

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 7 `no_detection` | 先用 `--allow-empty` 判断：能跑完 60 帧说明通路 OK，只是画面里没标签（需人放）；否则按序查边长 ≥40 px → 光照/反光 → 打印白边 → 镜头距离 |
| exit 5 `NameError: image` | payload 顶部取消 `# import image` 注释后重跑 |
| id 乱跳 | 多个标签同时在画面 / 标签被裁 → 只放一张、拍全 |
| exit 6 `no_frames` | `camera-check` 先确认有画面 |
