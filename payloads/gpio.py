# payloads/gpio.py —— GPIO 动作（可单独在 IDE 里运行）
# CFG: action(on|off|blink|read|key) pin times interval_ms
import time
from machine import Pin, FPIOA

CFG = CFG if 'CFG' in globals() else {}
ACTION = CFG.get('action', 'on')
PIN = CFG.get('pin', 52)
TIMES = CFG.get('times', 3)
IV = CFG.get('interval_ms', 200)

fpioa = FPIOA()
fn = getattr(FPIOA, 'GPIO%d' % PIN, None)
print('PIN=%d' % PIN)
print('ACTION=%s' % ACTION)

if fn is None:
    print('ERR_PIN_CONST=%d' % PIN)
else:
    fpioa.set_function(PIN, fn)

    if ACTION == 'key':
        p = Pin(PIN, Pin.IN, Pin.PULL_UP)
        t0 = time.ticks_ms()
        last = 1
        presses = 0
        while time.ticks_diff(time.ticks_ms(), t0) < TIMES * 1000:
            v = p.value()
            if v == 0 and last == 1:
                presses += 1
            last = v
            time.sleep_ms(10)
        print('PRESSES=%d' % presses)

    elif ACTION == 'read':
        p = Pin(PIN, Pin.IN, Pin.PULL_UP)
        print('VALUE=%d' % p.value())

    elif ACTION == 'blink':
        p = Pin(PIN, Pin.OUT)
        for _i in range(TIMES):
            p.value(1)
            time.sleep_ms(IV)
            p.value(0)
            time.sleep_ms(IV)
        print('STATE=0')

    else:
        p = Pin(PIN, Pin.OUT)
        v = 1 if ACTION == 'on' else 0
        p.value(v)
        print('STATE=%d' % v)

print('PAYLOAD_END')
