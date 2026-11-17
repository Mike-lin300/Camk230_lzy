# camera-check

## When to use

- "镜头有没有画面 / 是不是黑的"
- "分辨率多少、帧率多少"
- 任何视觉技能零检出前的前置排查

## Preconditions

- `board-online` PASS
- 摄像头排线插在 CSI 上（GC2093，出厂已装）

## Steps

1. `python tools/camera_check.py`
2. 读 `width/height`、`luma_mean`、`dark_ratio`、`fps`
3. 要存图：`python tools/camera_check.py --save` → 板端 `/data/live/cam_*.jpg` → `python tools/pull_logs.py --remote data/live --dest logs/live`
4. 人要亲眼看：`python tools/accept.py --skill camera-check` → IDE 打开产物运行

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 6 `too_dark` | 镜头盖/镜头被挡/排线松 → 肉眼查镜头，断电重插 CSI 排线 |
| exit 6 `too_bright` | 强光直射 → 换个角度；不要改曝光（本工具没做） |
| exit 5 Traceback `sensor` | 摄像头没被识别 → 断电重插排线；仍失败查 `FACTS.md` 的 CSI 项 |
| `fps` < 10 | 分辨率太高 → `--width 320 --height 240` 再测 |
