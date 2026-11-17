# uart-loopback

## When to use

- "串口通不通 / 回环测一下"
- 接飞控前的自测
- "TX/RX 到底接对没有"

## Preconditions

- **需要人**：一根杜邦线短接排针 pin8(TX1) 与 pin10(RX1)
- 没有其他设备占用 UART1 引脚

## Steps

1. **UART1**：短接 pin8↔pin10 → `python tools/uart_loop.py --count 5`
2. **UART2**（板上有端子口的那路）：把端子的 TX2 与 RX2 短接 → `python tools/uart_loop.py --uart 2`
   - 引脚约定：TX2 = GPIO11，RX2 = GPIO12；**与 I2C2 共用**，二选一
3. 读 `uart`、`tx_pin`/`rx_pin`、`rx_bytes`、`match_frames`、`expect_frames`
4. 拔掉短接再跑一次，应变成 `rx_bytes=0`（"线是唯一变量"的反证）

> 2026-11-17 已由用户实测：UART1 短接后 `rx_bytes=40`、`match=5/5`（见 `FACTS.md` F 段）。

## Failure modes

| 现象 | 确定性下一步 |
| --- | --- |
| exit 7 `no_echo` | 短接没做好：UART1=pin8/pin10，UART2=端子 TX2/RX2。先 `pinout.py --pin 8` 核对 |
| UART2 完全无反应 | 该脚被 I2C2 占用 → 确认没在用 I2C；端子丝印是否 `11/TX2`、`12/RX2`（`NEEDS-YOU.md` C） |
| exit 6 `partial` | 波特率不一致或线太长 → `--baud 9600` 复测 |
| exit 5 Traceback `UART` | 引脚被别的功能占用 → `FACTS.md` 的 UART 项复核 |
| exit 3 busy | 关 IDE |
