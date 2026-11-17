# payloads/uart_loop.py —— UART 回环自测（需要人把 TX 与 RX 短接）
# CFG: uart(1|2) baud count interval_ms
#   UART1: TX=pin8(GPIO3)  RX=pin10(GPIO4)
#   UART2: TX=GPIO11       RX=GPIO12      （与 I2C2 共用引脚，二选一）
import time
from machine import UART, FPIOA

CFG = CFG if 'CFG' in globals() else {}
UART_NO = CFG.get('uart', 1)
BAUD = CFG.get('baud', 115200)
COUNT = CFG.get('count', 5)
IV = CFG.get('interval_ms', 100)

fpioa = FPIOA()
if UART_NO == 2:
    fpioa.set_function(11, FPIOA.UART2_TXD)
    fpioa.set_function(12, FPIOA.UART2_RXD)
    uart = UART(UART.UART2, BAUD)
    tx, rx = 11, 12
else:
    fpioa.set_function(3, FPIOA.UART1_TXD)
    fpioa.set_function(4, FPIOA.UART1_RXD)
    uart = UART(UART.UART1, BAUD)
    tx, rx = 8, 10

print('UART=%d' % UART_NO)
print('BAUD=%d' % BAUD)
print('TX_PIN=%d' % tx)
print('RX_PIN=%d' % rx)

sent = 0
got = 0
match = 0
for i in range(COUNT):
    msg = b'$K230,%d*' % i
    uart.write(msg)
    sent += len(msg)
    time.sleep_ms(IV)
    data = uart.read(64)
    if data:
        got += len(data)
        if data[:5] == b'$K230':
            match += 1

print('SENT_BYTES=%d' % sent)
print('RX_BYTES=%d' % got)
print('MATCH_FRAMES=%d' % match)
print('EXPECT_FRAMES=%d' % COUNT)
print('PAYLOAD_END')
