# gpio-led

## When to use

- "点个灯 / 让板载蓝灯闪一下"
- "读一下按键"
- 验证外接 LED 接线是否对

## Preconditions

- `board-online` PASS
- 外接 LED 时：pin7(IO2) → 330Ω~1kΩ → LED 长脚 → 短脚到 pin9(GND)

## Steps

1. 板载灯：`python tools/gpio.py --action blink --times 5`
2. 常亮：`python tools/gpio.py --action on`
3. 外接 LED：`python tools/gpio.py --action blink --pin 2`
4. 按键：`python tools/gpio.py --action key --times 10`（**不填 --pin 时自动用 21**；`--times` 也接受 `--time`）

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 7 `bad_pin` | 该脚在 FPIOA 无对应常量 → `python tools/pinout.py --search IO5` 换脚 |
| 灯不亮但 exit 0 | 板载灯是否真的亮只有人能确认（UNVERIFIED，见 FACTS.md）→ 换外接 LED 交叉验证 |
| 按键 `presses=0` | 先看 SUMMARY 的 `pin`：若不是 21 说明读错脚（历史坑：默认曾是 52）。确认 `pin=21` 后按 2~3 次；仍 0 则查 `FACTS.md` F2 |
| exit 3 busy | 关 IDE |
