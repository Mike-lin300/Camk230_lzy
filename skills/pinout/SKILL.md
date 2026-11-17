# pinout

## When to use

- "IO2 是哪个针 / pin8 是什么"
- "UART 接哪两个脚"
- 接线前的查表

## Preconditions

- 无（纯静态表，不需要板子）

## Steps

1. `python tools/pinout.py`（全表）
2. `python tools/pinout.py --search UART1`
3. `python tools/pinout.py --pin 8`
4. `--json` 取机读版

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 6 `no_match` | 换关键词：`--search IO`、`--search PWM`、`--search ADC` |
| 接线不确定 | 以板子丝印为准；40Pin 端头的 2x3 调试排针（TX0/RX0/TX3/RX3）不可占用 |
