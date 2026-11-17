# display-lcd

## When to use

- "屏幕装好了，怎么点亮 / 怎么用"
- "LCD 一直是黑的 / 花屏"
- "把画面显示到 3.5 寸屏上看看"

## Preconditions

- 3.5" MIPI 屏已用 **31P 同向排线**接好：两端金手指**朝下**、插到底、压紧锁扣
- `smoke.py` 的 serial / repl PASS
- 板载蓝灯默认关背光：**上电不亮是正常的**，要跑本技能才亮

## Steps

1. `python tools/display.py`（默认 10 秒：红/绿/蓝 三条色带 + `K230 LCD OK` + FPS）
2. 换实时画面：`python tools/display.py --mode camera --seconds 30`
3. 读 SUMMARY：`lcd=ST7701`、`res=800x480`、`frames`、`fps`
4. **需要人眼确认**（`needs_human_confirm=true`）：屏是否真的出现色带
5. 要在 IDE 里同时看得见：本 payload 已带 `to_ide=True`

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 0 但屏是黑的 | 背光/FPC：断电 → 重插 31P 排线（金手指朝下、压锁扣）→ 重跑；仍黑则查 `FACTS.md` F5 |
| exit 5 Traceback `Display` | 驱动名不对（本板是 `Display.ST7701`）；确认固件仍是 v1.8（`board.py`） |
| 花屏 / 条纹 / 颜色错 | 排线接触不良 → 断电重插；不要带电插拔 |
| 只显示左上角一块 | 分辨率不匹配：屏是 800x480，payload 里 `width/height` 必须与之一致 |
| exit 3 `busy` | IDE 占着 COM → 关 IDE |
| `fps` 个位数 | 同时开了 IDE 推流（`to_ide=True`）→ 正常现象，屏上的帧率会低于 97（实测 800x480 无检测时约 97 FPS） |
